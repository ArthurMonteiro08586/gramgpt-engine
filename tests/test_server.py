# -*- coding: utf-8 -*-
"""test_server.py — e2e tests for the GramGPT clone backend.

Boots Server in-process on an ephemeral port, exercises: auth, me, accounts,
launch validation (422), launch_neuro_commenting happy path, worker execution,
task logs polling, cancel_task, GGR check, photos/prompts/proxies/blacklists/
webhooks/stats/history, 404/405/401 routing, openapi + panel serving.
"""
import json
import os
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gramgpt_server import Server, auth  # noqa: E402

PORT = 8791
BASE = f"http://127.0.0.1:{PORT}"


TOKEN = None


def req(method, path, body=None, token=TOKEN, expect=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            code, raw = resp.status, resp.read()
    except urllib.error.HTTPError as e:
        code, raw = e.code, e.read()
    ctype = "json"
    if raw[:1] in (b"<",):
        ctype = "html"
    parsed = raw if ctype == "html" else json.loads(raw or b"{}")
    if expect is not None:
        assert code == expect, f"{method} {path} -> {code} (want {expect}): {str(parsed)[:200]}"
    return code, parsed


class TestServerE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = Server(db=":memory:", speed=40.0)
        global TOKEN
        cls.token = TOKEN = auth.issue_token(cls.srv.store, username="tester", plan="basic",
                                     quota_total=1000, balance=10.0)
        for i in range(8):
            cls.srv.store.insert("accounts", user_id=1, phone=f"+38097000000{i}",
                                 username=f"u{i}", first_name="T", status="active",
                                 stage="warmed", ggr=None, ggr_tier=None, premium=0,
                                 proxy=None, project=None, created=cls.srv.store.now() - 40 * 86400,
                                 meta=None)
        cls.srv.serve(port=PORT, block=False)
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_01_health_meta(self):
        req("GET", "/healthz", token=TOKEN, expect=200)
        c, spec = req("GET", "/api/v1/openapi.json", token=TOKEN, expect=200)
        self.assertIn("paths", spec if isinstance(spec, dict) else {})
        c, html = req("GET", "/panel", token=TOKEN, expect=200)
        self.assertIn(b"tm-root", html)

    def test_02_auth_gates(self):
        req("GET", "/api/v1/me/", token=None, expect=401)
        req("GET", "/api/v1/me/", token="ggk_live_badtoken", expect=401)
        c, me = req("GET", "/api/v1/me/", token=TOKEN, expect=200)
        self.assertEqual(me["username"], "tester")
        self.assertEqual(me["plan"], "basic")

    def test_03_routing(self):
        req("GET", "/api/v1/nonexistent/", token=TOKEN, expect=404)
        req("DELETE", "/api/v1/me/", token=TOKEN, expect=405)

    def test_04_accounts(self):
        c, d = req("GET", "/api/v1/accounts/", token=TOKEN, expect=200)
        self.assertEqual(d["total"], 8)
        ids = [a["id"] for a in d["items"]]
        c, a = req("GET", f"/api/v1/accounts/{ids[0]}/", token=TOKEN, expect=200)
        self.assertEqual(a["id"], ids[0])
        req("GET", "/api/v1/accounts/99999/", token=TOKEN, expect=404)
        c, d = req("GET", "/api/v1/accounts/?search=u3", token=TOKEN, expect=200)
        self.assertEqual(d["total"], 1)

    def test_05_launch_validation_422(self):
        c, d = req("POST", "/api/v1/tools/launch_mass_react/",
                   body={"account_ids": []}, token=TOKEN, expect=422)
        self.assertIn("detail", d)
        c, d = req("POST", "/api/v1/tools/launch_neuro_commenting/",
                   body={"account_ids": [99999]}, token=TOKEN, expect=422)

    def test_06_launch_and_worker(self):
        ids = [a["id"] for a in req("GET", "/api/v1/accounts/", token=TOKEN)[1]["items"][:5]]
        c, t = req("POST", "/api/v1/tools/launch_neuro_commenting/",
                   body={"account_ids": ids, "queue_if_busy": True},
                   token=TOKEN, expect=200)
        tid = t["task_id"]
        self.assertEqual(t["status"], "waiting")
        deadline = time.time() + 25
        final = None
        logs_seen = 0
        while time.time() < deadline:
            c, s = req("GET", f"/api/v1/tasks/{tid}/", token=TOKEN, expect=200)
            c, lg = req("GET", f"/api/v1/tasks/{tid}/logs/?limit=500", token=TOKEN, expect=200)
            logs_seen = max(logs_seen, len(lg["items"]))
            if s["status"] in ("completed", "failed"):
                final = s
                break
            time.sleep(0.4)
        self.assertIsNotNone(final, "task did not finish in 25s")
        self.assertEqual(final["status"], "completed")
        self.assertGreaterEqual(logs_seen, 10)
        c, res = req("GET", f"/api/v1/tasks/{tid}/results/", token=TOKEN, expect=200)
        self.assertGreaterEqual(res["completed"], 1)

    def test_07_cancel(self):
        ids = [a["id"] for a in req("GET", "/api/v1/accounts/", token=TOKEN)[1]["items"][:3]]
        c, t = req("POST", "/api/v1/tools/launch_bulk_join/",
                   body={"account_ids": ids, "channels": ["@x"]},
                   token=TOKEN, expect=200)
        c, d = req("POST", "/api/v1/tools/cancel_task/",
                   body={"task_id": t["task_id"]}, token=TOKEN, expect=200)
        self.assertEqual(d["status"], "cancelled")
        req("POST", "/api/v1/tools/cancel_task/", body={"task_id": t["task_id"]},
            token=TOKEN, expect=409)

    def test_08_ggr(self):
        ids = [a["id"] for a in req("GET", "/api/v1/accounts/", token=TOKEN)[1]["items"][:3]]
        c, d = req("POST", "/api/v1/tools/check_account_ggr/",
                   body={"account_ids": ids}, token=TOKEN, expect=200)
        self.assertEqual(len(d["items"]), 3)
        for it in d["items"]:
            self.assertIn("score", it)
            self.assertIn(it["tier"], ("EXCELLENT", "GOOD", "FAIR", "RISKY", "DEAD"))
        c, g = req("GET", f"/api/v1/accounts/{ids[0]}/ggr/", token=TOKEN, expect=200)
        self.assertIn("risk_probability", g)

    def test_09_crud_groups(self):
        # photos
        c, d = req("POST", "/api/v1/photos/", body={"urls": ["http://x/1.jpg", "http://x/2.jpg"]},
                   token=TOKEN, expect=200)
        pid = d["created"][0]
        req("GET", "/api/v1/photos/", token=TOKEN, expect=200)
        req("GET", "/api/v1/photos/quota/", token=TOKEN, expect=200)
        req("GET", "/api/v1/photos/random/", token=TOKEN, expect=200)
        req("POST", f"/api/v1/photos/{pid}/use/", body={}, token=TOKEN, expect=200)
        req("DELETE", f"/api/v1/photos/{pid}/", token=TOKEN, expect=200)
        # prompts
        c, d = req("POST", "/api/v1/prompts/", body={"name": "p1", "text": "hello {chat}"},
                   token=TOKEN, expect=200)
        req("PATCH", f"/api/v1/prompts/{d['id']}/", body={"text": "hi"}, token=TOKEN, expect=200)
        req("GET", "/api/v1/prompts/", token=TOKEN, expect=200)
        # proxies
        cls_ = self.srv.store
        cls_.insert("proxies", user_id=1, url="socks5://1.2.3.4:1080", kind="socks5",
                    alive=1, attached_to=None, last_check=None)
        req("GET", "/api/v1/proxies/", token=TOKEN, expect=200)
        req("POST", "/api/v1/proxies/check/", body={}, token=TOKEN, expect=200)
        req("POST", "/api/v1/proxies/attach/", body={"proxy_id": 1, "account_ids": [1]},
            token=TOKEN, expect=200)
        req("POST", "/api/v1/proxies/detach/", body={"proxy_id": 1}, token=TOKEN, expect=200)
        # blacklists
        req("POST", "/api/v1/blacklists/peers/", body={"values": ["@bad1"]},
            token=TOKEN, expect=200)
        c, d = req("GET", "/api/v1/blacklists/peers/", token=TOKEN, expect=200)
        self.assertEqual(len(d["items"]), 1)
        req("DELETE", "/api/v1/blacklists/peers/", body={"values": ["@bad1"]},
            token=TOKEN, expect=200)
        # webhooks
        c, d = req("POST", "/api/v1/webhooks/", body={"url": "http://cb.local/hook"},
                   token=TOKEN, expect=200)
        wid = d["id"]
        req("GET", "/api/v1/webhooks/", token=TOKEN, expect=200)
        req("GET", f"/api/v1/webhooks/{wid}/deliveries/", token=TOKEN, expect=200)
        req("POST", f"/api/v1/webhooks/{wid}/deliveries/1/redeliver/", body={},
            token=TOKEN, expect=404)
        req("PATCH", f"/api/v1/webhooks/{wid}/", body={"active": False}, token=TOKEN, expect=200)
        req("DELETE", f"/api/v1/webhooks/{wid}/", token=TOKEN, expect=200)
        # stats/history/meta/media/tools-index
        req("GET", "/api/v1/stats/accounts/", token=TOKEN, expect=200)
        req("GET", "/api/v1/stats/activity/?days=3", token=TOKEN, expect=200)
        req("GET", "/api/v1/history/", token=TOKEN, expect=200)
        req("GET", "/api/v1/changelog/", token=TOKEN, expect=200)
        c, d = req("POST", "/api/v1/media/", body={"filename": "a.png", "data_base64": "AA=="},
                   token=TOKEN, expect=200)
        self.assertIn("media_id", d)
        c, d = req("GET", "/api/v1/tools/", token=TOKEN, expect=200)
        self.assertEqual(len(d["items"]), 13)

    def test_10_all_launch_modules_validate(self):
        """every one of 13 launch endpoints reachable + envelope enforced"""
        ids = [a["id"] for a in req("GET", "/api/v1/accounts/", token=TOKEN)[1]["items"][:2]]
        mods = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                           "gramgpt_server", "routes_spec.json"), encoding="utf-8"))
        launch = [r["path"] for r in mods if r["path"].startswith("/api/v1/tools/launch_")]
        self.assertEqual(len(launch), 13)
        for p in launch:
            req("POST", p, body={}, token=TOKEN, expect=422)   # envelope rejected
            req("POST", p, body={"account_ids": ["x"]}, token=TOKEN, expect=422)

    def test_11_balance_and_quota(self):
        c, d = req("POST", "/api/v1/tools/check_balance/", body={}, token=TOKEN, expect=200)
        self.assertEqual(d["balance"], 10.0)
        self.assertGreaterEqual(d["quota_used"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
