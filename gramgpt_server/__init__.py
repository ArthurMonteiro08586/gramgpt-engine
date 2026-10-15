# -*- coding: utf-8 -*-
"""gramgpt_server — full clean-room backend clone of gramgpt.io.

All 101 routes from their OpenAPI 3.0.3 spec (92 paths), Bearer ggk_live_*
auth, SQLite persistence, task worker executing all 13 launch modules on
gramgpt_engine logic, RU log templates rendered from their real template bank.

stdlib-only. Run: python examples/run_server.py [--port 8770] [--db gg.db]
"""
from .app import Server  # noqa: F401
from .store import Store  # noqa: F401
from .worker import TaskWorker  # noqa: F401

__version__ = "1.0.0"
