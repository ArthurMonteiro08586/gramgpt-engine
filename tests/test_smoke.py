# -*- coding: utf-8 -*-
"""Smoke tests — engine invariants (run: python -m unittest discover -s tests)."""
import random
import unittest
from datetime import datetime, timedelta

from gramgpt_engine import (Account, AccountSignals, C, DailyLimits, Engine,
                            PaceLimiter, Persona, PmTask, PoolRotator,
                            QuarantineManager, ShillingTask, build_scenario,
                            chain_plan, claim_target, day_plan, gate, lot_verdict,
                            maybe_ai_delay, plan_day, preflight_run_all,
                            replica_delay, risk_assessment, score_account,
                            warming_allowed, young_comment_delay, account_op_validate)


class TestAiProtection(unittest.TestCase):
    def test_sleep_window_blocks(self):
        ok, reason = gate(datetime(2026, 10, 14, 3, 0))
        self.assertFalse(ok)
        self.assertEqual(reason, "ai_protection_sleep")

    def test_break_windows(self):
        for h, frag in ((7, "early_morning"), (13, "lunch_time"), (23, "late_evening")):
            ok, reason = gate(datetime(2026, 10, 14, h, 30))
            self.assertFalse(ok, f"hour {h}")
            self.assertIn(frag, reason)

    def test_day_allowed(self):
        ok, _ = gate(datetime(2026, 10, 14, 15, 0))
        self.assertTrue(ok)

    def test_ai_delay_bounds(self):
        rng = random.Random(42)
        for _ in range(500):
            d = maybe_ai_delay(rng)
            self.assertTrue(d == 0.0 or C.AI_DELAY_RANGE[0] <= d <= C.AI_DELAY_RANGE[1])


class TestWarming(unittest.TestCase):
    def test_stages(self):
        now = datetime(2026, 10, 14, 12, 0)
        for days, stage in ((1, "new"), (5, "warming"), (20, "warmed"),
                            (40, "active"), (70, "trusted"), (100, "veteran")):
            a = Account(1, "+1", now - timedelta(days=days))
            self.assertEqual(a.stage(now), stage)

    def test_young_comment_rule(self):
        now = datetime(2026, 10, 14, 12, 0)
        a = Account(1, "+1", now - timedelta(days=1))
        a.comments_sent = 3
        a.last_used = now - timedelta(minutes=30)
        wait = young_comment_delay(a, now)
        self.assertIsNotNone(wait)
        self.assertEqual(wait, timedelta(minutes=42))
        a.comments_sent = 12
        self.assertIsNone(young_comment_delay(a, now))

    def test_risk_rules(self):
        now = datetime(2026, 10, 14, 12, 0)
        fresh = Account(1, "+1", now - timedelta(days=1))
        self.assertEqual(risk_assessment(fresh, "aggressive", 10, now)[0], "critical")
        mid = Account(2, "+2", now - timedelta(days=7))
        self.assertEqual(risk_assessment(mid, "aggressive", 10, now)[0], "high")
        old = Account(3, "+3", now - timedelta(days=60))
        self.assertEqual(risk_assessment(old, "aggressive", 10, now)[0], "ok")


class TestFlood(unittest.TestCase):
    def test_quarantine_24h(self):
        now = datetime(2026, 10, 14, 12, 0)
        a = Account(1, "+1", now)
        qm = QuarantineManager()
        qm.handle_flood(a, 3600, now)
        self.assertEqual(a.quarantine_until, now + timedelta(hours=24))
        rot = PoolRotator([a])
        self.assertIsNone(rot.next(now))
        self.assertTrue(rot.all_flooded(now))
        qm.release_expired([a], now + timedelta(hours=25))
        self.assertIsNotNone(rot.next(now + timedelta(hours=25)))


class TestPacing(unittest.TestCase):
    def test_curve_ratio(self):
        peak = max(C.ACTIVITY_WEIGHTS)
        trough = min(w for w in C.ACTIVITY_WEIGHTS if w > 0)
        self.assertGreaterEqual(peak / trough, 10)  # docs say up to 19x

    def test_pace_presets(self):
        rng = random.Random(1)
        d = replica_delay("calm", 12, rng, even_pace=True)
        self.assertTrue(C.PACE_PRESETS["calm"] * 0.3 <= d <= C.PACE_PRESETS["calm"] * 3 * 1.4)


class TestPreflight(unittest.TestCase):
    def test_identical_broadcast(self):
        r = preflight_run_all([], {"total": 10, "dead": 0}, ["same text"] * 6)
        self.assertFalse(r["allow_launch"])
        self.assertIn("identical_broadcast", r["blocked_by"])

    def test_lot_burn(self):
        r = preflight_run_all([], {"total": 10, "dead": 6}, ["a", "b", "c"])
        self.assertIn("lot_burn", r["blocked_by"])

    def test_clean_passes(self):
        r = preflight_run_all([{"id": 1, "ggr_meta": {"shadow_fraud": {"supplier_fraud": False, "authkey_cross_user_dups": 0}}}],
                              {"total": 10, "dead": 0}, ["a", "b", "c", "d"])
        self.assertTrue(r["allow_launch"])


class TestShilling(unittest.TestCase):
    def test_scenario_24_steps(self):
        t = ShillingTask(target="chat", subject="product",
                         personas=[Persona("A", "initiator"), Persona("B", "supporter")])
        steps = build_scenario(t, random.Random(7))
        self.assertEqual(len(steps), C.SCENARIO_STEPS)
        self.assertTrue(all(s.delay_before > 0 for s in steps))

    def test_even_pace_flat(self):
        t = ShillingTask(target="c", subject="s", personas=[Persona("A", "initiator")],
                         even_pace=True, daily_budget=48)
        plan = plan_day(t)
        self.assertEqual(plan[3], plan[20])


class TestSpamPm(unittest.TestCase):
    def test_lifetime_48h(self):
        t = PmTask(name="x", texts=["a"], targets=["u1"])
        t.created = datetime.now() - timedelta(hours=49)
        self.assertFalse(t.alive())

    def test_chain_bounds(self):
        rng = random.Random(3)
        for _ in range(100):
            self.assertIn(chain_plan(rng), (2, 3, 4))

    def test_dedup(self):
        t = PmTask(name="x", texts=["a"], targets=["u1", "u2"])
        self.assertTrue(claim_target(t, "u1"))
        self.assertFalse(claim_target(t, "u1"))

    def test_pace_limiter(self):
        t = PmTask(name="x", texts=["a"], targets=[], hourly_limit=2, daily_limit=3)
        lim = PaceLimiter(t)
        now = datetime(2026, 10, 14, 15, 30)
        self.assertTrue(lim.allow("acc1", now)[0])
        lim.register("acc1", now)
        lim.register("acc1", now)
        ok, reason, pause = lim.allow("acc1", now)
        self.assertFalse(ok)
        self.assertEqual(reason, "hourly_slot_pause")
        self.assertEqual(pause, 1800)


class TestGgr(unittest.TestCase):
    def test_fresh_clean_account(self):
        v = score_account(AccountSignals(age_days=200, has_2fa=True, has_username=True,
                                         has_photo=True, actions_last_7d=40))
        self.assertGreaterEqual(v.score, 7.5)
        self.assertEqual(v.tier, "good" if v.score < 9.0 else "excellent")
        self.assertEqual(len(v.shap), 7)
        self.assertEqual(set(v.shap), set(C.GGR_SHAP_GROUPS))

    def test_fraud_account_penalized(self):
        v = score_account(AccountSignals(age_days=1, authkey_dups=3, lot_dead_rate=0.8,
                                         spamblock_history=1, proxy_shared=10))
        self.assertLess(v.score, 3.5)
        self.assertTrue(v.meta["shadow_fraud"]["supplier_fraud"])

    def test_lot_verdict(self):
        self.assertTrue(lot_verdict(10, 6)["burn"])
        self.assertFalse(lot_verdict(71, 0)["burn"])


class TestAccountOp(unittest.TestCase):
    def test_validation(self):
        self.assertEqual(account_op_validate("check", [1]), None)
        self.assertIn("unknown_op", account_op_validate("hack", [1]) or "")
        self.assertIn("confirm", account_op_validate("reset_sessions", [1], {}) or "")
        self.assertEqual(account_op_validate("reset_sessions", [1], {"confirm": True}), None)
        self.assertIn("username_pool", account_op_validate(
            "generate_profiles", [1, 2], {"username_pool": ["only_one"]}) or "")

    def test_dry_run(self):
        e = Engine()
        r = e.run("check", [1, 2, 3])
        self.assertEqual(r.ok, [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
