# -*- coding: utf-8 -*-
"""pacing — chat activity curve (up to 19x day/night), pace presets, series bursts."""
import random
from datetime import datetime

from . import constants as C

_W = C.ACTIVITY_WEIGHTS
_MEAN = sum(_W) / len(_W)
NORM = [w / _MEAN for w in _W]


def activity_weight(hour: int) -> float:
    """Normalized weight for an hour (mean=1.0). Evening peak vs night trough ~19x."""
    return NORM[hour % 24]


def replica_delay(pace: str, hour: int | None = None, rng=None,
                  even_pace: bool = False) -> float:
    """Delay between replicas in a shilling/chatting conversation.

    pace: calm=15s / live=8s / hot=4s (PACE_PRESETS)
    Scaled by the hour activity curve unless even_pace=True
    (docs: 'Ровный темп круглосуточно' toggle).
    """
    rng = rng or random
    base = C.PACE_PRESETS[pace]
    if hour is None:
        hour = datetime.now().hour
    w = 1.0 if even_pace else activity_weight(hour)
    # higher activity -> shorter delays (inverse), clamp 0.3x..3x
    scale = min(3.0, max(0.3, 1.0 / max(w, 0.05)))
    return round(base * scale * rng.uniform(0.7, 1.4), 2)


def in_series(rng=None) -> int:
    """Number of fast replicas in a burst series (~40s window at live pace)."""
    rng = rng or random
    return max(2, int(C.SERIES_LEN_SEC / C.PACE_PRESETS["live"] * rng.uniform(0.6, 1.2)))


def scenario_pause(rng=None) -> float:
    """Pause between scenario steps: 20-70s."""
    rng = rng or random
    return rng.uniform(*C.SCENARIO_PAUSE)


def reaction_delay(lo: float, hi: float, rng=None) -> float:
    """docs reactions_block.delay_hint: random within user bounds; 0,0 = auto."""
    rng = rng or random
    if lo <= 0 and hi <= 0:
        return rng.uniform(3.0, 12.0)
    return rng.uniform(lo, max(hi, lo + 0.5))


def revival_delay(tempo: str, rng=None) -> float:
    """Revival tempo presets: fast=4s normal=8s slow=15s (frontend simulator)."""
    rng = rng or random
    base = C.REVIVAL_TEMPO[tempo]
    return base * rng.uniform(0.8, 1.25)
