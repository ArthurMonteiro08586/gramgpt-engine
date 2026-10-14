# -*- coding: utf-8 -*-
"""warming — account lifecycle: new -> warming -> warmed -> active -> trusted -> veteran.

Budget grows with age; young accounts obey the 72-min rule for first 10 comments;
warming runs only inside configured active windows.
"""
from datetime import datetime, timedelta

from . import constants as C


class Account:
    __slots__ = ("id", "phone", "created", "comments_sent", "actions_today",
                 "quarantine_until", "spamblock", "dead", "last_used", "day_actions")

    def __init__(self, id: int, phone: str, created: datetime, day: str = ""):
        self.id = id
        self.phone = phone
        self.created = created
        self.comments_sent = 0
        self.actions_today = 0
        self.day_actions: dict[str, int] = {}
        self.quarantine_until: datetime | None = None
        self.spamblock = False
        self.dead = False
        self.last_used: datetime | None = None

    def age_days(self, now: datetime | None = None) -> float:
        return ((now or datetime.now()) - self.created).total_seconds() / 86400.0

    def stage(self, now: datetime | None = None) -> str:
        age = self.age_days(now)
        stage = "new"
        for name, min_days in C.STAGES:
            if age >= min_days:
                stage = name
        return stage

    def budget(self, now: datetime | None = None) -> int:
        return C.STAGE_DAILY_BUDGET[self.stage(now)]


def young_comment_delay(acc: Account, now: datetime | None = None) -> timedelta | None:
    """First 10 comments: no more often than once per 72 minutes (logs.warmup_pacing_skip)."""
    if acc.comments_sent >= C.YOUNG_COMMENT_COUNT:
        return None
    if acc.last_used is None:
        return None
    elapsed = (now or datetime.now()) - acc.last_used
    need = timedelta(minutes=C.YOUNG_COMMENT_INTERVAL_MIN)
    return need - elapsed if elapsed < need else None


def in_active_window(now: datetime | None = None, windows=None) -> bool:
    now = now or datetime.now()
    windows = windows or C.WARM_ACTIVE_WINDOWS
    return any(a <= now.hour < b for a, b in windows)


def warming_allowed(acc: Account, now: datetime | None = None, windows=None) -> tuple[bool, str]:
    if acc.dead:
        return False, "dead"
    if acc.spamblock:
        return False, "spamblock"
    if acc.quarantine_until and (now or datetime.now()) < acc.quarantine_until:
        return False, "quarantine"
    if not in_active_window(now, windows):
        return False, "outside_active_window"
    day = (now or datetime.now()).strftime("%Y-%m-%d")
    if acc.day_actions.get(day, 0) >= acc.budget(now):
        return False, "daily_budget_reached"
    return True, "ok"


def register_action(acc: Account, now: datetime | None = None, comment: bool = False):
    now = now or datetime.now()
    day = now.strftime("%Y-%m-%d")
    acc.day_actions[day] = acc.day_actions.get(day, 0) + 1
    acc.last_used = now
    if comment:
        acc.comments_sent += 1


def risk_assessment(acc: Account, mode: str, comment_cap: int, now: datetime | None = None) -> tuple[str, str]:
    """logs.risk_* rules. Returns (level, message_key)."""
    age = acc.age_days(now)
    if mode == "aggressive" and age < C.RISK_NEW_AGGRESSIVE_DAYS:
        return "critical", "risk_critical_new_account"
    if age < C.RISK_NEW_AGGRESSIVE_DAYS and comment_cap > C.RISK_NEW_COMMENT_CAP[1]:
        return "critical", "risk_critical"
    if mode == "aggressive" and age < C.RISK_AGGRESSIVE_DAYS:
        return "high", "risk_high_new_aggressive"
    if age < C.RISK_AGGRESSIVE_DAYS:
        return "high", "risk_high"
    return "ok", ""
