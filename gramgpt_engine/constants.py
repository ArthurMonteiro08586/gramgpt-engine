# -*- coding: utf-8 -*-
"""GramGPT engine constants — reconstructed from public surface reverse (2026-10-14).

Sources: OpenAPI 92 endpoints, RU panel locale (2222 engine log templates,
5327 module docs), Nuxt frontend chunks (simulator generators), live GGR API responses.
Values marked (est.) are derived from observed frontend behaviour, not literal docs.
"""

# ── ai_protection ────────────────────────────────────────────────
SLEEP_WINDOW = (1, 7)            # 01:00-07:00 account must be inactive (logs.ai_protection_sleep)
BREAK_WINDOWS = [(6, 8), (12, 14), (23, 24 + 1)]  # early morning / lunch / late evening (logs.ai_protection_break_reasons)
RETRY_DELAY_SEC = 30             # logs.retry_delay
AI_DELAY_PROB = 0.05             # 5% of actions get ai_protection_delay
AI_DELAY_RANGE = (20, 90)        # seconds

# ── quarantine / flood ──────────────────────────────────────────
QUARANTINE_HOURS = 24            # FloodWait and spamblock quarantine (logs.account_quarantine_flood*)

# ── warming lifecycle ───────────────────────────────────────────
# docs: stage_warming = 3+ days, stage_warmed = 14+ days; later stages (est.)
STAGES = [
    ("new",      0),
    ("warming",  3),
    ("warmed",   14),
    ("active",   30),   # (est.)
    ("trusted",  60),   # (est.)
    ("veteran",  90),   # (est.)
]
YOUNG_COMMENT_COUNT = 10         # first 10 comments...
YOUNG_COMMENT_INTERVAL_MIN = 72  # ...no more often than once per 72 min (logs.warmup_pacing_skip)
WARM_ACTIVE_WINDOWS = [(8, 9), (15, 16), (20, 21)]  # docs modules.warming.settings.active_windows_hint

# action budget per day by stage (est. from docs "budget grows with age")
STAGE_DAILY_BUDGET = {"new": 5, "warming": 15, "warmed": 40, "active": 80, "trusted": 120, "veteran": 200}

# ── risk engine (logs.risk_*) ───────────────────────────────────
RISK_NEW_AGGRESSIVE_DAYS = 3     # <3 days + aggressive = CRITICAL
RISK_AGGRESSIVE_DAYS = 14        # <14 days + aggressive = HIGH
RISK_NEW_COMMENT_CAP = (3, 5)    # recommend cap 3-5 for new accounts
COLD_ACCOUNT_DAYS = 14           # logs.cold_accounts: <14 days activity = low footprint

# ── neuro_shilling ──────────────────────────────────────────────
SCENARIO_STEPS = 24              # 24-step scenario per target (frontend simulator)
SCENARIO_PAUSE = (20, 70)        # seconds between steps
PACE_PRESETS = {"calm": 15.0, "live": 8.0, "hot": 4.0}   # chat pace, sec between replicas

# --- Warming module settings (confirmed by real panel screenshots 2026-10-14) ---
WARMING_WINDOW = {"start_hour": 9, "end_hour": 24, "tz": "Europe/Moscow", "utc_offset": 3}
WARMING_INTENSITY = {
    "cautious":    {"days": (0, 7),   "label": "Осторожный — для новых аккаунтов, 0-7 дней"},
    "normal":      {"days": (7, 30),  "label": "Нормальный — для прогретых аккаунтов, 7-30 дней"},
    "aggressive":  {"days": (30, None), "label": "Агрессивный — для старых аккаунтов, >30 дней"},
}
WARMING_AUTO_ADAPT = True   # «Автоадаптация по стадии аккаунта» toggle — default ON
# Neurocommenting distributed mode: worker threads tagged T1..T10 in the live log console
NEURO_THREAD_TAGS = [f"T{i}" for i in range(1, 11)]
NEURO_PROFILES = ["сбалансированный", "осторожный", "агрессивный"]   # ИИ Защита levels
NEURO_ACCEPT_PROBABILITY = 70   # «принят в работу (вероятность 70)» from live logs
SERIES_LEN_SEC = 40              # burst series length (est.)
ACTIVITY_CURVE_MAX = 19.0        # evening vs night ratio up to 19x (docs even_pace_hint)
REVIVAL_TEMPO = {"fast": 4, "normal": 8, "slow": 15}     # revival tempo sec (frontend sim)

# hourly activity weights (0-23), normalized to mean 1.0, peak/trough ratio ~19
ACTIVITY_WEIGHTS = [
    0.05, 0.03, 0.02, 0.02, 0.02, 0.03, 0.06, 0.12,   # 00-07 night trough
    0.30, 0.55, 0.80, 1.00, 1.10, 1.05, 1.00, 1.05,   # 08-15
    1.20, 1.40, 1.60, 1.80, 1.90, 1.70, 1.20, 0.55,   # 16-23 evening peak (~19x vs 0.02 trough*avg)
]

# ── spam_pm ─────────────────────────────────────────────────────
TASK_LIFETIME_H = 48             # logs.dm_gate_task_lifetime
CHAIN_LEN = (2, 4)               # messages per dialog chain
FOLLOWUP_ENABLED = True          # "dozhim" followups
DEDUP_BY_HISTORY = True          # fleet dedup: never re-message a target

# ── story_mentions ──────────────────────────────────────────────
STORY_FREE_DAILY = 1             # logs.story_mentions_free_daily_limit (non-premium)

# ── modes / enums (OpenAPI) ─────────────────────────────────────
PROTECTION_MODES = ("careful", "balanced", "aggressive")
PARSING_MODES = ("auto", "channels", "comments", "groups", "messages", "users")
ACCOUNT_OPS = ("appeal_spamblock", "check", "check_spamblock", "generate_profiles",
               "leave_chats", "privacy", "reauthorize", "reset_sessions", "set_2fa")
SPAM_PM_MODES = ("direct", "trigger")
CHATTING_GOAL = ("count", "time")
COMMENTING_SELECT = ("all", "random", "keywords")
COMMENTING_TARGET = ("new", "existing", "both")

# ── GGR model (live API response shape, model auto-2026-10-13) ──
GGR_TIERS = [(9.0, "excellent"), (7.5, "good"), (5.5, "fair"), (3.5, "risky"), (0.0, "dead")]
GGR_SHAP_GROUPS = ("vintage", "identity", "network", "behavioural",
                   "spamblock_history", "restoration", "provenance")
GGR_FREE_QUOTA = 3               # checks/day without auth
GGR_COOLDOWN_MIN = 45

# ── plans (public pricing) ──────────────────────────────────────
PLANS = {"basic": {"price_usd": 130, "days": 30, "slots": 3000},
         "full":  {"price_usd": 720, "days": 365, "slots": 5000}}
