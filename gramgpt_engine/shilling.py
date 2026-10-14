# -*- coding: utf-8 -*-
"""neuro_shilling — 24-step scenario engine per target chat.

Reconstructed from frontend simulator generators (10 generators, 77 event types)
and RU module docs: personas, roles, pools, cohorts, pace, revival, activity curve.
This module plans the scenario; actual sending is delegated to a transport callable
so the engine stays stdlib-only (plug Telethon/MTProto yourself).
"""
import random
from dataclasses import dataclass, field
from datetime import datetime

from . import constants as C
from .pacing import activity_weight, replica_delay, revival_delay, scenario_pause


@dataclass
class Persona:
    name: str
    role: str                 # initiator / supporter / skeptic / expert / bystander
    style: str = "neutral"
    messages_sent: int = 0


@dataclass
class ScenarioStep:
    n: int
    persona: str
    role: str
    action: str               # message | reaction | reply | question | proof | offtopic
    payload: str
    delay_before: float
    hour: int = -1


@dataclass
class ShillingTask:
    target: str
    subject: str
    personas: list[Persona]
    pace: str = "live"
    even_pace: bool = False
    revival: bool = False
    revival_tempo: str = "normal"
    reactions_only: bool = False
    daily_budget: int = 60
    steps: list[ScenarioStep] = field(default_factory=list)


ACTIONS = ["message", "reaction", "reply", "question", "proof", "offtopic"]
# scenario arc: warm-up offtopic -> subject intro -> questions -> proofs -> reactions
ARC = (["offtopic"] * 4 + ["message"] * 3 + ["question"] * 3 + ["message"] * 3 +
       ["proof"] * 3 + ["reply"] * 3 + ["reaction"] * 3 + ["message", "question"])


def build_scenario(task: ShillingTask, rng: random.Random | None = None,
                   start_hour: int = 12) -> list[ScenarioStep]:
    """Generate the 24-step scenario (C.SCENARIO_STEPS) with per-step persona
    rotation, human pauses 20-70s and pace-scaled replica delays."""
    rng = rng or random.Random()
    steps = []
    for i in range(C.SCENARIO_STEPS):
        p = task.personas[i % len(task.personas)]
        action = "reaction" if task.reactions_only else ARC[i % len(ARC)]
        hour = (start_hour + i // 6) % 24
        if task.revival:
            delay = revival_delay(task.revival_tempo, rng)
        else:
            delay = scenario_pause(rng) + replica_delay(task.pace, hour, rng, task.even_pace)
        steps.append(ScenarioStep(
            n=i + 1, persona=p.name, role=p.role, action=action,
            payload=f"step{i+1}:{task.subject}", delay_before=round(delay, 2), hour=hour))
    task.steps = steps
    return steps


def budget_for_hour(hour: int, daily_budget: int) -> int:
    """Split the daily budget across hours by the activity curve (peak evening)."""
    w = activity_weight(hour)
    total_w = sum(activity_weight(h) for h in range(24))
    return max(0, round(daily_budget * w / total_w))


def plan_day(task: ShillingTask, rng: random.Random | None = None) -> dict[int, int]:
    """Even-pace toggle off -> budget follows the curve (up to 19x trough/peak)."""
    if task.even_pace:
        base = task.daily_budget // 24
        return {h: base for h in range(24)}
    return {h: budget_for_hour(h, task.daily_budget) for h in range(24)}


def next_step_due(task: ShillingTask, now: datetime, sent_today: int) -> ScenarioStep | None:
    """Pick the next scenario step if the hour budget and daily budget allow it."""
    if sent_today >= task.daily_budget:
        return None
    plan = plan_day(task)
    if plan[now.hour] <= 0:
        return None
    idx = sent_today % len(task.steps) if task.steps else -1
    return task.steps[idx] if idx >= 0 else None
