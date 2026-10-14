# -*- coding: utf-8 -*-
"""client — API client for the GramGPT public API (OpenAPI 3.0.3, 92 endpoints).

stdlib-only (urllib). Auth: Bearer ggk_live_* key from the panel.
Base: https://gramgpt.io/api/v1/  |  MCP: https://gramgpt.io/mcp/  |  WS: wss://api.gramgpt.io

This client speaks the ORIGINAL service contract (useful for automation against
a legit subscription). It is intentionally transport-thin: every endpoint is
reachable via call()/tools_launch().
"""
import json
import urllib.error
import urllib.request

BASE = "https://gramgpt.io/api/v1"

# core endpoint groups (full 92-path map lives in the reverse kit repo)
ENDPOINTS = {
    # tools / launches
    "launch_account_op": "/tools/launch_account_op/",
    "launch_neuro_shilling": "/tools/launch_neuro_shilling/",
    "launch_neuro_dialogs": "/tools/launch_neuro_dialogs/",
    "launch_neuro_chatting": "/tools/launch_neuro_chatting/",
    "launch_neuro_commenting": "/tools/launch_neuro_commenting/",
    "launch_spam_pm": "/tools/launch_spam_pm/",
    "launch_group_spammer": "/tools/launch_group_spammer/",
    "launch_mass_looking": "/tools/launch_mass_looking/",
    "launch_massreact": "/tools/launch_massreact/",
    "launch_parsing": "/tools/launch_parsing/",
    "launch_story_mentions": "/tools/launch_story_mentions/",
    "launch_inviter": "/tools/launch_inviter/",
    "launch_warming": "/tools/launch_warming/",
    # state
    "tasks": "/tasks/",
    "accounts": "/accounts/",
    "accounts_import": "/accounts/import/",
    "accounts_export": "/accounts/export/",
    "proxies": "/proxies/",
    "balance": "/balance/",
    "me": "/me/",
}

# webhook event enum (OpenAPI)
WEBHOOK_EVENTS = (
    "task.started", "task.progress", "task.completed",
    "dm.received", "dm.sent", "dm.read", "keyword.matched",
    "account.status_changed", "proxy.status_changed",
    "subscription.expiring", "ai.handoff",
)


class GramGPTClient:
    def __init__(self, api_key: str, base: str = BASE, timeout: int = 30):
        if not api_key.startswith("ggk_"):
            raise ValueError("API key must be a ggk_* key from the panel")
        self.key = api_key
        self.base = base.rstrip("/")
        self.timeout = timeout

    def call(self, path: str, method: str = "GET", body: dict | None = None,
             idempotency_key: str | None = None) -> dict:
        url = path if path.startswith("http") else f"{self.base}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.key}")
        req.add_header("Content-Type", "application/json")
        if idempotency_key:
            req.add_header("Idempotency-Key", idempotency_key)  # 24h TTL dedup
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = r.read().decode()
                return {"status": r.status, "json": json.loads(raw) if raw else None}
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")
            try:
                payload = json.loads(raw)
            except Exception:
                payload = {"raw": raw[:500]}
            return {"status": e.code, "json": payload}

    def tools_launch(self, tool: str, payload: dict, idempotency_key: str | None = None) -> dict:
        path = ENDPOINTS.get(tool)
        if not path:
            raise ValueError(f"unknown tool {tool}; known: {sorted(ENDPOINTS)}")
        return self.call(path, "POST", payload, idempotency_key)

    def me(self) -> dict:
        return self.call(ENDPOINTS["me"])

    def balance(self) -> dict:
        return self.call(ENDPOINTS["balance"])

    def tasks(self) -> dict:
        return self.call(ENDPOINTS["tasks"])
