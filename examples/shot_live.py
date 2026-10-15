# -*- coding: utf-8 -*-
"""shot_live.py — screenshot the LIVE panel driven by the clone backend.

Usage: python examples/shot_live.py <token_file> <out_png> [--wait 14]
Opens http://127.0.0.1:8770/panel, injects token, clicks "Запустить модуль"
(neuro_commenting), waits for streaming logs, saves PNG.
"""
import sys
import time

from playwright.sync_api import sync_playwright


def main():
    tok_file, out = sys.argv[1], sys.argv[2]
    wait = 14
    if "--wait" in sys.argv:
        wait = int(sys.argv[sys.argv.index("--wait") + 1])
    token = open(tok_file, encoding="utf-8").read().strip()
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=True)
        pg = br.new_page(viewport={"width": 1440, "height": 940},
                         locale="ru-RU",
                         user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36")
        pg.goto("http://127.0.0.1:8770/panel", wait_until="load")
        pg.evaluate("t => localStorage.setItem('gg_token', t)", token)
        pg.reload(wait_until="load")
        pg.wait_for_timeout(2500)  # connect() -> me -> first task refresh
        # launch a live task
        pg.evaluate("() => { document.getElementById('module').value = 'neuro_commenting'; launch(); }")
        time.sleep(wait)
        rows = pg.evaluate("() => document.querySelectorAll('.tm-log-row').length")
        cards = pg.evaluate("() => document.querySelectorAll('.tm-card').length")
        sub = pg.evaluate("() => document.getElementById('sub').textContent")
        pg.screenshot(path=out, full_page=False)
        print(f"saved {out} | log_rows={rows} task_cards={cards} | sub='{sub}'")
        br.close()


if __name__ == "__main__":
    main()
