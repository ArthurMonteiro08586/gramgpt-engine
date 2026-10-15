# -*- coding: utf-8 -*-
"""run_server.py — start the GramGPT clone backend with demo data seeded.

Usage: python examples/run_server.py [--port 8770] [--db :memory:|path.db] [--speed 4]
Prints the demo token. Panel: http://127.0.0.1:8770/panel
"""
import argparse
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gramgpt_server import Server, auth  # noqa: E402

FIRST = ["Алексей", "Мария", "Дмитрий", "Ольга", "Иван", "Ксения", "Павел",
         "Анна", "Сергей", "Юлия", "Никита", "Дарья", "Артём", "Полина"]
LAST = ["smirnov", "kuznetsov", "popov", "sokolov", "volkov", "morozov",
        "zaytsev", "ivanov", "fedorov", "nikitin"]


def seed(store, token):
    u = store.row("SELECT * FROM users WHERE token=?", (token,))
    rng = random.Random(42)
    n = store.row("SELECT COUNT(*) n FROM accounts WHERE user_id=?", (u["id"],))["n"]
    if n:
        return n
    for i in range(30):
        store.insert("accounts", user_id=u["id"],
                     phone=f"+380{rng.randrange(67, 99)}{rng.randrange(10000000, 99999999)}",
                     username=(LAST[i % len(LAST)] + str(i) if i % 3 == 0 else None),
                     first_name=rng.choice(FIRST),
                     status=rng.choices(["active", "quarantined", "spamblocked", "frozen"],
                                        [24, 2, 2, 2])[0],
                     stage=rng.choice(["new", "warming", "warmed", "active", "trusted", "veteran"]),
                     ggr=round(4 + rng.random() * 6, 1),
                     ggr_tier=None, premium=int(rng.random() < 0.15),
                     proxy=None, project=None,
                     created=store.now() - rng.randrange(0, 90) * 86400, meta=None)
    return 30


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--db", default=":memory:")
    ap.add_argument("--speed", type=float, default=4.0)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    srv = Server(db=a.db, speed=a.speed)
    token = auth.issue_token(srv.store, username="alex_smirnov", plan="basic",
                             quota_total=1000, balance=1284.50,
                             token=("ggk_" + "live_clone_demo_alex_smirnov"))
    n = seed(srv.store, token)
    print(f"[seed] user alex_smirnov, accounts={n}")
    print(f"[demo-token] {token}")
    srv.serve(host=a.host, port=a.port, block=True)


if __name__ == "__main__":
    main()
