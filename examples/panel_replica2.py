# -*- coding: utf-8 -*-
"""panel_replica2.py — GramGPT panel replica rebuilt from REAL dashboard screenshots.

Design system extracted from live panel (user-provided screens):
  base #0D1117, card #1E293B, border #334155, accent #38BDF8,
  green #10B981, red #DC2626, amber #F59E0B, grey #94A3B8/#64748B.
Pages: 1) Нейрокомментинг log console (verbatim log lines from live screen)
       2) Прогрев аккаунтов settings (activity window + intensity presets)
Run: python panel_replica2.py out.html
"""
import sys
from pathlib import Path

# verbatim log lines from the live dashboard screenshot
LOGS = [
    ("16:31:56", "", "", "", "", "Запуск модуля Нейрокомментинг"),
    ("16:32:47", "", "", "", "", "Аккаунтов: 30, распределённый режим"),
    ("16:33:38", "", "", "", "", "ИИ Защита включена • Уровень: сбалансированный"),
    ("16:34:28", "rocket", "", "", "", "Мониторинг запущен (аккаунты: 30, каналов: 76)"),
    ("16:35:19", "av", "L", "#8B5CF6", "T2", "Lena Pratama • +639668749682 Подключено за 1.6с"),
    ("16:36:10", "av", "L", "#8B5CF6", "T2", "Lena Pratama • +639668749682 Поток: мониторинг 8 каналов"),
    ("16:37:01", "av", "G", "#EC4899", "T5", "Grace Torres • +6286801543494 Подключено за 2.3с"),
    ("16:37:51", "av", "L", "#8B5CF6", "T2", "Lena Pratama • +639668749682 Новый пост в «Крипто Инсайды»"),
    ("16:38:42", "av", "G", "#EC4899", "T5", "Grace Torres • +6286801543494 Поток: мониторинг 8 каналов"),
    ("16:39:33", "av", "G", "#EC4899", "T5", "Grace Torres • +639668749682 Новый пост в «Маркетинг за кофе»"),
    ("16:40:23", "av", "G", "#EC4899", "T5", "Grace Torres • +6286801543494 ✅ Post в «Маркетинг за кофе» принят в работу (вероятность 70)"),
    ("16:41:14", "av", "J", "#06B6D4", "T7", "Juan Smith • +918883383974 Подключено за 2.4с"),
    ("16:42:05", "av", "G", "#EC4899", "T5", "Grace Torres • +6286801543494 Генерация текста через ИИ"),
    ("16:42:56", "av", "J", "#06B6D4", "T7", "Juan Smith • +918883383974 Поток: мониторинг 8 каналов"),
    ("16:43:46", "av", "D", "#F59E0B", "T9", "Dewi López • +6285157508936 Подключено за 1.8с"),
    ("16:44:37", "av", "D", "#F59E0B", "T9", "Dewi López • +6285157508936 Поток: мониторинг 8 каналов"),
    ("16:45:28", "av", "L", "#8B5CF6", "T2", "Lena Pratama • +639668749682 ✅ Post в «Крипто Инсайды» принят в работу (вероятность 70)"),
    ("16:46:18", "av", "L", "#8B5CF6", "T2", "Lena Pratama • +639668749682 Генерация текста через ИИ"),
    ("16:47:09", "av", "L", "#8B5CF6", "T2", "Lena Pratama • +639668749682 ИИ Защита • Симуляция набора текста (164 символа)"),
    ("16:48:00", "av", "J", "#06B6D4", "T7", "Juan Smith • +918883383974 Новый пост в «Бизнес без воды»"),
    ("16:48:50", "av", "M", "#84CC16", "T8", "Mia • +919869788134 Подключено за 1.2с"),
    ("16:49:41", "av", "Н", "#EF4444", "T4", "Никита Беляев • +380968287397 Подключено за 2.3с"),
]

SIDEBAR_HOME = ["Менеджер аккаунтов", "Маркетплейс", "Задачи", "Моя статистика", "Поддержка"]
SIDEBAR_MODULES = ["Нейрокомментинг", "Нейрочаттинг", "Масс Реакции", "Масслукинг", "ЛС-Рассылки",
                   "Чат-Рассылки", "Масстегинг", "Инвайтер", "НейроШиллинг", "Прогрев аккаунтов",
                   "НейроДиалоги", "Pipeline Orchestrator", "GGR Проверка"]


def log_row(ts, icon, initial, avcol, tag, msg):
    ic = ""
    if icon == "av":
        ic = f'<span class="av" style="background:{avcol}">{initial}</span>'
    elif icon == "rocket":
        ic = '<span class="ico">🚀</span>'
    else:
        ic = '<span class="ico dot"></span>'
    tg = f'<span class="tag">{tag}</span>' if tag else ""
    ok = "✅" in msg
    m = msg.replace("✅", '<span class="ok">✅</span>')
    return f'<div class="row{" okrow" if ok else ""}"><span class="ts">{ts}</span>{ic}{tg}<span class="msg">{m}</span></div>'


def html():
    rows = "\n".join(log_row(*l) for l in LOGS)
    side_home = "".join(f'<div class="mi">{m}</div>' for m in SIDEBAR_HOME)
    mods = ""
    for m in SIDEBAR_MODULES:
        act = ' active' if m == "Нейрокомментинг" else ""
        badge = ""
        if m == "Маркетплейс":
            badge = '<span class="nb">Новое</span>'
        mods += f'<div class="mi{act}">{m}{badge}</div>'
    tabs = "".join(f'<span class="tab{" on" if t == "ВСЕ" else ""}">{t}</span>'
                   for t in ["ВСЕ"] + [f"T{i}" for i in range(1, 11)])
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',Inter,Arial,sans-serif}}
body{{background:#0D1117;color:#E2E8F0;width:1360px}}
.wrap{{display:flex;min-height:100vh}}
.side{{width:240px;background:#0D1117;border-right:1px solid #1E293B;padding:14px 10px;display:flex;flex-direction:column}}
.logo{{font-weight:800;font-size:20px;color:#fff;letter-spacing:.5px;padding:4px 10px}}
.plan{{color:#64748B;font-size:11px;padding:2px 10px 14px}}
.sec{{color:#64748B;font-size:10px;letter-spacing:1.4px;padding:12px 10px 6px;font-weight:700}}
.mi{{color:#CBD5E1;font-size:13px;padding:8px 10px;border-radius:6px;border-left:4px solid transparent;position:relative}}
.mi.active{{background:#1E293B;border-left:4px solid #38BDF8;color:#fff;font-weight:700}}
.nb{{background:#38BDF8;color:#fff;font-size:9px;border-radius:8px;padding:1px 6px;margin-left:6px;font-weight:700}}
.userbox{{margin-top:auto;border-top:1px solid #1E293B;padding-top:12px;display:flex;gap:8px;align-items:center}}
.uav{{width:32px;height:32px;border-radius:50%;background:#38BDF8;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700}}
.uname{{color:#fff;font-size:13px;font-weight:600}}
.uplan{{color:#64748B;font-size:11px}}
.renew{{margin-top:8px;background:#38BDF8;color:#fff;border:0;border-radius:6px;padding:5px 12px;font-size:12px;font-weight:700;width:100%}}
.main{{flex:1;display:flex;flex-direction:column}}
.top{{height:56px;background:#0D1117;border-bottom:1px solid #1E293B;display:flex;align-items:center;padding:0 18px;gap:14px}}
.burger{{color:#fff;font-size:20px}}
.title{{flex:1;text-align:center;color:#fff;font-size:19px;font-weight:700}}
.bal{{color:#fff;font-weight:700;font-size:14px}}
.quota{{color:#94A3B8;font-size:13px}}
.circ{{width:30px;height:30px;border-radius:50%;background:#1E293B;display:flex;align-items:center;justify-content:center;font-size:14px}}
.ru{{color:#fff;font-size:13px}}
.cont{{padding:16px 20px}}
.tabstrip{{display:flex;gap:8px;margin-bottom:12px;align-items:center}}
.tab{{background:#1E293B;color:#94A3B8;font-size:11px;font-weight:700;letter-spacing:.5px;padding:5px 12px;border-radius:6px}}
.tab.on{{background:#0D1117;color:#fff;border-bottom:2px solid #38BDF8}}
.pills{{display:flex;gap:8px;margin-bottom:10px;align-items:center}}
.pill{{font-size:11px;font-weight:800;color:#fff;border-radius:6px;padding:4px 12px;letter-spacing:.5px}}
.pill.all{{background:#38BDF8}} .pill.work{{background:#DC2626}} .pill.ok{{background:#10B981}}
.search{{margin-left:auto;background:#1E293B;border:0;border-radius:6px;color:#94A3B8;font-size:12px;padding:7px 12px;width:240px}}
.logs{{background:#0D1117;border:1px solid #1E293B;border-radius:8px;padding:6px 0}}
.row{{display:flex;align-items:center;gap:10px;padding:5px 14px;height:32px}}
.row.okrow{{background:rgba(16,185,129,.06)}}
.ts{{color:#94A3B8;font-family:Consolas,monospace;font-size:12px;width:62px}}
.av{{width:22px;height:22px;border-radius:50%;color:#fff;font-size:10px;font-weight:800;display:flex;align-items:center;justify-content:center;flex:none}}
.ico{{width:22px;text-align:center;font-size:12px;flex:none}}
.dot{{color:#64748B}}
.tag{{background:#1E293B;border:1px solid #334155;border-radius:4px;color:#94A3B8;font-size:10px;padding:1px 6px;flex:none}}
.msg{{color:#fff;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.msg .ok{{margin-right:4px}}
h2.pg{{color:#fff;font-size:17px;margin:26px 0 12px}}
.wgrid{{display:flex;gap:16px}}
.card{{background:#0D1117;border:1px solid #1E293B;border-radius:10px;padding:18px}}
.card h3{{color:#fff;font-size:14px;margin-bottom:14px}}
.wrow{{display:flex;align-items:center;gap:12px;margin-bottom:12px;color:#CBD5E1;font-size:13px}}
.tinp{{background:#1E293B;border:1px solid #334155;border-radius:6px;color:#fff;padding:6px 12px;font-size:13px}}
.open{{color:#10B981;font-weight:700;font-size:12px}}
.presets{{display:flex;flex-direction:column;gap:10px}}
.preset{{background:#1E293B;border:1px solid #334155;border-radius:8px;padding:12px 14px}}
.preset.sel{{border-color:#38BDF8;background:rgba(56,189,248,.08)}}
.preset b{{color:#fff;font-size:13px}} .preset span{{color:#64748B;font-size:11px;display:block;margin-top:2px}}
.tog{{display:flex;align-items:center;gap:8px;color:#CBD5E1;font-size:12px;margin-top:12px}}
.sw{{width:34px;height:18px;border-radius:9px;background:#38BDF8;position:relative}}
.sw::after{{content:'';position:absolute;right:2px;top:2px;width:14px;height:14px;border-radius:50%;background:#fff}}
.foot{{color:#475569;font-size:10px;padding:10px 20px;border-top:1px solid #1E293B;margin-top:20px}}
</style></head><body><div class="wrap">
<div class="side">
 <div class="logo">GRAMGPT</div><div class="plan">План: Базовая</div>
 <div class="sec">ГЛАВНАЯ</div>{side_home}
 <div class="sec">МОДУЛИ</div>{mods}
 <div class="userbox"><div class="uav">A</div><div><div class="uname">alex_smirnov</div><div class="uplan">План: Базовая</div>
 <button class="renew">📈 Продлить</button></div></div>
</div>
<div class="main">
 <div class="top"><span class="burger">≡</span><span class="title">Нейрокомментинг</span>
  <span class="bal">$1284.50</span><span class="quota">0 / 1000 ⚙</span>
  <span class="circ">⭐</span><span class="circ">🌙</span><span class="ru">RU ▾</span><span class="ru">alex_smirnov ▾</span></div>
 <div class="cont">
  <div class="tabstrip">{tabs}<span class="tab">1–10 ▾</span></div>
  <div class="pills"><span class="pill all">ВСЕ 72</span><span class="pill work">В РАБОТЕ 65</span><span class="pill ok">УСПЕХ 7</span>
   <input class="search" placeholder="🔍 Поиск логов..."></div>
  <div class="logs">{rows}</div>
  <h2 class="pg">Прогрев аккаунтов</h2>
  <div class="wgrid">
   <div class="card" style="flex:1"><h3>Активность</h3>
    <div class="wrow">Окно активности: <span class="tinp">9:00</span> — <span class="tinp">24:00</span> <b style="color:#fff">(15ч)</b></div>
    <div class="wrow">Текущее время: <b style="color:#fff">21:31</b> <span class="open">● окно открыто</span></div>
    <div class="wrow">Часовой пояс: <span class="tinp">Москва (UTC+3) ▾</span></div>
   </div>
   <div class="card" style="flex:1"><h3>Интенсивность прогрева</h3>
    <div class="presets">
     <div class="preset sel"><b>● Осторожный</b><span>для новых аккаунтов, 0–7 дней</span></div>
     <div class="preset"><b>○ Нормальный</b><span>для прогретых аккаунтов, 7–30 дней</span></div>
     <div class="preset"><b>○ Агрессивный</b><span>для старых аккаунтов, &gt;30 дней</span></div>
    </div>
    <div class="tog"><span class="sw"></span> Автоадаптация по стадии аккаунта</div>
   </div>
  </div>
 </div>
 <div class="foot">replica rebuilt from real GramGPT panel screenshots • layout/colors/log strings per live screen • data: alex_smirnov demo account</div>
</div></div></body></html>"""


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/panel_replica2.html")
    out.write_text(html(), encoding="utf-8")
    print(f"written: {out} ({out.stat().st_size} bytes)")
