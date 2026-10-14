# -*- coding: utf-8 -*-
"""modules.py — launch contracts + planners for ALL 8 remaining GramGPT modules.

Source: /api/v1/tools/launch_* request schemas (openapi_parsed, $refs resolved)
+ live panel screenshots (2026-10-14). Stdlib-only, transport-agnostic:
validate_*() check a payload like the server would (422 reasons), plan_*()
build the local execution plan the panel worker would run.

Covered here: mass_react, mass_looking, neuro_chatting, neuro_dialogs,
group_spammer (Чат-Рассылки), bulk_join (Инвайтер/Масс-джойн), check_numbers,
parsing. Cross-cutting envelope shared by all 13 launch endpoints:
  account_ids(min 1) + dry_run + skip_unavailable + queue_if_busy + strict_config
  header Idempotency-Key (24h TTL); skipped reasons: busy|no_proxy|proxy_dead|status:<s>
  queue_if_busy: task 'waiting', re-checked every minute, gives up after 24h ->
  failed, stop_reason='queue_timeout'; cancel_task works on waiting tasks.
"""

TASK_STATES = ("waiting", "running", "completed", "failed", "cancelled")
SKIP_REASONS = ("busy", "no_proxy", "proxy_dead")          # + "status:<account status>"
QUEUE_TIMEOUT_H = 24
QUEUE_CHECK_MIN = 1
IDEMPOTENCY_TTL_H = 24

MODULES = {
    "mass_react":       "/api/v1/tools/launch_mass_react/",
    "mass_looking":     "/api/v1/tools/launch_mass_looking/",
    "neuro_chatting":   "/api/v1/tools/launch_neuro_chatting/",
    "neuro_dialogs":    "/api/v1/tools/launch_neuro_dialogs/",
    "group_spammer":    "/api/v1/tools/launch_group_spammer/",
    "bulk_join":        "/api/v1/tools/launch_bulk_join/",
    "check_numbers":    "/api/v1/tools/launch_check_numbers/",
    "parsing":          "/api/v1/tools/launch_parsing/",
    # already implemented elsewhere in the engine:
    "neuro_commenting": "/api/v1/tools/launch_neuro_commenting/",
    "neuro_shilling":   "/api/v1/tools/launch_neuro_shilling/",
    "spam_pm":          "/api/v1/tools/launch_spam_pm/",
    "warming":          "/api/v1/tools/launch_warming/",
    "account_op":       "/api/v1/tools/launch_account_op/",
}


def _err(msg):
    return msg


def validate_envelope(payload):
    """Shared part of every launch_* payload."""
    if not isinstance(payload, dict):
        return _err("payload must be an object")
    ids = payload.get("account_ids")
    if not isinstance(ids, list) or len(ids) < 1:
        return _err("account_ids: min 1 item required")
    if any(not isinstance(i, int) for i in ids):
        return _err("account_ids: integers only")
    for flag in ("dry_run", "skip_unavailable", "queue_if_busy", "strict_config"):
        if flag in payload and not isinstance(payload[flag], bool):
            return _err(f"{flag}: must be boolean")
    return None


# ---------------- mass_react ----------------

def validate_mass_react(payload):
    e = validate_envelope(payload)
    if e:
        return e
    ch = payload.get("channels")
    if not isinstance(ch, list) or len(ch) < 1:
        return _err("channels: min 1 required")
    if not isinstance(payload.get("reactions", []), list):
        return _err("reactions: list required")
    cfg = payload.get("config", {})
    lo = cfg.get("min_delay_seconds", 15)
    hi = cfg.get("max_delay_seconds", 60)
    if not (isinstance(lo, int) and lo >= 0) or not (isinstance(hi, int) and hi >= 0):
        return _err("config delays: non-negative integers")
    if hi < lo:
        return _err("max_delay_seconds < min_delay_seconds")
    return None


def plan_mass_react(accounts, channels, reactions, cfg=None, rng=None):
    """Per-account reaction schedule: random delay in [min,max] per action."""
    import random
    rng = rng or random
    cfg = cfg or {}
    lo, hi = cfg.get("min_delay_seconds", 15), cfg.get("max_delay_seconds", 60)
    plan = []
    for a in accounts:
        t = 0.0
        for ch in channels:
            for r in (reactions or ["👍"]):
                t += rng.uniform(lo, hi)
                plan.append({"account": a, "channel": ch, "reaction": r, "at_sec": round(t, 1)})
    return plan


# ---------------- mass_looking ----------------

def validate_mass_looking(payload):
    e = validate_envelope(payload)
    if e:
        return e
    peers = payload.get("peers")
    if not isinstance(peers, list) or len(peers) < 1:
        return _err("peers: min 1 required (users/chats whose stories to view)")
    return None


def plan_mass_looking(accounts, peers, like=False):
    """Story view (optionally like) per peer per account."""
    plan = []
    for a in accounts:
        for p in peers:
            plan.append({"account": a, "peer": p, "action": "view+like" if like else "view"})
    return plan


# ---------------- neuro_chatting ----------------

def validate_neuro_chatting(payload):
    e = validate_envelope(payload)
    if e:
        return e
    chats = payload.get("chats")
    if not isinstance(chats, list) or len(chats) < 1:
        return _err("chats: min 1 required")
    cfg = payload.get("config", {})
    lo, hi = cfg.get("min_delay_seconds", 30), cfg.get("max_delay_seconds", 120)
    if hi < lo:
        return _err("max_delay_seconds < min_delay_seconds")
    wm = cfg.get("work_mode", "count")
    if wm not in ("count", "time"):
        return _err("work_mode: enum count|time")
    if wm == "time":
        d = cfg.get("duration_minutes", 60)
        if not (isinstance(d, int) and d >= 1):
            return _err("duration_minutes: int >= 1")
    rm = cfg.get("reaction_mode", "interval")
    if rm not in ("interval", "keywords"):
        return _err("reaction_mode: enum interval|keywords")
    if rm == "keywords" and not cfg.get("keywords"):
        return _err("reaction_mode=keywords requires config.keywords")
    return None


def plan_neuro_chatting(accounts, chats, cfg=None, rng=None):
    """Reply schedule; interval mode uses reply_probability per incoming msg."""
    import random
    rng = rng or random
    cfg = cfg or {}
    lo, hi = cfg.get("min_delay_seconds", 30), cfg.get("max_delay_seconds", 120)
    mode = cfg.get("work_mode", "count")
    out = []
    for a in accounts:
        for c in chats:
            if mode == "count":
                n = cfg.get("max_messages", 10)
            else:
                n = max(1, int(cfg.get("duration_minutes", 60) * 60 / max(1, (lo + hi) / 2)))
            t = 0.0
            for i in range(n):
                t += rng.uniform(lo, hi)
                reply = True
                if cfg.get("reaction_mode", "interval") == "interval":
                    reply = rng.random() < cfg.get("reply_probability", 0.5)
                out.append({"account": a, "chat": c, "msg_no": i + 1,
                            "at_sec": round(t, 1), "reply": reply})
    return out


# ---------------- neuro_dialogs ----------------

def validate_neuro_dialogs(payload):
    e = validate_envelope(payload)
    if e:
        return e
    cfg = payload.get("config", {})
    lvl = cfg.get("accountProtectionLevel")
    if lvl is not None and lvl not in ("осторожный", "сбалансированный", "агрессивный",
                                       "cautious", "balanced", "aggressive"):
        return _err("config.accountProtectionLevel: cautious|balanced|aggressive")
    return None


# ---------------- group_spammer (Чат-Рассылки) ----------------

def validate_group_spammer(payload):
    e = validate_envelope(payload)
    if e:
        return e
    targets = payload.get("targets") or []
    folders = payload.get("folder_links") or []
    if not targets and not folders:
        return _err("targets or folder_links required (chats to post in)")
    chain = payload.get("chain")
    if not isinstance(chain, list) or not chain:
        return _err("chain: ordered message items required")
    if any(not isinstance(m, dict) for m in chain):
        return _err("chain: each item is an object")
    return None


def plan_group_spammer(accounts, targets, chain, folder_chats=None):
    """Each account posts the full chain (2-4 items) into each target once."""
    chats = list(dict.fromkeys((targets or []) + (folder_chats or [])))
    plan = []
    for a in accounts:
        for c in chats:
            for i, item in enumerate(chain):
                plan.append({"account": a, "chat": c, "chain_pos": i, "item": item})
    return plan


# ---------------- bulk_join (Инвайтер) ----------------

def validate_bulk_join(payload):
    e = validate_envelope(payload)
    if e:
        return e
    ch = payload.get("channels")
    if not isinstance(ch, list) or not ch:
        return _err("channels: list of channels/chats to join required")
    return None


def plan_bulk_join(accounts, channels, folder=None):
    plan = []
    for a in accounts:
        for c in channels:
            plan.append({"account": a, "join": c, "folder": folder})
    return plan


# ---------------- check_numbers ----------------

def validate_check_numbers(payload):
    e = validate_envelope(payload)
    if e:
        return e
    tg = payload.get("targets")
    if not isinstance(tg, list) or not tg:
        return _err("targets: phone numbers to check required")
    bad = [p for p in tg if not (isinstance(p, str) and p.startswith("+") and p[1:].isdigit())]
    if bad:
        return _err(f"targets: not E.164 phone(s): {bad[:3]}")
    return None


# ---------------- parsing ----------------

PARSE_KINDS = ("auto", "channels", "comments", "groups", "messages", "users")
PARSE_LIMIT_KEY = {"channels": "results_limit", "groups": "results_limit",
                   "users": "members_limit", "messages": "messages_limit",
                   "comments": "posts_limit"}
CHANNEL_MODES = ("search", "similar", "parse")


def validate_parsing(payload):
    e = validate_envelope(payload)
    if e:
        return e
    kind = payload.get("kind")
    if kind not in PARSE_KINDS:
        return _err("kind: enum " + "|".join(PARSE_KINDS))
    if kind in ("users", "messages", "comments") and not payload.get("targets"):
        return _err(f"kind={kind}: targets required")
    if kind == "groups" and not payload.get("search_keywords"):
        return _err("kind=groups: search_keywords required")
    cfg = payload.get("config", {})
    if kind == "channels":
        mode = cfg.get("mode", "search")
        if mode not in CHANNEL_MODES:
            return _err("config.mode: enum search|similar|parse")
        if mode == "similar" and not cfg.get("seed_links"):
            return _err("config.mode=similar requires seed_links")
        if mode == "parse" and not payload.get("targets"):
            return _err("config.mode=parse requires targets")
    for opt in ("skip_bots", "only_with_username", "only_premium"):
        if opt in cfg and not isinstance(cfg[opt], bool):
            return _err(f"config.{opt}: boolean")
    return None


def parse_result_shape(kind):
    """Result limit key differs per kind (channels/groups share results_limit)."""
    if kind == "comments":
        return {"limit_keys": ["posts_limit", "comments_per_post"]}
    return {"limit_keys": [PARSE_LIMIT_KEY.get(kind, "results_limit")]}
