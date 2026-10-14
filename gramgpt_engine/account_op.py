# -*- coding: utf-8 -*-
"""account_op — dispatcher mirroring POST /api/v1/tools/launch_account_op/.

Ops (OpenAPI enum): appeal_spamblock, check, check_spamblock, generate_profiles,
leave_chats, privacy, reauthorize, reset_sessions, set_2fa.

Each op takes a transport callable (async or sync) so the package stays
stdlib-only; wire your Telethon client in via Engine(transport=...).
"""
from dataclasses import dataclass, field
from datetime import datetime

from . import constants as C


@dataclass
class OpResult:
    op: str
    account_ids: list[int]
    ok: list[int] = field(default_factory=list)
    failed: dict[int, str] = field(default_factory=dict)
    ts: str = ""

    def as_dict(self) -> dict:
        return {"op": self.op, "accounts": self.account_ids, "ok": self.ok,
                "failed": self.failed, "ts": self.ts or datetime.now().isoformat()}


def validate(op: str, account_ids: list[int], config: dict | None = None) -> str | None:
    """Request validation per OpenAPI contract. Returns error string or None."""
    if op not in C.ACCOUNT_OPS:
        return f"unknown_op:{op}"
    if not account_ids or len(account_ids) < 1:
        return "account_ids:minItems:1"
    if op == "reset_sessions" and not (config or {}).get("confirm"):
        return "reset_sessions requires config.confirm=true"
    if op == "generate_profiles":
        allowed = {"settings", "generate_name", "generate_photo", "photo_source",
                   "photo_category", "photo_gender", "omit_last_name", "safe_mode",
                   "apply_to_telegram", "generation_prompt", "generate_username",
                   "username_pool", "name_pool", "custom_first_name", "custom_last_name",
                   "bio_pool", "custom_bio"}
        bad = set((config or {}).keys()) - allowed
        if bad:
            return f"generate_profiles:unknown_keys:{sorted(bad)}"
        up = (config or {}).get("username_pool")
        if up and len(up) < len(account_ids):
            return "username_pool must cover all account_ids (one each, in order)"
    return None


def assign_usernames(account_ids: list[int], username_pool: list[str]) -> dict[int, str]:
    """'handed out to account_ids in order, one each' (OpenAPI description)."""
    return dict(zip(account_ids, username_pool))


class Engine:
    """Runs ops against a transport: transport(op, account_id, config) -> (ok, detail)."""

    def __init__(self, transport=None):
        self.transport = transport

    def run(self, op: str, account_ids: list[int], config: dict | None = None,
            idempotency_key: str | None = None) -> OpResult:
        err = validate(op, account_ids, config)
        if err:
            raise ValueError(err)
        res = OpResult(op=op, account_ids=list(account_ids))
        cfg = config or {}
        if op == "generate_profiles" and cfg.get("username_pool"):
            cfg = dict(cfg)
            cfg["username_map"] = assign_usernames(account_ids, cfg["username_pool"])
        for aid in account_ids:
            if self.transport is None:
                res.ok.append(aid)  # dry-run mode
                continue
            ok, detail = self.transport(op, aid, cfg)
            if ok:
                res.ok.append(aid)
            else:
                res.failed[aid] = str(detail)
        return res
