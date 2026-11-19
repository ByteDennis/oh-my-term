"""Exercise the real Bash launcher with a disposable browser and local chat."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import shlex
import shutil
import signal
import socket
import subprocess
import sys
from threading import Thread

import pytest
from playwright.sync_api import sync_playwright

SCRIPT = Path(__file__).parents[1] / "cop"
HTML = b'''<textarea aria-label="Message Copilot"></textarea><div id="responses"></div>
<script>let n = 0; document.querySelector('textarea').onkeydown = e => {
if(e.key !== 'Enter') return; e.preventDefault(); n++;
history.replaceState({}, '', '?conversation=kept');
responses.insertAdjacentHTML('beforeend', '<article role="article">Answer ' + n + '</article>');
};</script>'''


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(HTML)

    def log_message(self, *_):
        pass


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.mark.skipif(sys.platform != "linux", reason="Linux native launcher regression")
def test_up_then_questions_never_relaunch_or_create_tabs(tmp_path):
    executable = os.environ.get("TEST_BROWSER") or shutil.which("google-chrome")
    if not executable:
        pytest.skip("set TEST_BROWSER to a Chromium executable")
    launches = tmp_path / "launches"
    browser_log = tmp_path / "browser.log"
    edge = tmp_path / "test edge"
    # Isolate this headless fixture from desktop extensions, keychain/first-run
    # dialogs and HTTPS upgrades of the local HTTP server. These are test flags,
    # never additions to the user's Edge launcher.
    edge.write_text("#!/bin/bash\nexec 2>" + shlex.quote(str(browser_log))
                    + "\nprintf '%s\\n' \"$$\" >> " + shlex.quote(str(launches))
                    + "\nexec " + shlex.quote(executable)
                    + ' --headless --no-sandbox --disable-dev-shm-usage --disable-gpu'
                    + ' --enable-unsafe-swiftshader --disable-extensions'
                    + ' --disable-features=PaintHolding,HttpsUpgrades,HttpsFirstBalancedModeAutoEnable'
                    + ' --password-store=basic --use-mock-keychain --disable-background-networking'
                    + ' --disable-search-engine-choice-screen'
                    + ' --disable-component-extensions-with-background-pages "$@"\n')
    edge.chmod(0o755)
    # Git Bash curl and native Python need not share network/proxy behavior.
    # Liveness must use Python, as the Playwright connection does.
    curl = tmp_path / "curl"
    curl.write_text("#!/bin/bash\nexit 1\n")
    curl.chmod(0o755)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    Thread(target=server.serve_forever, daemon=True).start()
    port = free_port()
    url = f"http://127.0.0.1:{server.server_port}/chat"
    env = dict(os.environ, COP_HOME=str(tmp_path / "cop home"), COP_EDGE=str(edge),
               COP_PYTHON=sys.executable, COP_PORT=str(port), COP_URL=url,
               COP_RENDER="cat", COP_TIMEOUT="5", COP_SETTLE="0.1", COP_LOGIN_TIMEOUT="2",
               PATH=str(tmp_path) + os.pathsep + os.environ["PATH"])

    def run(*args, **changes):
        return subprocess.run(["bash", str(SCRIPT), *args], input="", text=True,
                              capture_output=True, timeout=20, env=dict(env, **changes))

    browser = None
    try:
        with sync_playwright() as pw:
            for _ in range(2):
                result = run("up")
                assert result.returncode == 0, result.stderr + browser_log.read_text()[-5000:]
            assert len(launches.read_text().splitlines()) == 1
            # Neither invocation above had an external Playwright owner keeping
            # its browser alive; they exercised the actual detached launcher.
            browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
            ctx = browser.contexts[0]
            assert len(ctx.pages) == 1
            for number in (1, 2):
                result = run("ask", f"question {number}")
                assert result.returncode == 0, result.stderr
                assert result.stdout.strip() == f"Answer {number}"
                assert len(ctx.pages) == 1
                assert len(launches.read_text().splitlines()) == 1

            # An unavailable debug port must fail without launching Edge.
            result = run("ask", "offline", COP_PORT=str(free_port()))
            assert result.returncode != 0
            assert "cop doctor" in result.stderr
            assert len(launches.read_text().splitlines()) == 1
            assert (tmp_path / "cop home/last.md").read_text().strip() == "Answer 2"

            # An unrecognized existing tab also fails without replacing it.
            tab = ctx.pages[0]
            tab.goto(f"http://localhost:{server.server_port}/other?private=session")
            result = run("ask", "missing chat")
            assert result.returncode == 3
            assert "no Copilot tab" in result.stderr
            assert len(ctx.pages) == 1
            assert "localhost" in tab.url
            result = run("doctor")
            assert result.returncode == 0
            assert "tab host: localhost" in result.stdout
            assert "private=session" not in result.stdout
            assert len(launches.read_text().splitlines()) == 1
            browser.close()
            browser = None
    finally:
        server.shutdown()
        server.server_close()
        # Only PIDs recorded by this test's own launcher are eligible for cleanup.
        if launches.exists():
            for pid in launches.read_text().splitlines():
                try:
                    os.kill(int(pid), signal.SIGTERM)
                except ProcessLookupError:
                    pass
