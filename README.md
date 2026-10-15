# gramgpt-engine

**Clean-room Python implementation of the GramGPT anti-ban / automation engine logic** — reconstructed 2026-10 purely from the *public surface* of gramgpt.io:

- OpenAPI 3.0.3 spec (92 endpoints, `GramGPT Public API v1.0.0-alpha`)
- Nuxt frontend chunks (scenario simulator, 77 event types, 10 generators)
- RU panel locale (2222 engine log templates, 5327 module doc keys)
- Live-captured GGR API responses (model `auto-2026-10-13`)

**Not** a copy of their server code: the Django backend and ML model weights are not public. This repo re-implements the *observable behaviour* — constants, gates, pacing curves, lifecycle rules, preflight fraud checks, and the GGR scoring shape — as a stdlib-only Python package.

> Research/educational use. Telegram mass-messaging violates Telegram ToS; accounts get banned. Understand the mechanics, don't abuse them.

## What's inside

| Module | Logic |
|---|---|
| `constants.py` | All engine numbers: sleep window 01-07, breaks (6-8/12-14/23-01), AI delay 5% × 20-90s, quarantine 24h, warming stages `new→warming→warmed→active→trusted→veteran`, 72-min young-comment rule, pace presets calm 15s / live 8s / hot 4s, 24-step scenarios, 20-70s pauses, revival 4/8/15s, activity curve (~19x evening/night), spam_pm 48h lifetime + chains 2-4, GGR tiers & SHAP groups, plan prices |
| `aiprotection.py` | Human-gating: sleep/break windows, random hesitation delays, typing/read/scroll simulation, daily+weekly account quotas |
| `warming.py` | Account lifecycle: stage by age, growing daily budget, young-account comment pacing, active windows, risk assessment (critical/high for fresh accounts in aggressive mode) |
| `flood.py` | FloodWait & spamblock → 24h quarantine; pool rotation that stops the task instead of burning accounts when everyone is flooded |
| `pacing.py` | 24h activity curve, pace-scaled replica delays (even-pace toggle), burst series, reaction delays, revival tempo |
| `preflight.py` | Launch-time fraud checks: supplier_fraud_batch (authkey cross-user dups), lot_burn, identical_broadcast detection |
| `shilling.py` | neuro_shilling: 24-step scenario per chat — personas/roles, arc (offtopic→intro→questions→proofs→reactions), hourly budget split by activity curve |
| `spam_pm.py` | DM outreach: 48h task lifetime, day plan, offer rotation, fleet-wide target dedup, per-account hourly/daily pace limiter |
| `ggr.py` | Local clone of the GGR account-quality scorer: 7 SHAP groups (vintage, identity, network, behavioural, spamblock_history, restoration, provenance), tiers, risk probability, shadow-fraud meta, lot verdict |
| `account_op.py` | Dispatcher for `launch_account_op` (appeal_spamblock, check, generate_profiles, privacy, reauthorize, reset_sessions, set_2fa, …) with OpenAPI validation; plug any transport |
| `client.py` | Thin client for the real GramGPT API (`ggk_live_*` Bearer, Idempotency-Key, all launch endpoints) |

## Full backend clone (`gramgpt_server/`)

A **runnable stdlib-only clone of the entire public API surface** — all 101 routes from their OpenAPI spec, wired to the engine above:

| File | What it is |
|---|---|
| `routes_spec.json` | 101 routes generated verbatim from their `openapi.json` (92 paths, methods, tags) |
| `app.py` | ThreadingHTTPServer router: spec-exact matching (404 unknown, 405 wrong method), Bearer auth gate, CORS, serves `/panel` + `/api/v1/openapi.json` |
| `store.py` | SQLite persistence: users, accounts, tasks, task_logs, photos, prompts, proxies, blacklists, history, webhooks, exports |
| `auth.py` | `ggk_live_*` Bearer issuance/validation (clone-local; real keys come from Tribute/Stripe) |
| `worker.py` | Task lifecycle `waiting→running→completed/failed/cancelled`, `queue_if_busy` (re-check every minute, 24h `queue_timeout`), RU log rendering from their real 2222-template bank |
| `handlers.py` | Business logic for all 101 routes; 422 validation shape `{"detail":[{"loc":…}]}` like FastAPI; envelope for all 13 `launch_*` endpoints (account_ids, dry_run, skip_unavailable, queue_if_busy, strict_config); GGR via engine scorer |

```bash
python examples/run_server.py --port 8770 --db gg.db   # prints demo token
python examples/build_panel_live.py                    # rebuild /panel UI
python examples/shot_live.py _demo_token.txt proof.png # live screenshot
```

`/panel` is a **live** Task-Monitor UI built on their real component CSS (`task-monitor.BVhk1W4S.css` verbatim, data-v stripped) and driven by `fetch()` against the clone API — tasks, streaming logs, head-stats all real data from the worker.

E2E proof (11 server tests): launch → worker executes 40 steps → 23 RU logs → `completed`, counters/results exact.

## Quick start

```bash
python -m unittest discover -s tests -v   # 56 tests (24 engine + 21 modules + 11 server e2e)
python examples/demo_day.py               # simulated engine day
```

```python
from datetime import datetime, timedelta
from gramgpt_engine import Account, gate, warming_allowed, QuarantineManager

now = datetime.now()
ok, reason = gate(now)                     # ai_protection verdict for "now"
acc = Account(1, "+1...", now - timedelta(days=40))
print(acc.stage(now), acc.budget(now))     # active 80/day
allowed, why = warming_allowed(acc, now)

qm = QuarantineManager()
qm.handle_flood(acc, wait_seconds=3600)    # -> 24h quarantine, pool keeps working
```

Wire real sending with your own MTProto transport:

```python
from gramgpt_engine import Engine
def transport(op, account_id, config):     # e.g. via Telethon
    ...
    return True, "ok"
Engine(transport=transport).run("check", [1, 2, 3])
```

## Provenance & limits

- Every constant traces to a public artifact (log template, doc key, OpenAPI field, frontend simulator, or live API response). Values marked `(est.)` in `constants.py` are inferred, not literal.
- GGR local scorer reproduces the response *shape* and monotonic behaviour; exact scores differ from their ML model (weights not public).
- Server-side Django implementation is not reproduced — it isn't public.
- Companion repo with the raw reverse-engineering artifacts (OpenAPI map, module contracts, RU locale extracts): [`gbonnet65923/gramgpt-reverse-kit`](https://github.com/gbonnet65923/gramgpt-reverse-kit).

## License

MIT — see LICENSE.
