# -*- coding: utf-8 -*-
"""gramgpt_engine — clean-room Python implementation of the GramGPT engine logic.

Reconstructed 2026-10 from the public surface of gramgpt.io:
OpenAPI 3.0.3 (92 endpoints), Nuxt frontend chunks, RU panel locale
(2222 engine log templates / 5327 module doc keys), live GGR API responses.

stdlib-only. Plug your own MTProto transport (Telethon etc.) via Engine(transport=...).
"""
from . import constants as C  # noqa: F401
from .aiprotection import DailyLimits, gate, maybe_ai_delay, simulate_human_action  # noqa: F401
from .warming import Account, risk_assessment, warming_allowed, young_comment_delay  # noqa: F401
from .flood import PoolRotator, QuarantineManager  # noqa: F401
from .pacing import activity_weight, replica_delay, revival_delay, scenario_pause  # noqa: F401
from .preflight import run_all as preflight_run_all  # noqa: F401
from .shilling import Persona, ShillingTask, build_scenario, plan_day  # noqa: F401
from .spam_pm import PmTask, PaceLimiter, chain_plan, claim_target, day_plan  # noqa: F401
from .ggr import AccountSignals, score_account, lot_verdict  # noqa: F401
from .account_op import Engine, validate as account_op_validate  # noqa: F401
from .client import GramGPTClient  # noqa: F401
from . import modules as M  # noqa: F401

__version__ = "1.1.0"
__all__ = ["C", "M", "Account", "Engine", "GramGPTClient", "PmTask", "Persona",
           "ShillingTask", "QuarantineManager", "PoolRotator", "DailyLimits",
           "AccountSignals", "score_account", "lot_verdict", "build_scenario",
           "plan_day", "day_plan", "chain_plan", "claim_target", "gate",
           "preflight_run_all", "__version__"]
