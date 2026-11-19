import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, build_opener

from playwright.sync_api import sync_playwright

HOME = Path(os.environ.get("COP_HOME", Path.home() / ".cop"))
PORT = os.environ.get("COP_PORT", "9222")
CHAT = os.environ.get("COP_URL", "https://m365.cloud.microsoft/chat")
ORIGIN = "{0.scheme}://{0.netloc}".format(urlsplit(CHAT))
HOST = urlsplit(CHAT).netloc
MARK = "⁣cop⁣"
SEL = {
    "input": [
        "role=textbox[name=/message|copilot|ask|prompt|chat/i]",
        "[contenteditable=true][role=textbox]",
        "textarea",
    ],
    "stop": ["role=button[name=/^stop/i]"],
    "copy": ["role=button[name=/^copy(?! code)/i]"],
    "assistant": [
        "[data-message-author-role=assistant]",
        "[data-author=assistant]",
        "[data-testid*=assistant-message i]",
    ],
    "reply": ["[data-testid*=message-content i]", "[role=article]"],
}
AUTH_HOSTS = {"login.microsoftonline.com", "login.live.com", "login.microsoft.com"}
CHAT_HOSTS = {"m365.cloud.microsoft", "m365copilot.com", "copilot.cloud.microsoft"}


def status(message):
    if os.environ.get("COP_STATUS", "1" if sys.stderr.isatty() else "0") == "1":
        print(f"cop: {message}", file=sys.stderr, flush=True)


def is_chat(page):
    url = urlsplit(page.url)
    configured = urlsplit(CHAT)
    if url.scheme == configured.scheme and url.netloc.lower() == HOST.lower():
        return True
    # Microsoft redirects between these hosts. Custom COP_URL origins stay exact.
    return (configured.scheme == "https" and configured.hostname in CHAT_HOSTS
            and configured.port in (None, 443)
            and url.scheme == "https" and url.hostname in CHAT_HOSTS
            and url.port in (None, 443))


def debug_json(path):
    # Use the same native Python/loopback as Playwright, including in Git Bash.
    opener = build_opener(ProxyHandler({}))
    with opener.open(f"http://127.0.0.1:{PORT}/json/{path}", timeout=2) as response:
        return json.load(response)


def doctor():
    print(f"python: {sys.executable} ({platform.system()})")
    print(f"profile: {HOME / 'edge'}")
    print(f"debug endpoint: http://127.0.0.1:{PORT}")
    try:
        version = debug_json("version")
        print(f"browser: {version.get('Browser', 'unknown')}")
        for tab in debug_json("list"):
            if tab.get("type") == "page":
                url = urlsplit(tab.get("url", ""))
                # Omit paths, queries and titles, which can contain session data.
                print(f"tab host: {url.hostname or url.scheme or '(blank)'}")
    except Exception as exc:
        print(f"debug connection unavailable ({type(exc).__name__}); run: cop up")


def needs_login(page):
    return urlsplit(page.url).hostname in AUTH_HOSTS


# >>> print an error and exit with a code <<< #
def die(msg, code=1):
    print(f"cop: {msg}", file=sys.stderr)
    sys.exit(code)


# >>> default selectors merged with $COP_HOME/selectors.json <<< #
def selectors():
    sel = dict(SEL)
    f = HOME / "selectors.json"
    if f.exists():
        for k, v in json.loads(f.read_text(encoding="utf-8")).items():
            sel[k] = v if isinstance(v, list) else [v]
    return sel


# >>> first selector in the list that matches, as a locator <<< #
def find(page, queries, wait=0.0, visible=False):
    end = time.time() + wait
    while True:
        for q in queries:
            loc = page.locator(q)
            if visible:
                for index in range(loc.count() - 1, -1, -1):
                    if loc.nth(index).is_visible():
                        return loc.nth(index)
            elif loc.count():
                return loc
        if time.time() >= end:
            return None
        time.sleep(0.3)


# >>> number of elements matched by a selector list <<< #
def count(page, queries):
    loc = find(page, queries)
    return loc.count() if loc else 0


# >>> attach to the running edge and return the chat tab <<< #
def connect(pw, create=False):
    status("connecting to existing browser")
    try:
        browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}", timeout=10000)
    except Exception as exc:
        reason = str(exc).splitlines()[0]
        die(f"cannot attach to Edge on port {PORT}: {reason}; run: cop doctor", 2)
    ctx = browser.contexts[0]
    try:
        ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=ORIGIN)
    except Exception:
        pass
    tabs = [p for p in ctx.pages if is_chat(p)]
    auth = [p for p in ctx.pages if needs_login(p)]
    page = tabs[0] if tabs else (auth[0] if auth else None)
    if page is None and not create:
        die("browser connected; no Copilot tab (run: cop up)", 3)
    if page is None:
        page = next((p for p in ctx.pages if p.url == "about:blank"), None) or ctx.new_page()
        page.goto(CHAT, wait_until="domcontentloaded")
    try:
        origin = "{0.scheme}://{0.netloc}".format(urlsplit(page.url))
        if is_chat(page):
            ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=origin)
    except Exception:
        pass
    return page


# >>> open a session url, or a fresh chat when url is empty <<< #
def goto(page, url, fresh=False):
    # Leave a sign-in flow intact, and keep an unsaved conversation on ask.
    if needs_login(page) or (not url and not fresh and is_chat(page)):
        return
    if page.url == (url or CHAT) and not fresh:
        return
    page.goto(url or CHAT, wait_until="domcontentloaded")


def ready(page, sel, timeout=None):
    timeout = float(os.environ.get("COP_LOGIN_TIMEOUT", "120")) if timeout is None else timeout
    end = time.monotonic() + timeout
    reported = False
    status("checking chat input and sign-in")
    while True:
        box = find(page, sel["input"], visible=True) if is_chat(page) else None
        if box:
            status("connected")
            return box.last
        if needs_login(page) and not reported:
            status("needs login — sign in in the existing browser window; waiting")
            page.bring_to_front()
            reported = True
        if time.monotonic() >= end:
            if needs_login(page):
                die("needs login: sign in in the existing browser window, then retry", 3)
            die("chat input not found: check the browser, or run: cop probe", 3)
        page.wait_for_timeout(300)


def snapshot(page, sel):
    """Keep a separate baseline for each selector; generic articles may be users."""
    values = {}
    for query in sel.get("assistant", []) + sel["reply"]:
        values[query] = page.locator(query).evaluate_all("""nodes => nodes
            .filter(n => n.getClientRects().length && !n.closest(
                '[data-message-author-role=user], [data-author=user]'))
            .map(n => { const c = n.cloneNode(true);
                c.querySelectorAll('button, [role=button]').forEach(b => b.remove());
                return (c.textContent || '').trim(); })""")
    return values


def newest(before, after, prompt):
    normalize = lambda text: " ".join(text.split())
    for query, texts in after.items():
        old = before.get(query, [])
        for index in range(len(texts) - 1, -1, -1):
            text = texts[index]
            if text and normalize(text) != normalize(prompt) and (index >= len(old) or text != old[index]):
                return text
    return ""


# >>> read the system clipboard from the page, else from windows <<< #
def clip(page):
    try:
        return page.evaluate("navigator.clipboard.readText()")
    except Exception:
        pass
    ps = shutil.which("powershell") or shutil.which("powershell.exe")
    if ps:
        out = subprocess.run([ps, "-NoProfile", "-Command", "Get-Clipboard -Raw"],
                             capture_output=True, text=True, encoding="utf-8")
        return out.stdout.rstrip("\r\n")
    return ""


# >>> newest reply as markdown via its copy button, else as plain text <<< #
def reply(page, sel, fallback=None, copy_after=None):
    btn = find(page, sel["copy"])
    if btn and (copy_after is None or btn.count() > copy_after):
        try:
            previous = clip(page)
            page.evaluate("t => navigator.clipboard.writeText(t)", MARK)
            previous = MARK
        except Exception:
            previous = clip(page)
        try:
            btn.last.click(timeout=2000)
            for _ in range(20):
                text = clip(page)
                if text and text != MARK and text != previous:
                    return text
                page.wait_for_timeout(100)
        except Exception:
            pass
    if fallback is not None:
        return fallback
    box = find(page, sel["reply"])
    if not box:
        die("no reply found, run: cop probe", 5)
    return box.last.inner_text()


# >>> send one prompt and wait until the reply has finished <<< #
def ask(page, sel, prompt, timeout, url_file=None):
    box = ready(page, sel)
    before = count(page, sel["copy"])
    baseline = snapshot(page, sel)
    box.click()
    box.fill(prompt)
    page.keyboard.press("Enter")
    status("waiting for response — Ctrl+C to cancel")
    start = changed = time.monotonic()
    last, copied = "", False
    settle = float(os.environ.get("COP_SETTLE", "3"))
    stream = os.environ.get("COP_STREAM") == "1"
    streamed = False
    while time.monotonic() - start < timeout:
        if url_file and is_chat(page):
            Path(url_file).write_text(page.url, encoding="utf-8")
        if needs_login(page):
            die("needs login: the session expired; sign in in the existing browser window", 3)
        busy = find(page, sel["stop"], visible=True) is not None
        text = newest(baseline, snapshot(page, sel), prompt)
        has_copy = count(page, sel["copy"]) > before
        if text != last or has_copy != copied or busy:
            changed = time.monotonic()
        if stream and text and text != last:
            if not streamed:
                print("\n", end="", file=sys.stderr, flush=True)
            delta = text[len(last):] if text.startswith(last) else "\n" + text
            print(delta, end="", file=sys.stderr, flush=True)
            streamed = True
        last, copied = text, has_copy
        if not busy and (text or has_copy) and time.monotonic() - changed >= settle:
            answer = reply(page, sel, fallback=text or None, copy_after=before)
            if streamed:
                print(file=sys.stderr, flush=True)
            elif stream:
                print(answer, file=sys.stderr, flush=True)
            status("response received")
            return answer
        page.wait_for_timeout(200)
    die("timed out waiting for the reply", 4)


# >>> command line entry point <<< #
def main():
    for s in (sys.stdin, sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="cop.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    op = sub.add_parser("open")
    op.add_argument("url", nargs="?", default="")
    ak = sub.add_parser("ask")
    ak.add_argument("--url", default="")
    ak.add_argument("--url-file")
    ak.add_argument("--timeout", type=float, default=float(os.environ.get("COP_TIMEOUT", 600)))
    sub.add_parser("last")
    sub.add_parser("status")
    sub.add_parser("ping")
    sub.add_parser("doctor")
    sub.add_parser("ensure")
    pr = sub.add_parser("probe")
    pr.add_argument("file")
    a = ap.parse_args()

    if a.cmd == "ping":
        try:
            version = debug_json("version")
            if not version.get("webSocketDebuggerUrl"):
                raise ValueError("not a browser debug endpoint")
        except Exception:
            sys.exit(2)
        return
    if a.cmd == "doctor":
        doctor()
        return

    sel = selectors()
    with sync_playwright() as pw:
        page = connect(pw, create=a.cmd in {"open", "ensure"})
        if a.cmd == "ensure":
            return
        elif a.cmd == "open":
            goto(page, a.url, fresh=not a.url)
            print(page.url)
        elif a.cmd == "status":
            if needs_login(page):
                print("needs login — sign in in the existing browser window")
                return
            print("connected" if find(page, sel["input"], visible=True) else "browser connected; chat input not ready (run: cop probe)")
        elif a.cmd == "ask":
            prompt = sys.stdin.read().strip()
            if not prompt:
                die("empty prompt")
            goto(page, a.url)
            ready(page, sel)
            # Authentication may have redirected us away from the saved chat.
            goto(page, a.url)
            try:
                text = ask(page, sel, prompt, a.timeout, a.url_file)
            except KeyboardInterrupt:
                stop = find(page, sel["stop"], visible=True)
                if stop:
                    try:
                        stop.last.click(timeout=2000)
                    except Exception:
                        pass
                die("cancelled", 130)
            if a.url_file:
                Path(a.url_file).write_text(page.url, encoding="utf-8")
            print(text)
        elif a.cmd == "last":
            print(reply(page, sel))
        elif a.cmd == "probe":
            snap = page.locator("body").aria_snapshot()
            Path(a.file).write_text(f"# {page.url}\n\n{snap}\n", encoding="utf-8")
            print(a.file)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        die("cancelled", 130)
