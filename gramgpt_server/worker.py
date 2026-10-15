# -*- coding: utf-8 -*-
"""worker.py — task execution engine for the GramGPT backend clone.

Lifecycle (observable contract): waiting -> running -> completed/failed/cancelled.
queue_if_busy keeps a task waiting while its accounts are busy; re-check every
minute; give up after 24h -> failed (stop_reason=queue_timeout).
Log lines are rendered from the real RU template bank (2222 entries) whenever a
matching key exists, else from built-in fallbacks.
"""
import json
import os
import random
import string
import threading
import time

from .store import Store

_HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = {}
_tp = os.path.join(_HERE, "log_templates_ru.json")
if os.path.exists(_tp):
    TEMPLATES = json.load(open(_tp, encoding="utf-8"))


def T(key, default=None, **kw):
    """Render a template; missing keys fall back to default; unfilled
    placeholders are left as-is (never KeyError)."""
    raw = TEMPLATES.get("logs." + key, TEMPLATES.get(key))
    if raw is None:
        raw = default if default is not None else key
    try:
        return string.Formatter().vformat(raw, (), _SafeDict(kw))
    except Exception:
        return raw


class _SafeDict(dict):
    """Missing placeholders get plausible generated values (the real engine
    fills them from live state; the clone simulates)."""

    def __missing__(self, k):
        import random
        kl = k.lower()
        if "time" in kl or "sec" in kl or kl in ("t", "duration"):
            return f"{random.uniform(0.8, 3.4):.1f}"
        if "count" in kl or "num" in kl or kl in ("n", "total", "left", "remaining"):
            return str(random.randint(1, 30))
        if "chat" in kl or "channel" in kl:
            return random.choice(["@tg_маркетинг", "@Код и кофе", "@crypto_insights"])
        if "user" in kl or "name" in kl:
            return random.choice(["Алексей", "Мария", "Дмитрий", "Ольга"])
        return "{" + k + "}"


MODULE_STEPS = {
    # module -> (total_steps_fn, per-step log plan)
    "neuro_commenting": 40,
    "neuro_shilling": 30,
    "mass_react": 25,
    "mass_looking": 20,
    "neuro_chatting": 25,
    "neuro_dialogs": 20,
    "group_spammer": 25,
    "bulk_join": 20,
    "check_numbers": 15,
    "parsing": 18,
    "spam_pm": 25,
    "warming": 12,
    "account_op": 10,
}

THREAD_TAGS = ["T" + str(i) for i in range(1, 11)]
FAKE_CHATS = ["Крипто Инсайды", "AI News RU", "Нейросети чат", "DeFi Alerts",
              "Код и кофе", "TG маркетинг", "Стартапы 2026", "GPT гильдия"]


class TaskWorker(threading.Thread):
    daemon = True

    def __init__(self, store: Store, tick=0.15, speed=1.0):
        super().__init__(name="gg-worker")
        self.store = store
        self.tick = tick
        self.speed = speed          # steps per tick multiplier
        self.rng = random.Random(1337)
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    # ------------------------------------------------------------------
    def run(self):
        while not self._stop.is_set():
            try:
                self.cycle()
            except Exception as e:      # never die
                print("[worker] cycle error:", e)
            time.sleep(self.tick)

    def cycle(self):
        st = self.store
        now = st.now()
        for t in st.rows("SELECT * FROM tasks WHERE status='waiting' ORDER BY id"):
            payload = json.loads(t["payload"] or "{}")
            age_h = (now - t["created"]) / 3600.0
            busy = self._accounts_busy(t["user_id"], payload.get("account_ids", []))
            if busy and payload.get("queue_if_busy"):
                if age_h >= 24:
                    self._finish(t, "failed", stop_reason="queue_timeout")
                continue
            if busy and not payload.get("queue_if_busy"):
                self._finish(t, "failed", stop_reason="accounts_busy")
                continue
            self._start(t, payload)
        for t in st.rows("SELECT * FROM tasks WHERE status='running' ORDER BY id"):
            self._step(t)

    # ------------------------------------------------------------------
    def _accounts_busy(self, user_id, ids):
        if not ids:
            return False
        ph = ",".join("?" * len(ids))
        r = self.store.row(
            f"SELECT COUNT(*) n FROM tasks WHERE user_id=? AND status='running' "
            f"AND json_array_length(payload) IS NOT NULL AND id IN "
            f"(SELECT task_id FROM task_logs WHERE account IN ({ph}))",
            (user_id, *[str(i) for i in ids]))
        return bool(r and r["n"])

    def _start(self, t, payload):
        st = self.store
        n_acc = len(payload.get("account_ids", []))
        st.q("UPDATE tasks SET status='running', started=? WHERE id=?",
             (st.now(), t["id"]))
        st.q("UPDATE accounts SET status='working' WHERE user_id=? AND id IN (%s)"
             % ",".join("?" * n_acc), (t["user_id"], *payload.get("account_ids", [])))
        m = t["module"]
        st.log(t["id"], "info", T(f"{m}_start", f"Запуск модуля {m}"), badge="SYS")
        st.log(t["id"], "info", T("accounts_count", f"Аккаунтов: {n_acc}, распределённый режим",
                                  count=n_acc), badge="SYS")
        if payload.get("ai_protection", True):
            st.log(t["id"], "success",
                   T("ai_protection_on", "ИИ Защита включена • Уровень: сбалансированный"),
                   badge="AI")
        st.bump(t["id"], total=MODULE_STEPS.get(m, 15), done=0)

    def _step(self, t):
        st = self.store
        m = t["module"]
        c = json.loads(t["counters"] or "{}")
        total = c.get("total", MODULE_STEPS.get(m, 15))
        done = c.get("done", 0)
        steps = max(1, int(self.rng.random() * 2 * self.speed) + 1)
        for _ in range(steps):
            if done >= total:
                break
            done += 1
            self._emit(t, m, done, total)
        st.bump(t["id"], done=done)
        if done >= total:
            self._finish(t, "completed")

    def _emit(self, t, m, done, total):
        st = self.store
        tag = self.rng.choice(THREAD_TAGS)
        chat = self.rng.choice(FAKE_CHATS)
        r = self.rng.random()
        if m == "neuro_commenting":
            if done == 1:
                st.log(t["id"], "success", T("monitoring_started",
                       "Мониторинг запущен (аккаунты: {accs}, каналов: {chans})",
                       accs=30, chans=76), badge="SYS")
            elif done % 7 == 2:
                st.log(t["id"], "success", T("connected", "Подключено за {sec}с",
                       sec=round(0.8 + r * 2, 1)), account=tag)
            elif done % 7 == 3:
                st.log(t["id"], "success", T("new_post", "Новый пост в «{chat}»",
                       chat=chat), account=tag)
            elif done % 7 == 4:
                st.log(t["id"], "info", T("post_accepted", "принят в работу (вероятность {p})",
                       p=60 + int(r * 30)), account=tag, badge="AI")
            elif done % 7 == 5:
                st.log(t["id"], "info", T("typing_sim", "Симуляция набора текста ({n} символа)",
                       n=80 + int(r * 200)), account=tag)
            else:
                st.log(t["id"], "success", T("comment_published",
                       "Комментарий опубликован • @{chat}", chat=chat.replace(" ", "_").lower()),
                       account=tag)
                st.bump(t["id"], completed=1)
        elif m in ("mass_react", "mass_looking"):
            if r < 0.08:
                st.log(t["id"], "warning", T("floodwait", "FloodWait {sec}с — аккаунт приостановлен",
                       sec=20 + int(r * 300)), account=tag)
            else:
                st.log(t["id"], "success", T("reaction_ok", "Реакция {emoji} поставлена • @{chat}",
                       emoji=self.rng.choice(["👍", "🔥", "❤", "🎉"]),
                       chat=chat.replace(" ", "_").lower()), account=tag)
                st.bump(t["id"], completed=1)
        elif m == "bulk_join":
            st.log(t["id"], "success" if r > 0.1 else "warning",
                   T("join_result", "Вход в @{chat}: {res}", chat=chat.replace(" ", "_").lower(),
                     res="ok" if r > 0.1 else "flood"), account=tag)
            st.bump(t["id"], completed=1)
        elif m in ("check_numbers", "parsing"):
            kind = "номер" if m == "check_numbers" else "результат"
            st.log(t["id"], "info", T("parse_row", "{kind}: +38097***{tail} → найден (@user{tail})",
                   kind=kind, tail=1000 + int(r * 8999)), account=tag)
            st.bump(t["id"], completed=1)
        elif m == "group_spammer":
            st.log(t["id"], "success", T("chain_msg", "Цепочка {i}/{n} отправлена в «{chat}»",
                   i=1 + done % 4, n=4, chat=chat), account=tag)
            st.bump(t["id"], completed=1)
        elif m == "spam_pm":
            st.log(t["id"], "success", T("pm_sent", "ЛС отправлено • цель #{n}",
                   n=done), account=tag)
            st.bump(t["id"], completed=1)
        elif m in ("neuro_chatting", "neuro_dialogs", "neuro_shilling"):
            if r < 0.1:
                st.log(t["id"], "info", T("replica_gen", "Генерация реплики ({tok} токен)",
                       tok=20 + int(r * 120)), account=tag, badge="AI")
            else:
                st.log(t["id"], "success", T("replica_sent", "Реплика отправлена в «{chat}»",
                       chat=chat), account=tag)
                st.bump(t["id"], completed=1)
        elif m == "warming":
            st.log(t["id"], "info", T("warm_action", "Прогрев: {act} • окно 9-24",
                   act=self.rng.choice(["чтение ленты", "реакция", "вступление в чат", "пауза сна"])),
                   account=tag)
            st.bump(t["id"], completed=1)
        else:  # account_op
            st.log(t["id"], "success", T("op_done", "Операция выполнена", ), account=tag)
            st.bump(t["id"], completed=1)

    def _finish(self, t, status, stop_reason=None):
        st = self.store
        payload = json.loads(t["payload"] or "{}")
        st.q("UPDATE tasks SET status=?, finished=?, stop_reason=? WHERE id=?",
             (status, st.now(), stop_reason, t["id"]))
        ids = payload.get("account_ids", [])
        if ids:
            st.q("UPDATE accounts SET status='active' WHERE user_id=? AND id IN (%s)"
                 % ",".join("?" * len(ids)), (t["user_id"], *ids))
        msg = T("task_completed", "Задача #{id} завершена") if status == "completed" else \
            T("task_failed", "Задача #{id} остановлена: {reason}", reason=stop_reason or status)
        st.log(t["id"], "success" if status == "completed" else "error",
               msg.replace("{id}", str(t["id"])), badge="SYS")
