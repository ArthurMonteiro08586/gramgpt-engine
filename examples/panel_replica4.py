# -*- coding: utf-8 -*-
"""panel_replica4.py — Task Monitor replica built ON THEIR REAL CSS.

Source of truth (downloaded from gramgpt.io/_nuxt/ 2026-10-14):
  - task-monitor.BVhk1W4S.css  (20KB, 81 tm-* classes, dark tokens)
  - neuro-commenting.Bdlz8ued.css (module-page dark background)
  - logs.CdsstloZ.css (log row grid)
Rules are copied VERBATIM (scoped [data-v-*] attributes stripped), class names
and DOM structure follow the real component; data = live panel screenshots.
"""
import re
import sys

CSS_SRC = r"C:/Users/User/tmp/rev_targets/gramgpt/panel_css/task-monitor.BVhk1W4S.css"
NC_SRC = r"C:/Users/User/tmp/rev_targets/gramgpt/panel_css/neuro-commenting.Bdlz8ued.css"


def load_unscoped(path, keep=None):
    t = open(path, encoding="utf-8", errors="ignore").read()
    t = re.sub(r"\[data-v-[0-9a-fA-F]+\]", "", t)          # strip vue scoping
    if keep:
        # keep only rules whose selector mentions one of the keep-tokens
        out, buf, depth = [], "", 0
        for ch in t:
            buf += ch
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    sel = buf[: buf.index("{")]
                    if any(k in sel for k in keep):
                        out.append(buf)
                    buf = ""
        t = "".join(out)
    return t


TM_CSS = load_unscoped(CSS_SRC)
NC_CSS = load_unscoped(NC_SRC, keep=[".module-page", ".page-header", ".page-title", ".page-subtitle"])

LOG_ROWS = [
    # (time, acc, level, badge, msg)
    ("16:31:02", "SYS", "info", "", "Запуск модуля Нейрокомментинг"),
    ("16:31:02", "SYS", "info", "", "Аккаунтов: 30, распределённый режим"),
    ("16:31:03", "SYS", "success", "AI", "ИИ Защита включена • Уровень: сбалансированный"),
    ("16:31:05", "SYS", "success", "", "Мониторинг запущен (аккаунты: 30, каналов: 76)"),
    ("16:33:41", "T2", "success", "", "Подключено за 1.6с"),
    ("16:35:12", "T4", "info", "", "Поток: мониторинг 8 каналов"),
    ("16:38:20", "T3", "success", "", "Новый пост в «Крипто Инсайды»"),
    ("16:38:21", "T3", "info", "AI", "принят в работу (вероятность 70)"),
    ("16:38:24", "T3", "info", "", "Симуляция набора текста (164 символа)"),
    ("16:41:07", "T7", "success", "", "Комментарий опубликован • @crypto_insights"),
    ("16:44:55", "T5", "warning", "", "FloodWait 38с — аккаунт приостановлен"),
    ("16:47:19", "T9", "success", "", "Подключено за 1.2с"),
    ("16:49:03", "T6", "info", "AI", "Генерация ответа (qwen, 41 токен)"),
    ("16:49:31", "T6", "success", "", "Комментарий опубликован • @ai_news_ru"),
]

TASKS = [
    ("16:31", "Нейрокомментинг", "live", "72 логов", "65 в работе", "7 завершено", "alex_smirnov", True),
    ("14:02", "Прогрев аккаунтов", "live", "310 логов", "2 341 акк", "окно 9-24", "alex_smirnov", False),
    ("09:47", "Масс Реакции", "done", "18 логов", "1 204 ок", "2 ошиб", "alex_smirnov", False),
]


def log_row_html(r):
    time, acc, level, badge, msg = r
    b = f'<span class="tm-log-badge">{badge}</span>' if badge else "<span></span>"
    return (f'<div class="tm-log-row" data-level="{level}">'
            f'<span class="tm-log-time">{time}</span>'
            f'<button class="tm-log-acc">{acc}</button>'
            f'{b}'
            f'<span class="tm-log-msg">{msg}</span></div>')


def task_card_html(t):
    time, mod, dot, s1, s2, s3, user, sel = t
    return (f'<button class="tm-card{" selected" if sel else ""}">'
            f'<span class="tm-dot {dot}"></span>'
            f'<span class="tm-card-time">{time}</span>'
            f'<span class="tm-card-module"><span class="tm-card-name">{mod}</span></span>'
            f'<span class="tm-card-stats"><span>{s1}</span><b class="ok">{s2}</b><span>{s3}</span></span>'
            f'<span class="tm-card-user">{user}</span></button>')


def main(out):
    rows = "\n".join(log_row_html(r) for r in LOG_ROWS)
    cards = "\n".join(task_card_html(t) for t in TASKS)
    html = f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<title>GramGPT — Task Monitor (replica v4, real component CSS)</title>
<style>
:root {{ color-scheme: dark; }}
* {{ box-sizing: border-box; }}
html,body {{ margin:0; }}
body {{ background: radial-gradient(1100px 480px at 82% -12%, rgba(0,136,204,.10), transparent 60%),
        radial-gradient(840px 420px at 6% -8%, rgba(56,189,248,.07), transparent 58%),
        linear-gradient(180deg,#0a0f1a,#070a12);
        min-height:100vh; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; }}
/* ==== VERBATIM: task-monitor.BVhk1W4S.css (data-v stripped) ==== */
{TM_CSS}
/* ==== VERBATIM: neuro-commenting module page/header (data-v stripped) ==== */
{NC_CSS}
/* replica glue: put tm-root into a module-page shell */
.shell {{ max-width:1400px; margin:0 auto; padding:1rem 1.5rem 1.5rem; }}
.shell .tm-root {{ height:860px; border-radius:1rem; background:transparent; }}
.tm-log-header {{ align-items:center; display:flex; flex-wrap:wrap; gap:.7rem; padding:.8rem .95rem; border-bottom:1px solid var(--tm-hairline); }}
</style></head>
<body class="dark">
<div class="shell">
 <div class="page-header" style="margin-bottom:1rem">
  <div>
   <h1 class="page-title" style="margin:0;font-size:1.25rem;font-weight:700;color:#e7eef5">Нейрокомментинг — монитор задач</h1>
   <div class="page-subtitle" style="color:#94a3b8;font-size:.8rem;margin-top:.2rem">Task #2181 • запущен 16:31 • Basic план • alex_smirnov</div>
  </div>
 </div>
 <div class="tm-root">
  <aside class="tm-sidebar">
   <div class="tm-sidebar-head">
    <h2 class="tm-sidebar-title">Задачи</h2>
    <span class="tm-head-n">3</span>
    <span class="tm-live-dot"></span>
   </div>
   <div class="tm-pills">
    <button class="tm-pill active">Все <span class="tm-seg-count">3</span></button>
    <button class="tm-pill">Активные <span class="tm-seg-count">2</span></button>
    <button class="tm-pill">Ошибки <span class="tm-seg-count">0</span></button>
   </div>
   <div class="tm-list">
    {cards}
   </div>
  </aside>
  <main class="tm-cockpit">
   <div class="tm-task-head">
    <h1 class="tm-task-module"><span class="tm-dot live"></span>Нейрокомментинг</h1>
    <span class="tm-task-meta">#2181 · 30 акк · 76 каналов · сбалансированный</span>
    <div class="tm-head-stats">
     <div class="tm-hs-cell"><span class="tm-hs-k">логов</span><div class="tm-hs-v">72</div></div>
     <div class="tm-hs-cell"><span class="tm-hs-k">в работе</span><div class="tm-hs-v">65</div></div>
     <div class="tm-hs-cell"><span class="tm-hs-k">завершено</span><div class="tm-hs-v ok">7</div></div>
     <div class="tm-hs-cell"><span class="tm-hs-k">ошибки</span><div class="tm-hs-v err">0</div></div>
    </div>
   </div>
   <section class="tm-log-wrap">
    <div class="tm-log-header">
     <span class="tm-log-title">Журнал событий <span class="tm-live-dot"></span></span>
     <div class="tm-log-search"><i class="pi pi-search"></i><input placeholder="Поиск логов…"></div>
     <div class="tm-log-lvl">
      <button class="tm-log-btn active">Все</button>
      <button class="tm-log-btn">INFO</button>
      <button class="tm-log-btn warn">WARN</button>
      <button class="tm-log-btn err">ERR</button>
     </div>
     <div class="tm-log-actions"><button class="tm-log-btn">⭳ Export</button><button class="tm-log-btn">⏸ Пауза</button></div>
    </div>
    <div class="tm-log-feed">
     {rows}
    </div>
   </section>
  </main>
 </div>
</div>
</body></html>"""
    open(out, "w", encoding="utf-8").write(html)
    print(f"written: {out} ({len(html.encode('utf-8'))} bytes)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "examples/panel_replica4.html")
