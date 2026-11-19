"""Run after the frontend build. Uses a temporary DB, random admin password,
and owned uvicorn/Chrome processes. No real services or user data are modified.
"""
import json
import os
import re
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time

import httpx
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).parents[1]
EVIDENCE = ROOT.parent / "plans/evidence"
EVIDENCE.mkdir(parents=True, exist_ok=True)


def main():
    with tempfile.TemporaryDirectory(prefix="meta-browser-") as temp:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        password = secrets.token_urlsafe(32)
        env = dict(os.environ, META_ADMIN_PASSWORD=password, META_DB=str(Path(temp) / "catalog.sqlite"))
        server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(port)], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        url = f"http://127.0.0.1:{port}"
        try:
            for _ in range(100):
                try:
                    if httpx.get(url + "/api/health", trust_env=False).status_code == 200:
                        break
                except httpx.ConnectError:
                    pass
                time.sleep(.1)
            else:
                raise RuntimeError("uvicorn did not start")
            with sync_playwright() as pw:
                browser = pw.chromium.launch(executable_path=os.environ.get("TEST_BROWSER") or shutil.which("google-chrome") or None, headless=True)
                context = browser.new_context(viewport={"width": 1440, "height": 960}, reduced_motion="reduce")
                context.grant_permissions(["clipboard-read", "clipboard-write"], origin=url)
                page = context.new_page()
                page.set_default_timeout(10000)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(url, wait_until="networkidle")
                expect(page.get_by_role("heading", name="orders", exact=True)).to_be_visible()
                expect(page).to_have_title("Datasaurus · Metadata workspace")
                expect(page.get_by_role("link", name="Datasaurus Metadata workspace")).to_be_visible()
                expect(page.locator(".page-footer")).to_contain_text("Create time:")
                expect(page.locator(".page-footer")).to_contain_text("Update time:")
                expect(page.locator(".page-footer time")).to_have_count(2)
                expect(page.get_by_role("button", name="Edit metadata")).to_have_count(0)
                expect(page.get_by_role("tab")).to_have_count(5)
                expect(page.get_by_role("tab", name="People", exact=True)).to_have_count(0)
                expect(page.get_by_text("3 downstream tables", exact=True)).to_be_visible()
                page.locator(".owner-menu summary").click()
                page.get_by_role("button", name="Copy email address revenue@example.invalid", exact=True).click()
                expect(page.get_by_role("status")).to_have_text("Email address copied")
                assert page.evaluate("navigator.clipboard.readText()") == "revenue@example.invalid"
                page.locator(".owner-menu summary").click()
                page.screenshot(path=str(EVIDENCE / "meta-desktop.png"), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                page.get_by_role("combobox", name="Choose table").select_option("net_orders")
                expect(page.get_by_role("heading", name="net_orders", exact=True)).to_be_visible()
                page.get_by_role("combobox", name="Choose table").select_option("orders")
                expect(page.get_by_role("heading", name="orders", exact=True)).to_be_visible()
                page.screenshot(path=str(EVIDENCE / "meta-mobile.png"), full_page=True)
                page.set_viewport_size({"width": 1440, "height": 960})
                page.get_by_role("tab", name="Attributes").click()
                expect(page.get_by_role("cell", name="gross_amount DECIMAL(18,2)")).to_be_visible()
                page.get_by_role("tab", name="Lineage").click()
                expect(page.get_by_role("button", name="Explore analytics.net_orders")).to_be_visible()
                page.screenshot(path=str(EVIDENCE / "meta-lineage.png"), full_page=True)
                page.get_by_role("button", name="Explore analytics.net_orders").click()
                expect(page.get_by_role("heading", name="net_orders", exact=True)).to_be_visible()
                page.get_by_role("navigation", name="Tables").get_by_role("button", name="orders commerce").click()
                page.get_by_role("tab", name="Impact").click()
                page.get_by_role("combobox", name="Changed attribute").select_option("gross_amount")
                expect(page.get_by_role("button", name="reporting.daily_revenue")).to_be_visible()
                expect(page.get_by_role("button", name="reporting.channel_performance")).to_be_visible()
                page.get_by_role("button", name="Copy email address finance@example.invalid", exact=True).click()
                assert page.evaluate("navigator.clipboard.readText()") == "finance@example.invalid"
                expect(page.locator('a[href^="mailto:"]')).to_have_count(0)
                page.screenshot(path=str(EVIDENCE / "meta-impact.png"), full_page=True)
                page.get_by_role("combobox", name="Changed attribute").select_option("customer_id")
                expect(page.get_by_role("button", name="reporting.daily_revenue")).to_have_count(0)
                page.get_by_role("tab", name="Quality").click()
                expect(page.get_by_role("table")).to_be_visible()
                expect(page.get_by_role("row")).to_have_count(7)
                expect(page.get_by_text("99.84%", exact=True).first).to_be_visible()
                expect(page.get_by_text("3 downstream tables", exact=True)).to_be_visible()
                expect(page.get_by_role("status")).not_to_be_visible()
                page.screenshot(path=str(EVIDENCE / "meta-quality.png"), full_page=True)
                page.get_by_role("combobox", name="Quality result").select_option("issues")
                expect(page.get_by_role("row")).to_have_count(4)
                page.get_by_role("combobox", name="Quality severity").select_option("warn")
                expect(page.get_by_role("row")).to_have_count(2)
                page.get_by_role("button", name="View check Refund does not exceed order value", exact=True).click()
                expect(page.get_by_text("refund_amount <= gross_amount", exact=True)).to_be_visible()
                page.screenshot(path=str(EVIDENCE / "meta-quality-detail.png"), full_page=True)
                page.get_by_role("combobox", name="Quality severity").select_option("all")
                page.get_by_role("combobox", name="Quality result").select_option("all")
                page.locator(".quality-history summary").click()
                page.get_by_role("button", name="Select quality run 2026-11-13", exact=True).click()
                expect(page.get_by_role("combobox", name="Quality run").locator("option:checked")).to_contain_text("2026-11-13")
                expect(page.get_by_text("99.91%", exact=True).first).to_be_visible()
                page.get_by_role("combobox", name="Quality run").select_option(index=0)
                page.get_by_role("textbox", name="Search quality checks").fill("nonnegative")
                expect(page.get_by_role("row")).to_have_count(3)
                page.get_by_role("textbox", name="Search quality checks").fill("")
                page.get_by_role("navigation", name="Tables").get_by_role("button", name="customers commerce").click()
                expect(page.get_by_text("No recorded DQX runs for this table.", exact=True)).to_be_visible()
                page.get_by_role("navigation", name="Tables").get_by_role("button", name="orders commerce").click()
                page.get_by_role("button", name="Admin sign-in").click()
                page.get_by_label("Admin password").fill("incorrect")
                page.get_by_role("button", name="Sign in", exact=True).click()
                expect(page.get_by_role("alert")).to_have_text("Incorrect password")
                page.get_by_label("Admin password").fill(password)
                page.get_by_role("button", name="Sign in", exact=True).click()
                page.get_by_role("button", name="Edit metadata").click()
                expect(page.get_by_role("dialog")).to_be_visible()
                page.get_by_role("dialog").get_by_role("textbox", name="Business definition", exact=True).fill("Updated through the admin browser workflow.")
                page.get_by_role("button", name="Save changes").click()
                expect(page.get_by_role("dialog")).to_have_count(0)
                page.get_by_role("tab", name="Overview").click()
                expect(page.get_by_text("Updated through the admin browser workflow.", exact=True)).to_be_visible()
                page.reload()
                expect(page.get_by_text("Updated through the admin browser workflow.", exact=True)).to_be_visible()
                page.get_by_role("button", name="Sign out").click()
                expect(page.get_by_role("button", name="Edit metadata")).to_have_count(0)
                assets = context.request.get(url + "/api/assets").json()
                blocked = context.request.put(url + "/api/assets/" + assets[0]["id"], data=assets[0])
                assert blocked.status == 403
                # Keep the selected table and the whole page usable at phone width.
                page.set_viewport_size({"width": 390, "height": 844})
                for name in ("Overview", "Attributes", "Lineage", "Quality", "Impact"):
                    page.get_by_role("tab", name=name).click()
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), name
                    expect(page.locator("body")).not_to_contain_text(re.compile(r"sample data|sample workspace|sample results|curated sample|\batlas\b", re.I))
                    if name == "Quality":
                        page.screenshot(path=str(EVIDENCE / "meta-quality-mobile.png"), full_page=True)
                page.get_by_role("tab", name="Overview").click()
                assert not errors, errors
                browser.close()
            report = {"passed": True, "checks": ["reader controls", "five tabs with People merged into Impact", "compact owner contact menu", "owner and impact emails copy to clipboard", "no mailto navigation", "lineage navigation", "attribute impact", "compact DQX metrics table", "severity and result filtering", "historical run selection", "check search and recorded rule expansion", "no-result table state", "wrong password", "admin edit", "persistence after reload", "logout", "API rejects reader writes", "five mobile tabs without page overflow", "no browser exceptions"]}
            (EVIDENCE / "meta-browser.json").write_text(json.dumps(report, indent=2))
            print(json.dumps(report, indent=2))
        finally:
            server.terminate()
            server.wait(timeout=10)


if __name__ == "__main__":
    main()
