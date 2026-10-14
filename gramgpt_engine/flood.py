# -*- coding: utf-8 -*-
"""flood — FloodWait / spamblock quarantine and pool rotation.

Engine rules (from log templates):
- FloodWait on an account -> quarantine 24h, task continues on the rest of the pool
- spamblock verdict -> quarantine 24h
- ALL accounts in FLOOD -> task stops, accounts are untouched (no burn)
"""
from datetime import datetime, timedelta

from . import constants as C
from .warming import Account


class QuarantineManager:
    def __init__(self, hours: int = C.QUARANTINE_HOURS):
        self.hours = hours
        self.log: list[dict] = []

    def quarantine(self, acc: Account, reason: str, now: datetime | None = None,
                   wait_seconds: int | None = None):
        now = now or datetime.now()
        until = now + timedelta(hours=self.hours)
        acc.quarantine_until = until
        if reason == "spamblock":
            acc.spamblock = True
        entry = {"ts": now.isoformat(), "phone": acc.phone, "reason": reason,
                 "until": until.isoformat(), "wait_seconds": wait_seconds}
        self.log.append(entry)
        return entry

    def handle_flood(self, acc: Account, wait_seconds: int, now: datetime | None = None) -> dict:
        """logs.account_quarantine_flood_wait: 'Карантин 24ч до {until} (FloodWait {s}с)'"""
        return self.quarantine(acc, "flood", now, wait_seconds)

    def handle_spamblock(self, acc: Account, now: datetime | None = None) -> dict:
        """logs.account_spamblock_quarantine: 'Аккаунт заблокирован (спамблок) — карантин 24ч'"""
        return self.quarantine(acc, "spamblock", now)

    def release_expired(self, accounts: list[Account], now: datetime | None = None) -> list[Account]:
        now = now or datetime.now()
        released = []
        for a in accounts:
            if a.quarantine_until and a.quarantine_until <= now:
                a.quarantine_until = None
                released.append(a)
        return released


class PoolRotator:
    """Round-robin over non-quarantined accounts; all_flood -> stop task."""

    def __init__(self, accounts: list[Account]):
        self.accounts = accounts
        self._i = 0

    def available(self, now: datetime | None = None) -> list[Account]:
        now = now or datetime.now()
        return [a for a in self.accounts
                if not a.dead and (a.quarantine_until is None or a.quarantine_until <= now)]

    def next(self, now: datetime | None = None) -> Account | None:
        avail = self.available(now)
        if not avail:
            return None
        self._i = (self._i + 1) % len(avail)
        return avail[self._i]

    def all_flooded(self, now: datetime | None = None) -> bool:
        """True when every account sits in quarantine -> engine stops the task,
        accounts remain untouched (no forced burn)."""
        return len(self.available(now)) == 0 and len(self.accounts) > 0
