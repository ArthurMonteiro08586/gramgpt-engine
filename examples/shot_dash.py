# -*- coding: utf-8 -*-
"""shot_dash.py — render examples/dashboard.html to PNG via playwright chromium."""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

html = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1280, "height": 900}, locale="ru-RU")
    pg.goto(html.as_uri())
    pg.wait_for_timeout(500)
    pg.screenshot(path=str(out), full_page=True)
    b.close()
print(f"shot: {out} {out.stat().st_size} bytes")
