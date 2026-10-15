# -*- coding: utf-8 -*-
"""store.py — SQLite persistence for the GramGPT backend clone (stdlib only).

Tables mirror the observable API surface: users, accounts, tasks, task_logs,
photos, prompts, proxies, blacklists, history, webhooks, exports.
"""
import json
import sqlite3
import threading
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY, token TEXT UNIQUE, username TEXT, plan TEXT DEFAULT 'basic',
  quota_total INTEGER DEFAULT 1000, quota_used INTEGER DEFAULT 0,
  balance REAL DEFAULT 0, created REAL);
CREATE TABLE IF NOT EXISTS accounts(
  id INTEGER PRIMARY KEY, user_id INTEGER, phone TEXT, username TEXT, first_name TEXT,
  status TEXT DEFAULT 'active', stage TEXT DEFAULT 'new', ggr REAL, ggr_tier TEXT,
  premium INTEGER DEFAULT 0, proxy TEXT, project TEXT, created REAL, meta TEXT);
CREATE TABLE IF NOT EXISTS tasks(
  id INTEGER PRIMARY KEY, user_id INTEGER, module TEXT, status TEXT DEFAULT 'waiting',
  payload TEXT, stop_reason TEXT, created REAL, started REAL, finished REAL,
  counters TEXT DEFAULT '{}');
CREATE TABLE IF NOT EXISTS task_logs(
  id INTEGER PRIMARY KEY, task_id INTEGER, ts REAL, level TEXT, account TEXT,
  badge TEXT, message TEXT);
CREATE TABLE IF NOT EXISTS photos(
  id INTEGER PRIMARY KEY, user_id INTEGER, url TEXT, tags TEXT, used INTEGER DEFAULT 0,
  created REAL);
CREATE TABLE IF NOT EXISTS prompts(
  id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, text TEXT, module TEXT, created REAL);
CREATE TABLE IF NOT EXISTS proxies(
  id INTEGER PRIMARY KEY, user_id INTEGER, url TEXT, kind TEXT, alive INTEGER DEFAULT 1,
  attached_to TEXT, last_check REAL);
CREATE TABLE IF NOT EXISTS blacklists(
  id INTEGER PRIMARY KEY, user_id INTEGER, kind TEXT, value TEXT, created REAL,
  UNIQUE(user_id, kind, value));
CREATE TABLE IF NOT EXISTS history(
  id INTEGER PRIMARY KEY, user_id INTEGER, module TEXT, action TEXT, detail TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS webhooks(
  id INTEGER PRIMARY KEY, user_id INTEGER, url TEXT, events TEXT, secret TEXT,
  active INTEGER DEFAULT 1, created REAL);
CREATE TABLE IF NOT EXISTS exports(
  id TEXT PRIMARY KEY, user_id INTEGER, kind TEXT, status TEXT DEFAULT 'pending',
  created REAL, finished REAL, data TEXT);
CREATE INDEX IF NOT EXISTS idx_logs_task ON task_logs(task_id, id);
CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id, id);
CREATE INDEX IF NOT EXISTS idx_accounts_user ON accounts(user_id, id);
"""

ACCOUNT_STATUSES = ("active", "working", "banned", "invalid", "muted",
                    "spamblocked", "frozen", "quarantined", "reauth")


class Store:
    def __init__(self, path=":memory:"):
        self.path = path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA busy_timeout=15000")
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def q(self, sql, args=()):
        with self._lock:
            cur = self._conn.execute(sql, args)
            self._conn.commit()
            return cur

    def rows(self, sql, args=()):
        with self._lock:
            return [dict(r) for r in self._conn.execute(sql, args).fetchall()]

    def row(self, sql, args=()):
        with self._lock:
            r = self._conn.execute(sql, args).fetchone()
            return dict(r) if r else None

    # ---- helpers -------------------------------------------------------
    def now(self):
        return time.time()

    def insert(self, table, **kw):
        cols = ", ".join(kw)
        ph = ", ".join("?" * len(kw))
        cur = self.q(f"INSERT INTO {table} ({cols}) VALUES ({ph})",
                     tuple(_enc(v) for v in kw.values()))
        return cur.lastrowid

    def log(self, task_id, level, message, account="", badge=""):
        self.insert("task_logs", task_id=task_id, ts=self.now(), level=level,
                    account=account, badge=badge, message=message)

    def bump(self, task_id, **counters):
        t = self.row("SELECT counters FROM tasks WHERE id=?", (task_id,))
        if not t:
            return
        c = json.loads(t["counters"] or "{}")
        for k, v in counters.items():
            c[k] = v if not isinstance(c.get(k), int) or not isinstance(v, int) else c[k] + v
        self.q("UPDATE tasks SET counters=? WHERE id=?", (json.dumps(c, ensure_ascii=False), task_id))


def _enc(v):
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, bool):
        return int(v)
    return v
