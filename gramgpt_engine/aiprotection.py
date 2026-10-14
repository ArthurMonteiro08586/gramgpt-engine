# -*- coding: utf-8 -*-
"""ai_protection — human-like activity gating (sleep windows, breaks, delays)."""
import random
import time
from datetime import datetime

from . import constants as C


def in_sleep_window(dt: datetime | None = None) -> bool:
    dt = dt or datetime.now()
    s, e = C.SLEEP_WINDOW
    return s <= dt.hour < e


def in_break_window(dt: datetime | None = None) -> str | None:
    """Return break reason if inside a break window, else None."""
    dt = dt or datetime.now()
    h = dt.hour
    reasons = {0: "early_morning", 1: "lunch_time", 2: "late_evening"}
    for i, (a, b) in enumerate(C.BREAK_WINDOWS):
        lo, hi = min(a, b), max(a, b)
        if a > b:  # wraps midnight (23-01)
            if h >= a or h < b:
                return reasons.get(i, f"break_{i}")
        elif lo <= h < hi:
            return reasons.get(i, f"break_{i}")
    return None


def gate(now: datetime | None = None) -> tuple[bool, str]:
    """Decide whether an action may run now.

    Returns (allowed, reason). Mirrors engine logs:
      - sleep  -> action skipped
      - break  -> action postponed
    """
    if in_sleep_window(now):
        return False, "ai_protection_sleep"
    br = in_break_window(now)
    if br:
        return False, f"ai_protection_break:{br}"
    return True, "ok"


def maybe_ai_delay(rng=None) -> float:
    """5% of actions get a 20-90s 'human hesitation' delay. Returns seconds to wait."""
    rng = rng or random
    if rng.random() < C.AI_DELAY_PROB:
        return rng.uniform(*C.AI_DELAY_RANGE)
    return 0.0


def simulate_human_action(rng=None) -> list[dict]:
    """Generate the typing/read/scroll simulation sequence the engine emits
    around a real action (observed in log templates: 'печатает', 'прочитал', 'скролл')."""
    rng = rng or random
    seq = []
    if rng.random() < 0.8:
        seq.append({"act": "read", "ms": rng.randint(800, 4000)})
    if rng.random() < 0.6:
        seq.append({"act": "scroll", "ms": rng.randint(400, 2500)})
    seq.append({"act": "typing", "ms": rng.randint(1200, 9000)})
    return seq


class DailyLimits:
    """Per-account daily/weekly action caps (docs: daily/weekly limits)."""

    def __init__(self, daily: int, weekly: int | None = None):
        self.daily = daily
        self.weekly = weekly or daily * 5
        self._day: dict[str, int] = {}
        self._week: dict[str, int] = {}

    @staticmethod
    def _k(day: str) -> str:
        return day

    def take(self, account: str, day: str, week: str) -> tuple[bool, str]:
        dk, wk = f"{account}:{day}", f"{account}:{week}"
        if self._day.get(dk, 0) >= self.daily:
            return False, "account_quota_exhausted"
        if self._week.get(wk, 0) >= self.weekly:
            return False, "account_week_quota_exhausted"
        self._day[dk] = self._day.get(dk, 0) + 1
        self._week[wk] = self._week.get(wk, 0) + 1
        return True, "ok"
