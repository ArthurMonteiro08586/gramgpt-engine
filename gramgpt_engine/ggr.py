# -*- coding: utf-8 -*-
"""ggr — local re-implementation of the GGR account-quality scorer.

Public API response shape (live-captured 2026-10-14, model auto-2026-10-13):
  score (0-10), tier, ml_score, risk_probability, lifespan_days_median,
  cohort_survival{survival_7d,...}, lot_score{current_lot,previous_lot,source_3w},
  meta{shadow_fraud{authkey_cross_user_dups,supplier_fraud}, age_band, spamblock_verdict},
  recommendation{headline_key, body_key}
SHAP groups: vintage, identity, network, behavioural, spamblock_history,
restoration, provenance.

This is a deterministic heuristic clone of the OBSERVABLE scoring behaviour
(weights fitted to captured live responses), not their proprietary model.
"""
import math
from dataclasses import dataclass, field
from datetime import datetime

from . import constants as C


@dataclass
class AccountSignals:
    age_days: float = 0.0
    has_2fa: bool = False
    has_username: bool = False
    has_photo: bool = False
    phone_visible: bool = False
    spamblock_history: int = 0        # count of past spamblocks
    restored: bool = False            # session reauthorized recently
    authkey_dups: int = 0             # cross-user authkey duplicates (shadow fraud)
    lot_dead_rate: float = 0.0        # death rate of source lot (3w window)
    proxy_shared: int = 1             # accounts sharing exit IP
    actions_last_7d: int = 0
    premium: bool = False


@dataclass
class GgrVerdict:
    score: float
    tier: str
    risk_probability: float
    shap: dict = field(default_factory=dict)
    recommendation: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)


def _clamp(x: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, x))


def score_account(s: AccountSignals, now: datetime | None = None) -> GgrVerdict:
    """Deterministic scoring. Group contributions mirror the SHAP groups."""
    # vintage: age is the strongest positive (log-scaled, plateaus ~180d)
    vintage = _clamp(2.6 * math.log1p(s.age_days / 12.0), 0, 3.2)
    # identity: username/photo/2fa completeness
    identity = 0.6 * s.has_username + 0.6 * s.has_photo + 0.8 * s.has_2fa + (0.3 if not s.phone_visible else 0.0)
    identity = _clamp(identity, 0, 2.0)
    # network: shared proxy penalty
    network = _clamp(1.2 - 0.15 * max(0, s.proxy_shared - 1), 0, 1.2)
    # behavioural: activity without burn
    behavioural = _clamp(0.4 + min(s.actions_last_7d, 60) / 60.0 * 1.2 + (0.3 if s.premium else 0.0), 0, 1.8)
    # spamblock_history: hard penalty
    spamblock_history = _clamp(-1.6 * s.spamblock_history, -3.2, 0)
    # restoration: recently restored session = mild suspicion
    restoration = -0.7 if s.restored else 0.0
    # provenance: lot death rate + shadow fraud
    provenance = _clamp(-4.0 * s.lot_dead_rate - 1.5 * min(s.authkey_dups, 2), -4.0, 0)

    raw = 1.4 + vintage + identity + network + behavioural + spamblock_history + restoration + provenance
    score = round(_clamp(raw), 1)

    tier = "dead"
    for thr, name in C.GGR_TIERS:
        if score >= thr:
            tier = name
            break

    # risk probability: logistic from the negative contributors
    neg = -(spamblock_history + restoration + provenance) + max(0.0, 2.0 - (vintage + identity))
    risk = round(1.0 / (1.0 + math.exp(-(neg - 2.2) * 0.9)), 4)

    survival_7d = round(_clamp(1.0 - risk * 0.9 - s.lot_dead_rate * 0.5, 0.0, 1.0), 4)

    # recommendation keys observed live: account_in_transit/wait_until_active etc.
    if s.age_days < 3:
        rec = {"headline_key": "account_in_transit", "body_key": "wait_until_active"}
    elif tier in ("dead", "risky"):
        rec = {"headline_key": "high_risk_account", "body_key": "do_not_use_for_broadcast"}
    elif s.spamblock_history:
        rec = {"headline_key": "spamblock_history", "body_key": "warm_before_use"}
    else:
        rec = {"headline_key": "account_ready", "body_key": "good_for_tasks"}

    return GgrVerdict(
        score=score, tier=tier, risk_probability=risk,
        shap={"vintage": round(vintage, 3), "identity": round(identity, 3),
              "network": round(network, 3), "behavioural": round(behavioural, 3),
              "spamblock_history": round(spamblock_history, 3),
              "restoration": round(restoration, 3), "provenance": round(provenance, 3)},
        recommendation=rec,
        meta={"model_version": "local-clone-1.0", "predicted_at": (now or datetime.now()).isoformat(),
              "shadow_fraud": {"detected": s.authkey_dups > 0,
                               "authkey_cross_user_dups": s.authkey_dups,
                               "supplier_fraud": s.authkey_dups > 2},
              "cohort_survival": {"survival_7d": survival_7d},
              "score_source": "local"},
    )


def lot_verdict(total: int, dead: int) -> dict:
    """lot_score shape from the live response."""
    rate = dead / total if total else 0.0
    return {"total": total, "dead": dead, "death_rate": round(rate, 4),
            "burn": rate >= 0.5, "survival_7d": round(1.0 - rate, 4)}
