# -*- coding: utf-8 -*-
"""preflight — task-level anti-fraud checks the engine runs BEFORE launch.

Observed in log templates / OpenAPI descriptions:
- supplier_fraud_batch: batch of accounts from one fraudulent supplier
  (shadow_fraud.authkey_cross_user_dups / supplier_fraud flags from GGR)
- lot_burn: the whole lot dies abnormally fast -> stop spending the lot
- identical broadcast: same text to many targets in one wave = spam signature
"""
import hashlib
import re
from collections import Counter


def supplier_fraud_batch(accounts: list[dict]) -> dict:
    """accounts: [{id, ggr_meta: {shadow_fraud: {...}}}]. Flags a batch when
    cross-user authkey duplicates or supplier_fraud appear."""
    flagged, dups = [], 0
    for a in accounts:
        sf = (a.get("ggr_meta") or {}).get("shadow_fraud") or {}
        if sf.get("supplier_fraud") or (sf.get("authkey_cross_user_dups") or 0) > 0:
            flagged.append(a.get("id"))
            dups += sf.get("authkey_cross_user_dups") or 0
    return {"verdict": "supplier_fraud_batch" if flagged else "ok",
            "flagged": flagged, "authkey_dups": dups}


def lot_burn(lot: dict, death_rate_threshold: float = 0.5) -> dict:
    """lot: {date, total, dead}. Engine stops feeding a lot that burns."""
    total, dead = lot.get("total", 0), lot.get("dead", 0)
    rate = dead / total if total else 0.0
    return {"verdict": "lot_burn" if rate >= death_rate_threshold else "ok",
            "death_rate": round(rate, 4), "total": total, "dead": dead}


_NORM_RE = re.compile(r"\s+")


def identical_broadcast(texts: list[str], threshold: int = 5) -> dict:
    """Same normalized text repeated >= threshold times in one wave = burn signature.
    Engine requires variation (chain/offer rotation)."""
    norm = [ _NORM_RE.sub(" ", t.strip().lower()) for t in texts ]
    counts = Counter(hashlib.sha1(n.encode()).hexdigest()[:12] for n in norm)
    hot = [(h, c) for h, c in counts.items() if c >= threshold]
    return {"verdict": "identical_broadcast" if hot else "ok",
            "duplicates": [{"hash": h, "count": c} for h, c in hot],
            "unique_ratio": round(len(set(norm)) / max(1, len(norm)), 3)}


def run_all(accounts: list[dict], lot: dict, texts: list[str]) -> dict:
    checks = {
        "supplier_fraud": supplier_fraud_batch(accounts),
        "lot_burn": lot_burn(lot),
        "identical_broadcast": identical_broadcast(texts),
    }
    blocked = [k for k, v in checks.items() if v["verdict"] != "ok"]
    return {"allow_launch": not blocked, "blocked_by": blocked, "checks": checks}
