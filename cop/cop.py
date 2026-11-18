import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

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
    "reply": ["[data-testid*=message-content i]", "[role=article]"],
}


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
            if loc.count() and (not visible or loc.last.is_visible()):
                return loc
        if time.time() >= end:
            return None
        time.sleep(0.3)


# >>> number of elements matched by a selector list <<< #
def count(page, queries):
    loc = find(page, queries)
    return loc.count() if loc else 0


# >>> attach to the running edge and return the chat tab <<< #
def connect(pw):
    try:
        browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
    except Exception:
        die("edge is not running on port %s, start it with: cop up" % PORT, 2)
    ctx = browser.contexts[0]
    try:
        ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=ORIGIN)
    except Exception:
        pass
    tabs = [p for p in ctx.pages if HOST in p.url]
    page = tabs[0] if tabs else (ctx.pages[0] if ctx.pages else ctx.new_page())
    if HOST not in page.url:
        page.goto(CHAT, wait_until="domcontentloaded")
    page.bring_to_front()
    return page


# >>> open a session url, or a fresh chat when url is empty <<< #
def goto(page, url):
    if url and page.url.split("?")[0] == url.split("?")[0]:
        return
    page.goto(url or CHAT, wait_until="domcontentloaded")


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
def reply(page, sel):
    btn = find(page, sel["copy"])
    if btn:
        try:
            page.evaluate("t => navigator.clipboard.writeText(t)", MARK)
        except Exception:
            pass
        btn.last.click()
        for _ in range(20):
            text = clip(page)
            if text and text != MARK:
                return text
            time.sleep(0.1)
    box = find(page, sel["reply"])
    if not box:
        die("no reply found, run: cop probe", 5)
    return box.last.inner_text()


# >>> send one prompt and wait until the reply has finished <<< #
def ask(page, sel, prompt, timeout):
    box = find(page, sel["input"], wait=60, visible=True)
    if not box:
        die("chat input not found: sign in inside the edge window, or run: cop probe", 3)
    before = count(page, sel["copy"])
    box = box.last
    box.click()
    box.fill(prompt)
    page.keyboard.press("Enter")
    start, seen, gone = time.time(), False, None
    while time.time() - start < timeout:
        busy = find(page, sel["stop"], visible=True) is not None
        if busy:
            seen, gone = True, None
        elif count(page, sel["copy"]) > before:
            return reply(page, sel)
        elif seen:
            gone = gone or time.time()
            if time.time() - gone > 5:
                return reply(page, sel)
        time.sleep(0.4)
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
    pr = sub.add_parser("probe")
    pr.add_argument("file")
    a = ap.parse_args()

    sel = selectors()
    with sync_playwright() as pw:
        page = connect(pw)
        if a.cmd == "open":
            goto(page, a.url)
            print(page.url)
        elif a.cmd == "ask":
            prompt = sys.stdin.read().strip()
            if not prompt:
                die("empty prompt")
            goto(page, a.url)
            text = ask(page, sel, prompt, a.timeout)
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
    main()
