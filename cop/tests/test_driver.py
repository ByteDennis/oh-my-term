import importlib.util
import shutil
import socket

import pytest
from playwright.sync_api import sync_playwright
from pathlib import Path

spec = importlib.util.spec_from_file_location("cop_driver", Path(__file__).parents[1] / "cop.py")
cop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cop)


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        cop.PORT = str(port)
        b = pw.chromium.launch(executable_path=shutil.which("google-chrome") or None,
                               headless=True, args=[f"--remote-debugging-port={port}"])
        yield pw, b
        b.close()


@pytest.fixture
def page(browser, monkeypatch):
    monkeypatch.setenv("COP_SETTLE", "0.3")
    ctx = browser[1].new_context()
    ctx.route("**/*", lambda route: route.fulfill(body="<html><body>Mock</body></html>", content_type="text/html"))
    p = ctx.new_page()
    p.goto(cop.CHAT)
    yield p
    ctx.close()


def mock(page, script):
    page.set_content('<textarea aria-label="Message Copilot"></textarea><div id="responses"></div><script>'
                     'document.querySelector("textarea").onkeydown = e => {'
                     'if (e.key === "Enter") {' + script + '}};</script>')


def test_query_conversation_switch(page):
    page.goto(cop.CHAT + "?conversation=first")
    cop.goto(page, cop.CHAT + "?conversation=second")
    assert page.url.endswith("conversation=second")


def test_unsaved_chat_is_not_reloaded(page):
    page.evaluate("window.preserved = 42")
    cop.goto(page, "")
    assert page.evaluate("window.preserved") == 42


def test_reply_without_stop_or_copy(page):
    mock(page, "setTimeout(() => responses.innerHTML = '<article role=article>Real answer</article>', 100);")
    assert cop.ask(page, cop.SEL, "hello", timeout=3) == "Real answer"


def test_prompt_echo_is_not_a_reply(page):
    mock(page, "responses.innerHTML = '<article role=article>hello</article>';")
    with pytest.raises(SystemExit) as exc:
        cop.ask(page, cop.SEL, "hello", timeout=0.6)
    assert exc.value.code == 4


def test_old_answer_is_not_returned(page):
    mock(page, "responses.insertAdjacentHTML('beforeend', '<article role=article>hello</article>');")
    page.locator("#responses").evaluate("n => n.innerHTML = '<article role=article>Old answer</article>'")
    with pytest.raises(SystemExit) as exc:
        cop.ask(page, cop.SEL, "hello", timeout=0.6)
    assert exc.value.code == 4


def test_waits_for_busy_to_finish_and_saves_url(page, tmp_path):
    mock(page, """responses.innerHTML = '<button aria-label=Stop>Stop</button><article role=article>Partial</article>';
      setTimeout(() => {responses.innerHTML = '<article role=article>Complete answer</article>';
      history.replaceState({}, '', '?conversation=saved');}, 700);""")
    target = tmp_path / "url"
    assert cop.ask(page, cop.SEL, "hello", timeout=4, url_file=target) == "Complete answer"
    assert target.read_text().endswith("conversation=saved")


def test_copy_reply_and_clipboard_fallback(page, monkeypatch):
    mock(page, "responses.innerHTML = '<article role=article>DOM answer</article><button aria-label=Copy>Copy</button>';")
    monkeypatch.setattr(cop, "clip", lambda page: "Clipboard markdown")
    assert cop.ask(page, cop.SEL, "hello", timeout=3) == "Clipboard markdown"
    # A reused old Copy button must never return an older response.
    assert cop.reply(page, cop.SEL, fallback="New answer", copy_after=1) == "New answer"


def test_status_connection_leaves_login_tab_in_place(browser):
    pw, b = browser
    # CDP uses the default context, not the incognito contexts above.
    ctx = b.contexts[0] if b.contexts else b.new_context()
    ctx.route("**/*", lambda route: route.fulfill(body="<html>Sign in</html>", content_type="text/html"))
    login = ctx.new_page()
    login.goto("https://login.microsoftonline.com/test")
    old = login.url
    count = len(ctx.pages)
    attached = cop.connect(pw, create=False)
    assert attached.url == old
    cop.goto(attached, cop.CHAT + "?conversation=saved")
    assert attached.url == old
    assert len(ctx.pages) == count
    login.close()
