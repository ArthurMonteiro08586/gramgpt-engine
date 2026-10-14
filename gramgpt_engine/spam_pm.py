# -*- coding: utf-8 -*-
"""spam_pm — DM outreach task engine.

Spec from log templates + OpenAPI launch_spam_pm:
- task lifetime 48h (logs.dm_gate_task_lifetime)
- day plan; followups ("dozhim") after the plan
- dialog chains 2-4 messages
- fleet dedup by history: a target is never messaged twice across the fleet
- pace limits per account: hourly slot pause, daily stop (docs safety.hint)
- modes: direct | trigger; protection: careful | balanced | aggressive
"""
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from . import constants as C


@dataclass
class PmTask:
    name: str
    texts: list[str]              # offer rotation pool
    targets: list[str]
    mode: str = "direct"          # direct | trigger
    protection: str = "balanced"  # careful | balanced | aggressive
    hourly_limit: int = 12        # per account
    daily_limit: int = 40         # per account
    created: datetime = field(default_factory=datetime.now)
    history: set = field(default_factory=set)   # fleet-wide dedup

    def alive(self, now: datetime | None = None) -> bool:
        now = now or datetime.now()
        return (now - self.created) <= timedelta(hours=C.TASK_LIFETIME_H)

    def remaining_hours(self, now: datetime | None = None) -> float:
        now = now or datetime.now()
        left = timedelta(hours=C.TASK_LIFETIME_H) - (now - self.created)
        return max(0.0, left.total_seconds() / 3600.0)


def chain_plan(rng=None) -> int:
    """2-4 messages per dialog chain."""
    rng = rng or random
    return rng.randint(*C.CHAIN_LEN)


def pick_text(task: PmTask, target: str, rng=None) -> str:
    """Offer rotation — never identical broadcast (see preflight.identical_broadcast)."""
    rng = rng or random
    h = sum(ord(c) for c in target)
    return task.texts[(h + rng.randint(0, len(task.texts) - 1)) % len(task.texts)]


def claim_target(task: PmTask, target: str) -> bool:
    """Fleet dedup: returns False if this target was already messaged by ANY account."""
    if not C.DEDUP_BY_HISTORY:
        return True
    if target in task.history:
        return False
    task.history.add(target)
    return True


class PaceLimiter:
    """Hourly slot pause + daily stop (docs group_spammer.safety.hint)."""

    def __init__(self, task: PmTask):
        self.task = task
        self._hour: dict[str, int] = {}
        self._day: dict[str, int] = {}

    def allow(self, account: str, now: datetime | None = None) -> tuple[bool, str, float]:
        """Returns (allowed, reason, pause_seconds)."""
        now = now or datetime.now()
        hk = f"{account}:{now.strftime('%Y%m%d%H')}"
        dk = f"{account}:{now.strftime('%Y%m%d')}"
        if self._day.get(dk, 0) >= self.task.daily_limit:
            secs = (now.replace(hour=0, minute=0, second=0) + timedelta(days=1) - now).total_seconds()
            return False, "daily_stop", secs
        if self._hour.get(hk, 0) >= self.task.hourly_limit:
            secs = 3600 - (now.minute * 60 + now.second)
            return False, "hourly_slot_pause", secs
        return True, "ok", 0.0

    def register(self, account: str, now: datetime | None = None):
        now = now or datetime.now()
        hk = f"{account}:{now.strftime('%Y%m%d%H')}"
        dk = f"{account}:{now.strftime('%Y%m%d')}"
        self._hour[hk] = self._hour.get(hk, 0) + 1
        self._day[dk] = self._day.get(dk, 0) + 1


def day_plan(task: PmTask, accounts: list[str], now: datetime | None = None) -> dict:
    """logs.dm_gate_daily_plan_done — distribute remaining targets over remaining
    lifetime of the task (<=48h)."""
    now = now or datetime.now()
    rem_targets = [t for t in task.targets if t not in task.history]
    rem_hours = task.remaining_hours(now)
    days = max(1, int(rem_hours // 24) + (1 if rem_hours % 24 else 0))
    per_day = max(1, len(rem_targets) // days)
    per_account = max(1, min(task.daily_limit, per_day // max(1, len(accounts))))
    return {"remaining_targets": len(rem_targets), "remaining_hours": round(rem_hours, 2),
            "days_left": days, "per_day": per_day, "per_account_today": per_account,
            "feasible": per_day <= len(accounts) * task.daily_limit}
