# -*- coding: utf-8 -*-
"""test_modules.py — contract tests for the 8 remaining launch modules."""
import random
import unittest

from gramgpt_engine import modules as M


class TestEnvelope(unittest.TestCase):
    def test_envelope_min_accounts(self):
        self.assertIsNotNone(M.validate_envelope({"account_ids": []}))
        self.assertIsNone(M.validate_envelope({"account_ids": [1]}))

    def test_envelope_flags_bool(self):
        self.assertIsNotNone(M.validate_envelope({"account_ids": [1], "dry_run": "yes"}))

    def test_module_registry_13(self):
        self.assertEqual(len(M.MODULES), 13)
        for path in M.MODULES.values():
            self.assertTrue(path.startswith("/api/v1/tools/launch_"))


class TestMassReact(unittest.TestCase):
    def test_validate(self):
        self.assertIsNone(M.validate_mass_react(
            {"account_ids": [1], "channels": ["@x"], "reactions": ["👍"]}))
        self.assertIsNotNone(M.validate_mass_react({"account_ids": [1], "channels": []}))
        self.assertIsNotNone(M.validate_mass_react(
            {"account_ids": [1], "channels": ["@x"],
             "config": {"min_delay_seconds": 60, "max_delay_seconds": 15}}))

    def test_plan_delays_in_window(self):
        rng = random.Random(7)
        plan = M.plan_mass_react([1, 2], ["@a"], ["👍", "🔥"],
                                 {"min_delay_seconds": 15, "max_delay_seconds": 60}, rng)
        self.assertEqual(len(plan), 4)          # 2 acc * 1 ch * 2 reactions
        prev = {}
        for p in plan:
            last = prev.get(p["account"])
            if last is not None:
                self.assertGreaterEqual(p["at_sec"] - last, 14.9)
                self.assertLessEqual(p["at_sec"] - last, 60.1)
            prev[p["account"]] = p["at_sec"]


class TestMassLooking(unittest.TestCase):
    def test_validate(self):
        self.assertIsNone(M.validate_mass_looking({"account_ids": [1], "peers": ["@x"]}))
        self.assertIsNotNone(M.validate_mass_looking({"account_ids": [1], "peers": []}))

    def test_plan(self):
        plan = M.plan_mass_looking([1], ["@a", "@b"], like=True)
        self.assertEqual(len(plan), 2)
        self.assertTrue(all(p["action"] == "view+like" for p in plan))


class TestNeuroChatting(unittest.TestCase):
    def test_validate_modes(self):
        base = {"account_ids": [1], "chats": ["@c"]}
        self.assertIsNone(M.validate_neuro_chatting(base))
        self.assertIsNotNone(M.validate_neuro_chatting({**base, "config": {"work_mode": "x"}}))
        self.assertIsNotNone(M.validate_neuro_chatting(
            {**base, "config": {"work_mode": "time", "duration_minutes": 0}}))
        self.assertIsNotNone(M.validate_neuro_chatting(
            {**base, "config": {"reaction_mode": "keywords"}}))       # keywords missing
        self.assertIsNone(M.validate_neuro_chatting(
            {**base, "config": {"reaction_mode": "keywords", "keywords": ["купить"]}}))

    def test_plan_count_mode(self):
        rng = random.Random(1)
        plan = M.plan_neuro_chatting([1], ["@c"], {"work_mode": "count", "max_messages": 5,
                                                   "min_delay_seconds": 30,
                                                   "max_delay_seconds": 120}, rng)
        self.assertEqual(len(plan), 5)
        self.assertTrue(plan[-1]["at_sec"] > plan[0]["at_sec"])


class TestNeuroDialogs(unittest.TestCase):
    def test_validate_protection_level(self):
        self.assertIsNone(M.validate_neuro_dialogs({"account_ids": [1]}))
        self.assertIsNone(M.validate_neuro_dialogs(
            {"account_ids": [1], "config": {"accountProtectionLevel": "сбалансированный"}}))
        self.assertIsNotNone(M.validate_neuro_dialogs(
            {"account_ids": [1], "config": {"accountProtectionLevel": "yolo"}}))


class TestGroupSpammer(unittest.TestCase):
    def test_validate(self):
        self.assertIsNone(M.validate_group_spammer(
            {"account_ids": [1], "targets": ["@t"], "chain": [{"text": "hi"}]}))
        self.assertIsNotNone(M.validate_group_spammer(
            {"account_ids": [1], "chain": [{"text": "hi"}]}))          # no targets/folders
        self.assertIsNotNone(M.validate_group_spammer(
            {"account_ids": [1], "targets": ["@t"], "chain": []}))
        self.assertIsNotNone(M.validate_group_spammer(
            {"account_ids": [1], "targets": ["@t"], "chain": ["plain"]}))

    def test_plan_chain_order(self):
        chain = [{"text": "a"}, {"text": "b"}, {"text": "c"}]
        plan = M.plan_group_spammer([1], ["@t", "@u"], chain)
        self.assertEqual(len(plan), 6)
        self.assertEqual([p["chain_pos"] for p in plan[:3]], [0, 1, 2])

    def test_folder_dedup(self):
        plan = M.plan_group_spammer([1], ["@t"], [{"text": "x"}], folder_chats=["@t", "@f"])
        self.assertEqual(len({p["chat"] for p in plan}), 2)


class TestBulkJoin(unittest.TestCase):
    def test_validate(self):
        self.assertIsNone(M.validate_bulk_join({"account_ids": [1], "channels": ["@c"]}))
        self.assertIsNotNone(M.validate_bulk_join({"account_ids": [1], "channels": []}))

    def test_plan(self):
        plan = M.plan_bulk_join([1, 2], ["@a", "@b"], folder="work")
        self.assertEqual(len(plan), 4)
        self.assertTrue(all(p["folder"] == "work" for p in plan))


class TestCheckNumbers(unittest.TestCase):
    def test_validate_e164(self):
        self.assertIsNone(M.validate_check_numbers({"account_ids": [1], "targets": ["+380961234567"]}))
        self.assertIsNotNone(M.validate_check_numbers({"account_ids": [1], "targets": []}))
        self.assertIsNotNone(M.validate_check_numbers({"account_ids": [1], "targets": ["380961234567"]}))
        self.assertIsNotNone(M.validate_check_numbers({"account_ids": [1], "targets": ["+abc"]}))


class TestParsing(unittest.TestCase):
    def test_kind_enum(self):
        self.assertIsNotNone(M.validate_parsing({"account_ids": [1], "kind": "bogus"}))
        for kind in M.PARSE_KINDS:
            p = {"account_ids": [1], "kind": kind}
            if kind in ("users", "messages", "comments"):
                p["targets"] = ["@t"]
            if kind == "groups":
                p["search_keywords"] = ["crypto"]
            self.assertIsNone(M.validate_parsing(p), kind)

    def test_targets_required(self):
        self.assertIsNotNone(M.validate_parsing({"account_ids": [1], "kind": "users"}))
        self.assertIsNotNone(M.validate_parsing({"account_ids": [1], "kind": "groups"}))

    def test_channel_modes(self):
        self.assertIsNotNone(M.validate_parsing(
            {"account_ids": [1], "kind": "channels", "config": {"mode": "similar"}}))
        self.assertIsNone(M.validate_parsing(
            {"account_ids": [1], "kind": "channels",
             "config": {"mode": "similar", "seed_links": ["https://t.me/x"]}}))
        self.assertIsNotNone(M.validate_parsing(
            {"account_ids": [1], "kind": "channels", "config": {"mode": "parse"}}))
        self.assertIsNone(M.validate_parsing(
            {"account_ids": [1], "kind": "channels", "targets": ["@x"],
             "config": {"mode": "parse"}}))

    def test_limit_keys(self):
        self.assertEqual(M.parse_result_shape("users")["limit_keys"], ["members_limit"])
        self.assertEqual(M.parse_result_shape("comments")["limit_keys"],
                         ["posts_limit", "comments_per_post"])
        self.assertEqual(M.parse_result_shape("groups")["limit_keys"], ["results_limit"])

    def test_bool_options(self):
        self.assertIsNotNone(M.validate_parsing(
            {"account_ids": [1], "kind": "users", "targets": ["@t"],
             "config": {"skip_bots": "yes"}}))


if __name__ == "__main__":
    unittest.main()
