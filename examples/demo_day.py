# -*- coding: utf-8 -*-
"""demo_day.py — simulate one engine day: gating, warming, shilling scenario,
spam_pm day plan, preflight, GGR scoring, FloodWait quarantine. stdlib-only.

Run: python examples/demo_day.py
"""
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gramgpt_engine import (C, Account, AccountSignals, DailyLimits, Engine,
                            PaceLimiter, Persona, PmTask, PoolRotator,
                            QuarantineManager, ShillingTask, build_scenario,
                            chain_plan, claim_target, day_plan, gate,
                            lot_verdict, maybe_ai_delay, plan_day,
                            preflight_run_all, replica_delay, risk_assessment,
                            score_account, warming_allowed, young_comment_delay)


def main():
    rng = random.Random(20261014)
    now = datetime(2026, 10, 14, 12, 0)
    print(f"== GramGPT engine demo — {now} ==\n")

    # 1. Fleet of accounts at different ages
    fleet = [
        Account(1, "+10000000001", now - timedelta(days=95)),   # veteran
        Account(2, "+10000000002", now - timedelta(days=40)),   # active
        Account(3, "+10000000003", now - timedelta(days=10)),   # warming
        Account(4, "+10000000004", now - timedelta(days=1)),    # new
    ]
    print("-- fleet --")
    for a in fleet:
        stage = a.stage(now)
        lvl, msg = risk_assessment(a, "balanced", 5, now)
        print(f"  acc{a.id} age={a.age_days(now):.0f}d stage={stage:8s} "
              f"budget={a.budget(now):3d}/day risk={lvl or 'ok'}")

    # 2. ai_protection gates through the day
    print("\n-- ai_protection gates (every 2h) --")
    for h in range(0, 24, 2):
        t = datetime(2026, 10, 14, h, 30)
        ok, reason = gate(t)
        print(f"  {h:02d}:30 {'ALLOW' if ok else 'BLOCK':5s} {reason}")

    # 3. shilling scenario
    task = ShillingTask(target="@example_chat", subject="product X",
                        personas=[Persona("Viktor", "initiator"),
                                  Persona("Alina", "supporter"),
                                  Persona("Marat", "skeptic")],
                        pace="live")
    steps = build_scenario(task, rng, start_hour=15)
    print(f"\n-- neuro_shilling scenario: {len(steps)} steps --")
    for s in steps[:8]:
        print(f"  step{s.n:2d} {s.persona:7s} ({s.role:9s}) {s.action:8s} "
              f"delay={s.delay_before:6.1f}s")
    print(f"  ... ({len(steps)-8} more)")
    plan = plan_day(task)
    print(f"  day budget 60 -> peak hour 20:00 = {plan[20]}/h, night 03:00 = {plan[3]}/h")

    # 4. spam_pm
    pm = PmTask(name="offer wave", texts=["offer A", "offer B", "offer C"],
                targets=[f"user{i}" for i in range(500)],
                hourly_limit=12, daily_limit=40)
    dp = day_plan(pm, ["acc1", "acc2"], now)
    print(f"\n-- spam_pm day plan --\n  {dp}")
    lim = PaceLimiter(pm)
    acc_ok = lim.allow("acc1", now)
    print(f"  acc1 pace check: {acc_ok}")
    print(f"  chain lengths sample: {[chain_plan(rng) for _ in range(6)]}")
    print(f"  dedup: claim user7 -> {claim_target(pm,'user7')}, again -> {claim_target(pm,'user7')}")

    # 5. preflight
    pre = preflight_run_all([{"id": 1, "ggr_meta": {}}], {"total": 71, "dead": 0},
                            [f"text {i}" for i in range(6)])
    print(f"\n-- preflight --\n  allow_launch={pre['allow_launch']} blocked_by={pre['blocked_by']}")
    bad = preflight_run_all([], {"total": 10, "dead": 7}, ["same"] * 8)
    print(f"  bad lot + identical: allow={bad['allow_launch']} blocked={bad['blocked_by']}")

    # 6. GGR scoring (local clone)
    print("\n-- GGR local scorer --")
    good = score_account(AccountSignals(age_days=200, has_2fa=True, has_username=True,
                                        has_photo=True, actions_last_7d=40), now)
    bad_a = score_account(AccountSignals(age_days=1, authkey_dups=3, lot_dead_rate=0.8,
                                         spamblock_history=1, proxy_shared=10), now)
    for v in (good, bad_a):
        print(f"  score={v.score} tier={v.tier:9s} risk={v.risk_probability} "
              f"rec={v.recommendation['headline_key']}")
    print(f"  lot(71,0) -> {lot_verdict(71, 0)}")

    # 7. flood quarantine + rotation
    print("\n-- flood handling --")
    qm = QuarantineManager()
    e = qm.handle_flood(fleet[2], wait_seconds=3600, now=now)
    print(f"  acc3 quarantined until {e['until']}")
    rot = PoolRotator(fleet)
    avail = rot.available(now + timedelta(minutes=1))
    print(f"  pool available now: {[a.id for a in avail]} (acc3 parked)")
    allowed, why = warming_allowed(fleet[2], now)
    print(f"  warming_allowed(acc3): {allowed} ({why})")

    # 8. account_op dispatch (dry-run)
    eng = Engine()
    r = eng.run("check", [a.id for a in fleet])
    print(f"\n-- account_op dry-run --\n  {r.as_dict()}")
    print(f"  generate_profiles username assign: {Engine().run('generate_profiles',[1,2],{'username_pool':['aaa','bbb']}).ok}")

    print("\nDEMO OK")


if __name__ == "__main__":
    main()
