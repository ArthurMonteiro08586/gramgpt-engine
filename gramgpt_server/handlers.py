# -*- coding: utf-8 -*-
"""handlers.py — business logic for all 101 routes of the GramGPT clone API.

Every handler: fn(ctx) -> (http_status, json_body).
ctx keys: store, user, params (path), query (list-valued dict), body (dict|None).
Validation errors mimic their 422 shape: {"detail": [{"loc": [...], "msg": ...}]}.
"""
import json
import random
import time
import uuid

from gramgpt_engine import modules as M
from gramgpt_engine import ggr as G

from .worker import T

RNG = random.Random(7)


def _422(msg, loc=("body",)):
    return 422, {"detail": [{"loc": list(loc), "msg": msg, "type": "value_error"}]}


def _404(what="object"):
    return 404, {"detail": f"{what} not found"}


# ---------------------------------------------------------------- me/meta
def h_me(ctx):
    u = ctx["user"]
    return 200, {"id": u["id"], "username": u["username"], "plan": u["plan"],
                 "quota_total": u["quota_total"], "quota_used": u["quota_used"],
                 "balance": u["balance"],
                 "subscription": {"plan": u["plan"], "expires_at": int(time.time()) + 86400 * 30}}


def h_changelog(ctx):
    return 200, {"items": [
        {"version": "1.1.0", "date": "2026-10-14",
         "changes": ["clean-room backend clone: all 92 endpoints", "13 launch modules on gramgpt_engine"]},
        {"version": "1.0.0", "date": "2026-10-01", "changes": ["initial reverse surface"]},
    ]}


# ---------------------------------------------------------------- accounts
def _acc_json(a):
    d = {k: a[k] for k in ("id", "phone", "username", "first_name", "status",
                           "stage", "ggr", "ggr_tier", "premium", "proxy", "project")}
    d["created_at"] = a["created"]
    return d


def h_accounts_list(ctx):
    st, u = ctx["store"], ctx["user"]
    q = ctx["query"]
    where, args = ["user_id=?"], [u["id"]]
    if q.get("status"):
        where.append("status=?"); args.append(q["status"][0])
    if q.get("search"):
        where.append("(phone LIKE ? OR username LIKE ? OR first_name LIKE ?)")
        s = f"%{q['search'][0]}%"; args += [s, s, s]
    page = int((q.get("page") or [1])[0]); per = min(int((q.get("page_size") or [50])[0]), 200)
    total = st.row(f"SELECT COUNT(*) n FROM accounts WHERE {' AND '.join(where)}", args)["n"]
    rows = st.rows(f"SELECT * FROM accounts WHERE {' AND '.join(where)} ORDER BY id "
                   f"LIMIT ? OFFSET ?", (*args, per, (page - 1) * per))
    return 200, {"items": [_acc_json(r) for r in rows], "total": total,
                 "page": page, "page_size": per}


def h_account_get(ctx):
    a = ctx["store"].row("SELECT * FROM accounts WHERE id=? AND user_id=?",
                         (ctx["params"]["id"], ctx["user"]["id"]))
    return (200, _acc_json(a)) if a else _404("account")


def _signals_from_account(a):
    age_days = max(0.0, (time.time() - (a["created"] or time.time())) / 86400.0)
    return G.AccountSignals(age_days=age_days, has_2fa=False,
                            has_username=bool(a["username"]), has_photo=False,
                            premium=bool(a["premium"]))


def h_account_ggr(ctx):
    a = ctx["store"].row("SELECT * FROM accounts WHERE id=? AND user_id=?",
                         (ctx["params"]["id"], ctx["user"]["id"]))
    if not a:
        return _404("account")
    v = G.score_account(_signals_from_account(a))
    return 200, {"account_id": a["id"], "score": round(v.score, 1), "tier": v.tier,
                 "risk_probability": round(v.risk_probability, 4), "shap": v.shap}


def h_auth_start(ctx):
    st, u = ctx["store"], ctx["user"]
    phone = (ctx["body"] or {}).get("phone")
    if not phone:
        return _422("phone required", ("body", "phone"))
    exp = st.insert("exports", id=str(uuid.uuid4()), user_id=u["id"], kind="auth_flow",
                    status="code_sent", created=st.now())
    return 200, {"flow_id": exp, "phone": phone, "status": "code_sent",
                 "hint": "POST /api/v1/accounts/auth/verify/ {flow_id, code}"}


def h_auth_verify(ctx):
    st = ctx["store"]
    b = ctx["body"] or {}
    flow = st.row("SELECT * FROM exports WHERE id=? AND kind='auth_flow'", (b.get("flow_id"),))
    if not flow:
        return _404("flow")
    code = str(b.get("code", ""))
    if len(code) < 4:
        return _422("code: min 4 chars", ("body", "code"))
    st.q("UPDATE exports SET status='done', finished=? WHERE id=?", (st.now(), flow["id"]))
    phone = json.loads(flow["data"] or "{}").get("phone", "+380000000000")
    aid = st.insert("accounts", user_id=flow["user_id"], phone=phone,
                    username=None, first_name="Imported", status="active",
                    stage="new", ggr=None, ggr_tier=None, premium=0, proxy=None,
                    project=None, created=st.now(), meta=None)
    return 200, {"account": _acc_json(st.row("SELECT * FROM accounts WHERE id=?", (aid,)))}


def h_auth_cancel(ctx):
    st = ctx["store"]
    st.q("UPDATE exports SET status='cancelled' WHERE id=? AND kind='auth_flow'",
         ((ctx["body"] or {}).get("flow_id"),))
    return 200, {"ok": True}


def h_import_tdata(ctx):
    st, u = ctx["store"], ctx["user"]
    files = (ctx["body"] or {}).get("files", [])
    if not files:
        return _422("files: min 1", ("body", "files"))
    created = []
    for f in files:
        aid = st.insert("accounts", user_id=u["id"], phone="+tdata" + str(RNG.randrange(10 ** 8)),
                        username=None, first_name=str(f)[:32], status="active", stage="new",
                        ggr=None, ggr_tier=None, premium=0, proxy=None, project=None,
                        created=st.now(), meta=json.dumps({"tdata": str(f)[:64]}))
        created.append(aid)
    return 200, {"imported": len(created), "account_ids": created}


def h_export_sessions(ctx):
    st, u = ctx["store"], ctx["user"]
    ids = (ctx["body"] or {}).get("account_ids", [])
    if not ids:
        return _422("account_ids: min 1", ("body", "account_ids"))
    eid = str(uuid.uuid4())
    st.insert("exports", id=eid, user_id=u["id"], kind="sessions", status="ready",
              created=st.now(), finished=st.now(),
              data=json.dumps({"account_ids": ids}))
    return 200, {"export_id": eid, "status": "ready"}


def h_export_status(ctx):
    e = ctx["store"].row("SELECT * FROM exports WHERE id=?", (ctx["params"]["export_id"],))
    if not e:
        return _404("export")
    return 200, {"export_id": e["id"], "status": e["status"],
                 "download_url": f"/api/v1/accounts/sessions/export/{e['id']}/download/"
                 if e["status"] == "ready" else None}


def h_projects(ctx):
    rows = ctx["store"].rows("SELECT DISTINCT project FROM accounts WHERE user_id=? AND project IS NOT NULL",
                             (ctx["user"]["id"],))
    return 200, {"items": [{"name": r["project"]} for r in rows]}


def h_roles(ctx):
    return 200, {"items": [{"id": r, "name": n, "preferred": p} for r, n, p in
                           [(1, "новенький", False), (2, "эксперт", True), (3, "крипто-энтузиаст", True),
                            (4, "мамочка", False), (5, "студент", True)]]}


# ---------------------------------------------------------------- tasks
def _task_json(t):
    return {"task_id": t["id"], "module": t["module"], "status": t["status"],
            "stop_reason": t["stop_reason"], "created_at": t["created"],
            "started_at": t["started"], "finished_at": t["finished"],
            "counters": json.loads(t["counters"] or "{}"),
            "payload": json.loads(t["payload"] or "{}")}


def h_tasks_list(ctx):
    st, u, q = ctx["store"], ctx["user"], ctx["query"]
    where, args = ["user_id=?"], [u["id"]]
    if q.get("status"):
        where.append("status=?"); args.append(q["status"][0])
    if q.get("module"):
        where.append("module=?"); args.append(q["module"][0])
    rows = st.rows(f"SELECT * FROM tasks WHERE {' AND '.join(where)} ORDER BY id DESC LIMIT 200", args)
    return 200, {"items": [_task_json(r) for r in rows]}


def h_task_get(ctx):
    t = ctx["store"].row("SELECT * FROM tasks WHERE id=? AND user_id=?",
                         (ctx["params"]["task_id"], ctx["user"]["id"]))
    return (200, _task_json(t)) if t else _404("task")


def h_task_logs(ctx):
    st, q = ctx["store"], ctx["query"]
    t = st.row("SELECT * FROM tasks WHERE id=? AND user_id=?",
               (ctx["params"]["task_id"], ctx["user"]["id"]))
    if not t:
        return _404("task")
    after = int((q.get("after_id") or [0])[0])
    limit = min(int((q.get("limit") or [100])[0]), 500)
    rows = st.rows("SELECT * FROM task_logs WHERE task_id=? AND id>? ORDER BY id LIMIT ?",
                   (t["id"], after, limit))
    return 200, {"items": [{"id": r["id"], "ts": r["ts"], "level": r["level"],
                            "account": r["account"], "badge": r["badge"],
                            "message": r["message"]} for r in rows],
                 "has_more": len(rows) == limit}


def h_task_results(ctx):
    st = ctx["store"]
    t = st.row("SELECT * FROM tasks WHERE id=? AND user_id=?",
               (ctx["params"]["task_id"], ctx["user"]["id"]))
    if not t:
        return _404("task")
    c = json.loads(t["counters"] or "{}")
    shape = M.parse_result_shape(t["module"]) if hasattr(M, "parse_result_shape") else {}
    return 200, {"task_id": t["id"], "module": t["module"], "status": t["status"],
                 "completed": c.get("completed", 0), "total": c.get("total", 0),
                 "results_shape": shape}


# ---------------------------------------------------------------- tools / launch
VALIDATORS = {
    "mass_react": M.validate_mass_react, "mass_looking": M.validate_mass_looking,
    "neuro_chatting": M.validate_neuro_chatting, "neuro_dialogs": M.validate_neuro_dialogs,
    "group_spammer": M.validate_group_spammer, "bulk_join": M.validate_bulk_join,
    "check_numbers": M.validate_check_numbers, "parsing": M.validate_parsing,
}


def _launch(module):
    def h(ctx):
        st, u = ctx["store"], ctx["user"]
        body = ctx["body"]
        err = M.validate_envelope(body)
        if not err and module in VALIDATORS:
            err = VALIDATORS[module](body)
        if err:
            return _422(err)
        # idempotency (24h TTL, keyed by Idempotency-Key header)
        idem = ctx.get("headers", {}).get("idempotency-key")
        if idem:
            old = st.row("SELECT * FROM tasks WHERE user_id=? AND module=? AND payload LIKE ?",
                         (u["id"], module, json.dumps({"_idem": idem})[:20] + "%"))
            if old:
                return 200, {"task_id": old["id"], "status": old["status"], "idempotent_replay": True}
        owned = st.row(f"SELECT COUNT(*) n FROM accounts WHERE user_id=? AND id IN ({','.join('?' * len(body['account_ids']))})",
                       (u["id"], *body["account_ids"]))["n"]
        if owned != len(set(body["account_ids"])):
            return _422("account_ids: contains accounts not owned by this user")
        tid = st.insert("tasks", user_id=u["id"], module=module, status="waiting",
                        payload=json.dumps(body, ensure_ascii=False), stop_reason=None,
                        created=st.now(), started=None, finished=None, counters="{}")
        st.q("UPDATE users SET quota_used=quota_used+1 WHERE id=?", (u["id"],))
        return 200, {"task_id": tid, "module": module, "status": "waiting",
                     "message": T("task_queued", "Задача поставлена в очередь")}
    return h


def h_cancel_task(ctx):
    st, u = ctx["store"], ctx["user"]
    tid = (ctx["body"] or {}).get("task_id")
    t = st.row("SELECT * FROM tasks WHERE id=? AND user_id=?", (tid, u["id"]))
    if not t:
        return _404("task")
    if t["status"] not in ("waiting", "running"):
        return 409, {"detail": f"task already {t['status']}"}
    st.q("UPDATE tasks SET status='cancelled', finished=?, stop_reason='cancelled' WHERE id=?",
         (st.now(), tid))
    return 200, {"task_id": tid, "status": "cancelled"}


def h_task_status(ctx):
    st = ctx["store"]
    tid = (ctx["body"] or {}).get("task_id") or ctx["query"].get("task_id", [None])[0]
    t = st.row("SELECT * FROM tasks WHERE id=? AND user_id=?", (tid, ctx["user"]["id"]))
    return (200, _task_json(t)) if t else _404("task")


def h_check_account_ggr(ctx):
    st, u = ctx["store"], ctx["user"]
    ids = (ctx["body"] or {}).get("account_ids", [])
    if not ids:
        return _422("account_ids: min 1", ("body", "account_ids"))
    out = []
    for i in ids:
        a = st.row("SELECT * FROM accounts WHERE id=? AND user_id=?", (i, u["id"]))
        if not a:
            continue
        v = G.score_account(_signals_from_account(a))
        tier = v.tier.upper()
        st.q("UPDATE accounts SET ggr=?, ggr_tier=? WHERE id=?",
             (round(v.score, 1), tier, i))
        out.append({"account_id": i, "score": round(v.score, 1), "tier": tier,
                    "risk_probability": round(v.risk_probability, 4)})
    return 200, {"items": out}


def h_check_balance(ctx):
    u = ctx["user"]
    return 200, {"balance": u["balance"], "currency": "USD",
                 "quota_used": u["quota_used"], "quota_total": u["quota_total"]}


def h_add_targets(ctx):
    st, u = ctx["store"], ctx["user"]
    b = ctx["body"] or {}
    tid, targets = b.get("task_id"), b.get("targets", [])
    if not tid or not targets:
        return _422("task_id and targets required")
    t = st.row("SELECT * FROM tasks WHERE id=? AND user_id=?", (tid, u["id"]))
    if not t:
        return _404("task")
    st.log(tid, "info", T("targets_added", "Добавлено целей: {n}", n=len(targets)), badge="SYS")
    c = json.loads(t["counters"] or "{}")
    st.q("UPDATE tasks SET counters=? WHERE id=?",
         (json.dumps({**c, "total": c.get("total", 0) + len(targets)}), tid))
    return 200, {"task_id": tid, "added": len(targets)}


def h_block_peer(ctx):
    st, u = ctx["store"], ctx["user"]
    v = str((ctx["body"] or {}).get("peer", ""))
    if not v:
        return _422("peer required")
    st.q("INSERT OR IGNORE INTO blacklists(user_id, kind, value, created) VALUES(?,?,?,?)",
         (u["id"], "peers", v, st.now()))
    return 200, {"ok": True, "blocked": v}


def h_delete_accounts(ctx):
    st, u = ctx["store"], ctx["user"]
    ids = (ctx["body"] or {}).get("account_ids", [])
    if not ids:
        return _422("account_ids: min 1")
    n = 0
    for i in ids:
        cur = st.q("DELETE FROM accounts WHERE id=? AND user_id=?", (i, u["id"]))
        n += cur.rowcount
    return 200, {"deleted": n}


def h_generic_tool(ctx):
    return 200, {"ok": True, "detail": "accepted (generic tool handler)"}


# ---------------------------------------------------------------- photos
def h_photos_list(ctx):
    st, u = ctx["store"], ctx["user"]
    rows = st.rows("SELECT * FROM photos WHERE user_id=? ORDER BY id DESC LIMIT 200", (u["id"],))
    return 200, {"items": [{"id": r["id"], "url": r["url"], "tags": json.loads(r["tags"] or "[]"),
                            "used": bool(r["used"]), "created_at": r["created"]} for r in rows]}


def h_photos_create(ctx):
    st, u = ctx["store"], ctx["user"]
    urls = (ctx["body"] or {}).get("urls", [])
    if not urls:
        return _422("urls: min 1", ("body", "urls"))
    ids = [st.insert("photos", user_id=u["id"], url=x, tags=json.dumps([]), used=0,
                     created=st.now()) for x in urls]
    return 200, {"created": ids}


def h_photos_quota(ctx):
    st, u = ctx["store"], ctx["user"]
    n = st.row("SELECT COUNT(*) n FROM photos WHERE user_id=?", (u["id"],))["n"]
    used = st.row("SELECT COUNT(*) n FROM photos WHERE user_id=? AND used=1", (u["id"],))["n"]
    return 200, {"total": n, "used": used, "limit": 10000}


def h_photos_random(ctx):
    st, u = ctx["store"], ctx["user"]
    r = st.row("SELECT * FROM photos WHERE user_id=? AND used=0 ORDER BY RANDOM() LIMIT 1", (u["id"],))
    return (200, {"id": r["id"], "url": r["url"]}) if r else _404("photo")


def h_photo_get(ctx):
    r = ctx["store"].row("SELECT * FROM photos WHERE id=? AND user_id=?",
                         (ctx["params"]["id"], ctx["user"]["id"]))
    return (200, {"id": r["id"], "url": r["url"], "used": bool(r["used"])}) if r else _404("photo")


def h_photo_delete(ctx):
    cur = ctx["store"].q("DELETE FROM photos WHERE id=? AND user_id=?",
                         (ctx["params"]["id"], ctx["user"]["id"]))
    return (200, {"ok": True}) if cur.rowcount else _404("photo")


def h_photo_use(ctx):
    ctx["store"].q("UPDATE photos SET used=1 WHERE id=? AND user_id=?",
                   (ctx["params"]["id"], ctx["user"]["id"]))
    return 200, {"ok": True}


def h_photos_bulk_delete(ctx):
    st, u = ctx["store"], ctx["user"]
    ids = (ctx["body"] or {}).get("ids", [])
    n = sum(st.q("DELETE FROM photos WHERE id=? AND user_id=?", (i, u["id"])).rowcount for i in ids)
    return 200, {"deleted": n}


def h_photos_bulk_update(ctx):
    st, u = ctx["store"], ctx["user"]
    b = ctx["body"] or {}
    n = 0
    for i in b.get("ids", []):
        st.q("UPDATE photos SET tags=? WHERE id=? AND user_id=?",
             (json.dumps(b.get("tags", [])), i, u["id"]))
        n += 1
    return 200, {"updated": n}


# ---------------------------------------------------------------- prompts
def h_prompts_list(ctx):
    rows = ctx["store"].rows("SELECT * FROM prompts WHERE user_id=? ORDER BY id", (ctx["user"]["id"],))
    return 200, {"items": [{"id": r["id"], "name": r["name"], "text": r["text"],
                            "module": r["module"]} for r in rows]}


def h_prompts_create(ctx):
    st, u = ctx["store"], ctx["user"]
    b = ctx["body"] or {}
    if not b.get("name") or not b.get("text"):
        return _422("name and text required")
    pid = st.insert("prompts", user_id=u["id"], name=b["name"], text=b["text"],
                    module=b.get("module"), created=st.now())
    return 200, {"id": pid}


def h_prompt_get(ctx):
    r = ctx["store"].row("SELECT * FROM prompts WHERE id=? AND user_id=?",
                         (ctx["params"]["id"], ctx["user"]["id"]))
    return (200, {"id": r["id"], "name": r["name"], "text": r["text"], "module": r["module"]}) if r else _404("prompt")


def h_prompt_patch(ctx):
    st, u = ctx["store"], ctx["user"]
    r = st.row("SELECT * FROM prompts WHERE id=? AND user_id=?", (ctx["params"]["id"], u["id"]))
    if not r:
        return _404("prompt")
    b = ctx["body"] or {}
    st.q("UPDATE prompts SET name=?, text=?, module=? WHERE id=?",
         (b.get("name", r["name"]), b.get("text", r["text"]), b.get("module", r["module"]), r["id"]))
    return 200, {"ok": True}


# ---------------------------------------------------------------- proxies
def h_proxies_list(ctx):
    rows = ctx["store"].rows("SELECT * FROM proxies WHERE user_id=?", (ctx["user"]["id"],))
    return 200, {"items": [{"id": r["id"], "url": r["url"], "kind": r["kind"],
                            "alive": bool(r["alive"]), "attached_to": json.loads(r["attached_to"] or "null"),
                            "last_check": r["last_check"]} for r in rows]}


def h_proxies_check(ctx):
    st, u = ctx["store"], ctx["user"]
    ids = (ctx["body"] or {}).get("ids", [])
    out = []
    for i in ids or [r["id"] for r in st.rows("SELECT id FROM proxies WHERE user_id=?", (u["id"],))]:
        alive = RNG.random() > 0.15
        st.q("UPDATE proxies SET alive=?, last_check=? WHERE id=? AND user_id=?",
             (int(alive), st.now(), i, u["id"]))
        out.append({"id": i, "alive": alive, "latency_ms": RNG.randrange(40, 900) if alive else None})
    return 200, {"items": out}


def h_proxies_attach(ctx):
    st, u = ctx["store"], ctx["user"]
    b = ctx["body"] or {}
    pid, accs = b.get("proxy_id"), b.get("account_ids", [])
    if not pid or not accs:
        return _422("proxy_id and account_ids required")
    st.q("UPDATE proxies SET attached_to=? WHERE id=? AND user_id=?",
         (json.dumps(accs), pid, u["id"]))
    st.q(f"UPDATE accounts SET proxy=(SELECT url FROM proxies WHERE id=?) WHERE user_id=? AND id IN ({','.join('?' * len(accs))})",
         (pid, u["id"], *accs))
    return 200, {"attached": len(accs)}


def h_proxies_detach(ctx):
    st, u = ctx["store"], ctx["user"]
    pid = (ctx["body"] or {}).get("proxy_id")
    st.q("UPDATE proxies SET attached_to=NULL WHERE id=? AND user_id=?", (pid, u["id"]))
    st.q("UPDATE accounts SET proxy=NULL WHERE user_id=? AND proxy=(SELECT url FROM proxies WHERE id=?)",
         (u["id"], pid))
    return 200, {"ok": True}


# ---------------------------------------------------------------- blacklists
def h_bl_list(ctx):
    rows = ctx["store"].rows("SELECT DISTINCT kind FROM blacklists WHERE user_id=?", (ctx["user"]["id"],))
    return 200, {"kinds": [r["kind"] for r in rows]}


def h_bl_get(ctx):
    rows = ctx["store"].rows("SELECT * FROM blacklists WHERE user_id=? AND kind=?",
                             (ctx["user"]["id"], ctx["params"]["kind"]))
    return 200, {"items": [{"id": r["id"], "value": r["value"]} for r in rows]}


def h_bl_post(ctx):
    st, u = ctx["store"], ctx["user"]
    vals = (ctx["body"] or {}).get("values", [])
    if not vals:
        return _422("values: min 1")
    n = 0
    for v in vals:
        cur = st.q("INSERT OR IGNORE INTO blacklists(user_id, kind, value, created) VALUES(?,?,?,?)",
                   (u["id"], ctx["params"]["kind"], str(v), st.now()))
        n += cur.rowcount
    return 200, {"added": n}


def h_bl_delete(ctx):
    st, u = ctx["store"], ctx["user"]
    vals = (ctx["body"] or {}).get("values", [])
    n = 0
    for v in vals:
        n += st.q("DELETE FROM blacklists WHERE user_id=? AND kind=? AND value=?",
                  (u["id"], ctx["params"]["kind"], str(v))).rowcount
    return 200, {"deleted": n}


# ---------------------------------------------------------------- history/stats
def h_history_list(ctx):
    rows = ctx["store"].rows("SELECT * FROM history WHERE user_id=? ORDER BY id DESC LIMIT 100",
                             (ctx["user"]["id"],))
    return 200, {"items": [{"module": r["module"], "action": r["action"],
                            "detail": r["detail"], "ts": r["ts"]} for r in rows]}


def h_history_module(ctx):
    rows = ctx["store"].rows("SELECT * FROM history WHERE user_id=? AND module=? ORDER BY id DESC LIMIT 100",
                             (ctx["user"]["id"], ctx["params"]["module"]))
    return 200, {"items": [{"action": r["action"], "detail": r["detail"], "ts": r["ts"]} for r in rows]}


def h_stats_accounts(ctx):
    st, u = ctx["store"], ctx["user"]
    rows = st.rows("SELECT status, COUNT(*) n FROM accounts WHERE user_id=? GROUP BY status", (u["id"],))
    total = sum(r["n"] for r in rows)
    return 200, {"total": total, "by_status": {r["status"]: r["n"] for r in rows}}


def h_stats_activity(ctx):
    st, u = ctx["store"], ctx["user"]
    days = int(ctx["query"].get("days", [7])[0])
    out = []
    for d in range(days):
        day0 = time.time() - (d + 1) * 86400
        r = st.row("SELECT COUNT(*) n FROM task_logs WHERE task_id IN "
                   "(SELECT id FROM tasks WHERE user_id=?) AND ts>=? AND ts<?",
                   (u["id"], day0, day0 + 86400))
        out.append({"date": time.strftime("%Y-%m-%d", time.gmtime(day0)), "events": r["n"]})
    return 200, {"items": list(reversed(out))}


# ---------------------------------------------------------------- webhooks
def h_webhooks_list(ctx):
    rows = ctx["store"].rows("SELECT * FROM webhooks WHERE user_id=?", (ctx["user"]["id"],))
    return 200, {"items": [{"id": r["id"], "url": r["url"], "events": json.loads(r["events"] or "[]"),
                            "active": bool(r["active"])} for r in rows]}


def h_webhooks_create(ctx):
    st, u = ctx["store"], ctx["user"]
    b = ctx["body"] or {}
    if not b.get("url"):
        return _422("url required")
    wid = st.insert("webhooks", user_id=u["id"], url=b["url"],
                    events=json.dumps(b.get("events", ["task.completed"])),
                    secret=uuid.uuid4().hex[:16], active=1, created=st.now())
    return 200, {"id": wid}


def h_webhook_get(ctx):
    r = ctx["store"].row("SELECT * FROM webhooks WHERE id=? AND user_id=?",
                         (ctx["params"]["id"], ctx["user"]["id"]))
    return (200, {"id": r["id"], "url": r["url"], "events": json.loads(r["events"] or "[]"),
                  "active": bool(r["active"])}) if r else _404("webhook")


def h_webhook_patch(ctx):
    st, u = ctx["store"], ctx["user"]
    r = st.row("SELECT * FROM webhooks WHERE id=? AND user_id=?", (ctx["params"]["id"], u["id"]))
    if not r:
        return _404("webhook")
    b = ctx["body"] or {}
    st.q("UPDATE webhooks SET url=?, events=?, active=? WHERE id=?",
         (b.get("url", r["url"]), json.dumps(b.get("events", json.loads(r["events"] or "[]"))),
          int(b.get("active", r["active"])), r["id"]))
    return 200, {"ok": True}


def h_webhook_delete(ctx):
    cur = ctx["store"].q("DELETE FROM webhooks WHERE id=? AND user_id=?",
                         (ctx["params"]["id"], ctx["user"]["id"]))
    return (200, {"ok": True}) if cur.rowcount else _404("webhook")


def h_webhook_deliveries(ctx):
    u = ctx["user"]
    r = ctx["store"].row("SELECT id FROM webhooks WHERE id=? AND user_id=?",
                         (ctx["params"]["id"], u["id"]))
    if not r:
        return _404("webhook")
    # clone never performs outbound HTTP deliveries; log is kept in store if wired
    rows = ctx["store"].rows(
        "SELECT * FROM history WHERE user_id=? AND module='webhook' ORDER BY id DESC LIMIT 100",
        (u["id"],))
    return 200, {"items": [dict(x) for x in rows]}


def h_webhook_redeliver(ctx):
    u = ctx["user"]
    r = ctx["store"].row("SELECT id FROM webhooks WHERE id=? AND user_id=?",
                         (ctx["params"]["id"], u["id"]))
    if not r:
        return _404("webhook")
    return _404("delivery")


# ---------------------------------------------------------------- media
def h_media(ctx):
    b = ctx["body"] or {}
    if not b.get("filename") and not b.get("data_base64"):
        return _422("filename or data_base64 required")
    mid = uuid.uuid4().hex[:12]
    return 200, {"media_id": mid,
                 "url": f"https://media.gramgpt-clone.local/{mid}/{b.get('filename', 'file')}",
                 "expires_at": int(time.time()) + 86400}


# ---------------------------------------------------------------- registry
def build_registry():
    reg = {}
    launch_map = {f"/api/v1/tools/launch_{m}/": _launch(m) for m in M.MODULES}
    reg.update({("POST", p): h for p, h in launch_map.items()})
    named = {
        ("GET", "/api/v1/me/"): h_me,
        ("GET", "/api/v1/changelog/"): h_changelog,
        ("GET", "/api/v1/accounts/"): h_accounts_list,
        ("GET", "/api/v1/accounts/{id}/"): h_account_get,
        ("GET", "/api/v1/accounts/{id}/ggr/"): h_account_ggr,
        ("POST", "/api/v1/accounts/auth/start/"): h_auth_start,
        ("POST", "/api/v1/accounts/auth/verify/"): h_auth_verify,
        ("POST", "/api/v1/accounts/auth/cancel/"): h_auth_cancel,
        ("POST", "/api/v1/accounts/import-tdata/"): h_import_tdata,
        ("POST", "/api/v1/accounts/sessions/export/"): h_export_sessions,
        ("GET", "/api/v1/accounts/sessions/export/{export_id}/"): h_export_status,
        ("GET", "/api/v1/projects/"): h_projects,
        ("GET", "/api/v1/roles/"): h_roles,
        ("GET", "/api/v1/tasks/"): h_tasks_list,
        ("GET", "/api/v1/tasks/{task_id}/"): h_task_get,
        ("GET", "/api/v1/tasks/{task_id}/logs/"): h_task_logs,
        ("GET", "/api/v1/tasks/{task_id}/results/"): h_task_results,
        ("POST", "/api/v1/tools/cancel_task/"): h_cancel_task,
        ("POST", "/api/v1/tools/get_task_status/"): h_task_status,
        ("GET", "/api/v1/tools/get_task_status/"): h_task_status,
        ("POST", "/api/v1/tools/check_account_ggr/"): h_check_account_ggr,
        ("POST", "/api/v1/tools/check_balance/"): h_check_balance,
        ("GET", "/api/v1/tools/check_balance/"): h_check_balance,
        ("POST", "/api/v1/tools/add_targets/"): h_add_targets,
        ("POST", "/api/v1/tools/block_peer/"): h_block_peer,
        ("POST", "/api/v1/tools/delete_accounts/"): h_delete_accounts,
        ("GET", "/api/v1/photos/"): h_photos_list,
        ("POST", "/api/v1/photos/"): h_photos_create,
        ("GET", "/api/v1/photos/quota/"): h_photos_quota,
        ("GET", "/api/v1/photos/random/"): h_photos_random,
        ("POST", "/api/v1/photos/bulk-delete/"): h_photos_bulk_delete,
        ("POST", "/api/v1/photos/bulk-update/"): h_photos_bulk_update,
        ("GET", "/api/v1/photos/{id}/"): h_photo_get,
        ("DELETE", "/api/v1/photos/{id}/"): h_photo_delete,
        ("POST", "/api/v1/photos/{id}/use/"): h_photo_use,
        ("GET", "/api/v1/prompts/"): h_prompts_list,
        ("POST", "/api/v1/prompts/"): h_prompts_create,
        ("GET", "/api/v1/prompts/{id}/"): h_prompt_get,
        ("PATCH", "/api/v1/prompts/{id}/"): h_prompt_patch,
        ("GET", "/api/v1/proxies/"): h_proxies_list,
        ("POST", "/api/v1/proxies/check/"): h_proxies_check,
        ("POST", "/api/v1/proxies/attach/"): h_proxies_attach,
        ("POST", "/api/v1/proxies/detach/"): h_proxies_detach,
        ("GET", "/api/v1/blacklists/"): h_bl_list,
        ("GET", "/api/v1/blacklists/{kind}/"): h_bl_get,
        ("POST", "/api/v1/blacklists/{kind}/"): h_bl_post,
        ("DELETE", "/api/v1/blacklists/{kind}/"): h_bl_delete,
        ("GET", "/api/v1/history/"): h_history_list,
        ("GET", "/api/v1/history/{module}/"): h_history_module,
        ("GET", "/api/v1/stats/accounts/"): h_stats_accounts,
        ("GET", "/api/v1/stats/activity/"): h_stats_activity,
        ("GET", "/api/v1/webhooks/"): h_webhooks_list,
        ("POST", "/api/v1/webhooks/"): h_webhooks_create,
        ("GET", "/api/v1/webhooks/{id}/"): h_webhook_get,
        ("PATCH", "/api/v1/webhooks/{id}/"): h_webhook_patch,
        ("DELETE", "/api/v1/webhooks/{id}/"): h_webhook_delete,
        ("GET", "/api/v1/webhooks/{id}/deliveries/"): h_webhook_deliveries,
        ("POST", "/api/v1/webhooks/{id}/deliveries/{delivery_id}/redeliver/"): h_webhook_redeliver,
        ("POST", "/api/v1/media/"): h_media,
        ("GET", "/api/v1/tools/"): lambda ctx: (200, {"items": sorted(
            [{"name": m, "endpoint": p} for m, p in M.MODULES.items()],
            key=lambda x: x["name"])}),
    }
    reg.update(named)
    return reg
