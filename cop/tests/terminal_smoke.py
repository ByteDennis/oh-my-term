"""Linux terminal + real Chromium/CDP integration against a local mock page.

Requires playwright and pexpect. Never visits Microsoft or modifies user profiles.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
from threading import Thread
import time

import pexpect
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parents[2]
HTML = r'''<!doctype html><textarea aria-label="Message Copilot"></textarea><div id="responses"></div>
<script>
let timer;
document.cookie = 'fixture=persistent; Path=/; Max-Age=3600';
document.querySelector('textarea').onkeydown = e => {
 if(e.key !== 'Enter') return;
 e.preventDefault();
 const prompt = e.target.value; e.target.value = '';
 const number = Number(localStorage.getItem('count') || 0) + 1;
 localStorage.setItem('count', String(number));
 if(!location.search) history.replaceState({}, '', '?conversation=' + crypto.randomUUID());
 const user = document.createElement('article'); user.role = 'article'; user.dataset.messageAuthorRole = 'user'; user.textContent = prompt; responses.append(user);
 const stop = document.createElement('button'); stop.setAttribute('aria-label', 'Stop'); stop.textContent = 'Stop'; responses.append(stop);
 stop.onclick = () => {clearTimeout(timer); stop.remove();};
 timer = setTimeout(() => {
  stop.remove();
  const answer = 'Mock answer ' + number + ': ' + prompt;
  const article = document.createElement('article'); article.role = 'article'; article.dataset.messageAuthorRole = 'assistant'; article.textContent = answer; responses.append(article);
  const copy = document.createElement('button'); copy.setAttribute('aria-label', 'Copy'); copy.textContent = 'Copy'; copy.onclick = () => navigator.clipboard.writeText(answer); responses.append(copy);
 }, prompt === 'slow' ? 30000 : 150);
};
</script>'''


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML.encode())

    def log_message(self, *_):
        pass


def main():
    with tempfile.TemporaryDirectory(prefix="cop-terminal-") as temp, sync_playwright() as pw:
        temp = Path(temp)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        Thread(target=server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{server.server_port}/chat"
        browser = pw.chromium.launch_persistent_context(str(temp / "profile"),
            executable_path=os.environ.get("TEST_BROWSER") or shutil.which("google-chrome") or None, headless=True,
            args=[f"--remote-debugging-port={port}"])
        browser.pages[0].goto(url)
        env = dict(os.environ, COP_HOME=str(temp / "cop"), COP_PORT=str(port), COP_URL=url,
                   COP_PYTHON=sys.executable, COP_RENDER="cat", COP_TIMEOUT="15", COP_SETTLE="0.3",
                   COP_LOGIN_TIMEOUT="3", PROMPT_TOOLKIT_NO_CPR="1", TERM="xterm-256color")
        children = []
        try:
            child = pexpect.spawn("bash", [str(ROOT / "cop/cop"), "chat"], env=env, encoding="utf-8", timeout=25, dimensions=(35, 120))
            children.append(child)
            child.expect(r"In \[1\]:")
            child.sendline(":status")
            child.expect("connected")
            child.expect(r"In \[1\]:")
            child.sendline("hello")
            child.expect("Mock answer 1: hello")
            child.expect(r"In \[2\]:")
            child.send("first line\x1b\rsecond line\r")
            child.expect("Mock answer 2: first line")
            child.expect(r"In \[3\]:")
            attachment = temp / "test file.txt"
            attachment.write_text("attachment content")
            child.sendline(":file " + str(attachment))
            child.expect("Attached test file.txt")
            child.expect(r"In \[3\]:")
            child.sendline(":stream on")
            child.expect("Streaming on")
            child.expect(r"In \[3\]:")
            child.sendline("read this")
            child.expect("Mock answer 3: read this")
            child.expect("attachment content")
            child.expect(r"In \[4\]:")
            previous = (temp / "cop/last.md").read_text()
            child.sendline("slow")
            child.expect("waiting for response")
            child.sendcontrol("c")
            child.expect(r"In \[4\]:")
            for _ in range(50):
                if not (temp / "cop/lock").exists():
                    break
                time.sleep(.1)
            assert not (temp / "cop/lock").exists(), "cancelled prompt kept its lock"
            assert (temp / "cop/last.md").read_text() == previous
            child.sendline("after cancel")
            child.expect("Mock answer 5: after cancel")
            child.expect(r"In \[5\]:")
            export = temp / "conversation.md"
            child.sendline(":export " + str(export))
            child.expect("Exported 4 turns")
            child.expect(r"In \[5\]:")
            assert export.read_text().count("## You") == 4
            child.sendline(":q")
            child.expect(pexpect.EOF)
            assert len(browser.pages) == 1, "asking opened extra tabs"
            assert browser.pages[0].evaluate("localStorage.getItem('count')") == "5"
            assert "hello" in (temp / "cop/history").read_text()
            # The separate GitLab prompt stays usable after a parse error.
            repo = temp / "repo"
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            lab = pexpect.spawn("bash", [str(ROOT / "lab/lab"), "-C", str(repo)],
                env=dict(env, LAB_PYTHON=sys.executable, LAB_HOME=str(temp / "lab")), encoding="utf-8", timeout=15)
            children.append(lab)
            lab.expect(r"lab \[repo\]>")
            lab.sendline("unknown-command")
            lab.expect("invalid choice")
            lab.expect(r"lab \[repo\]>")
            lab.send("stat\t")
            lab.expect("status")
            lab.send("\r")
            lab.expect(r"git status --short --branch")
            lab.expect(r"lab \[repo\]>")
            lab.sendline("--dry-run ci test --ref feature")
            lab.expect("glab ci lint .gitlab-ci.yml --dry-run --include-jobs --ref feature")
            lab.expect(r"lab \[repo\]>")
            lab.sendline("quit")
            lab.expect(pexpect.EOF)
            report = {"passed": True, "checks": ["numbered prompt", "status", "real CDP round trips", "multiline keyboard input", "file attachment", "streaming", "cancellation and lock cleanup", "last reply preserved on cancel", "next request after cancel", "Markdown export", "single tab reuse", "persistent history", "GitLab prompt error recovery", "Tab completion", "CI simulation preview"]}
            evidence = ROOT / "plans/evidence"
            evidence.mkdir(parents=True, exist_ok=True)
            (evidence / "terminal-smoke.json").write_text(json.dumps(report, indent=2))
            print(json.dumps(report, indent=2))
        finally:
            for child in children:
                child.close(force=True)
            browser.close()
            server.shutdown()


if __name__ == "__main__":
    main()
