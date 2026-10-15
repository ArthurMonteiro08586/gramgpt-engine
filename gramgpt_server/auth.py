# -*- coding: utf-8 -*-
"""auth.py — Bearer ggk_live_* token auth (clone-local issuance).

Real GramGPT issues keys after Tribute/Stripe payment. The clone issues
deterministic local keys: POST /api/v1/auth/token (clone-only extension,
not part of their OpenAPI) or env GG_DEMO_TOKEN.
"""
import hashlib
import secrets

from .store import Store

PREFIX = "ggk_live_"


def issue_token(store: Store, username="demo", plan="basic", quota_total=1000,
                balance=0.0, token=None):
    token = token or PREFIX + secrets.token_hex(16)
    existing = store.row("SELECT id FROM users WHERE token=?", (token,))
    if existing:  # idempotent across restarts (UNIQUE users.token)
        return token
    store.insert("users", token=token, username=username, plan=plan,
                 quota_total=quota_total, quota_used=0, balance=balance,
                 created=store.now())
    return token


def user_by_token(store: Store, token):
    if not token or not token.startswith(PREFIX):
        return None
    return store.row("SELECT * FROM users WHERE token=?", (token,))


def fingerprint(token):
    return hashlib.sha256(token.encode()).hexdigest()[:12]
