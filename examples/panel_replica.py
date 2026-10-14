# -*- coding: utf-8 -*-
"""panel_replica.py — replica of the real GramGPT panel UI ("Менеджер аккаунтов").

UI text/structure: 1:1 from gramgpt.io RU locale (panel_locale_ru.json, 70 sections).
Numbers: computed live by gramgpt-engine (clean-room). stdlib only.
Run: python examples/panel_replica.py [out.html]
"""
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gramgpt_engine import (Account, AccountSignals, lot_verdict, risk_assessment,
                            score_account, warming_allowed)

NOW = datetime(2026, 10, 14, 15, 0)
RNG = random.Random(7)

SIDEBAR = [
    ("Главная", [("▦", "Менеджер аккаунтов", True), ("◈", "Маркетплейс", False, ),
                 ("▤", "Задачи", False), ("▧", "Моя статистика", False), ("⛨", "Поддержка", False)]),
    ("Модули", [("💬", "Нейрокомментинг", False), ("🗨", "Нейрочаттинг", False),
                ("👍", "Масс Реакции", False), ("👁", "Масслукинг", False),
                ("➦", "ЛС-Рассылки", False), ("👥", "Чат-Рассылки", False),
                ("#", "Масстегинг", False), ("＋", "Инвайтер", False),
                ("🚀", "НейроШиллинг", False), ("🔥", "Прогрев аккаунтов", False),
                ("🗪", "НейроДиалоги", False), ("⚙", "Pipeline Orchestrator", False),
                ("★", "GGR Проверка", False)]),
]

STAT_TAGS = [  # (title, tooltip) — verbatim from main_dashboard.stats.tags
    ("Активные", "Валидные аккаунты, готовые к запуску в модулях", 2326, "ok"),
    ("В работе", "Аккаунты, прямо сейчас занятые в активных задачах", 184, "work"),
    ("Забаненные", "Аккаунты с постоянным баном Telegram", 37, "bad"),
    ("Невалидные", "Аккаунты с ошибкой авторизации или недоступной сессией", 12, "bad"),
    ("Мут", "Аккаунты в состоянии мьюта", 8, "warn"),
    ("Спамблок", "Временный или постоянный спамблок от Telegram", 21, "bad"),
    ("Замороженные", "Аккаунты, замороженные платформой", 5, "warn"),
    ("На карантине", "Аккаунты в локальном карантине после рискованных действий", 3, "warn"),
    ("Реавторизация", "Аккаунты, которым требуется повторный вход", 6, "warn"),
]

BULK_BTNS = ["Назначить прокси", "Проверка прокси", "Проверка спамблока",
             "GGR проверка выбранных", "Установка 2FA", "ИИ профили",
             "Сброс сессий", "Настройка приватности", "Экспорт"]

COUNTRIES = ["ID", "VN", "PH", "IN", "BR", "NG", "PL", "TR"]


def fleet_rows():
    rows = []
    for i in range(1, 11):
        age = RNG.choice([1, 3, 9, 17, 30, 64, 120, 210])
        acc = Account(i, f"+{RNG.randint(100,199)}****{RNG.randint(1000,9999)}",
                      NOW - timedelta(days=age))
        sig = AccountSignals(age_days=age, has_2fa=RNG.random() < 0.6,
                             has_username=RNG.random() < 0.8, has_photo=RNG.random() < 0.7,
                             actions_last_7d=RNG.randint(0, 60),
                             authkey_dups=RNG.choice([0, 0, 0, 2]),
                             proxy_shared=RNG.choice([0, 1, 6]))
        v = score_account(sig, NOW)
        st = acc.stage(NOW)
        allowed, why = warming_allowed(acc, NOW)
        status = "Активен" if st in ("active", "trusted", "veteran") else (
            "Прогрев" if allowed else why.title())
        scls = "s-ok" if status == "Активен" else ("s-warn" if status == "Прогрев" else "s-bad")
        rows.append(
            f"<tr><td>{acc.phone}</td><td>{RNG.choice(COUNTRIES)}</td><td>{age} дн назад</td>"
            f"<td class='mono'>socks5://…{RNG.randint(1000,9999)}</td>"
            f"<td><span class='st {scls}'>{status}</span></td>"
            f"<td>{'вкл' if sig.has_2fa else 'выкл'}</td>"
            f"<td><b class='ggr'>{v.score}</b> <span class='tier t-{v.tier}'>{v.tier.upper()}</span></td>"
            f"<td>{round(v.meta['cohort_survival']['survival_7d'] * 100)}% · 7 дн</td>"
            f"<td>${RNG.uniform(0.3, 1.2):.2f}</td></tr>")
    return "".join(rows)


def ggr_card():
    sig = AccountSignals(age_days=14, authkey_dups=2, lot_dead_rate=0.11,
                         proxy_shared=3, has_2fa=False)
    v = score_account(sig, NOW)
    lv = lot_verdict(71, 0)
    pct = round(v.meta["cohort_survival"]["survival_7d"] * 100)
    shap = "".join(
        f"<tr><td>{k}</td><td><div class='sbar'><i style='width:{min(100, abs(val)/4*100):.0f}%"
        f"{' ;background:#dc2626' if val < 0 else ''}'></i></div></td><td>{val:+.2f}</td></tr>"
        for k, val in v.shap.items())
    return f"""<div class="card ggr">
<h3>GGR — GramGPT Rating <span class="beta">БЕТА</span></h3>
<div class="ggr-flex"><div class="bigscore">{v.score}<span class="tier t-{v.tier}">{v.tier.upper()}</span></div>
<div><div class="glabel">Рейтинг · <span title="Шанс, что аккаунт проживёт ближайшие 7 дней, ×10">Доживут неделю</span></div>
<div class="gcaption">≈{pct}% таких аккаунтов доживают неделю</div>
<div class="glabel">Потенциал · {pct}% · горизонт 7 дн</div>
<div class="gcaption">Эта партия ({lv['total']} акк.): смертей пока нет · burn={lv['burn']}</div>
<div class="glabel">Почему такой балл</div>
<div class="gcaption">Telegram морозит партиями: балл собран из того, что случилось с вашими партиями.</div></div></div>
<table class="shap"><tr><th>фактор (SHAP)</th><th></th><th>вклад</th></tr>{shap}</table>
<p class="foot-note">модель: engine local-clone · авто-2026-10-13 · n когорты 6505</p></div>"""


def sidebar_html():
    out = ['<div class="logo">⚡ <b>GramGPT</b><span class="ver">панель</span></div>']
    for title, items in SIDEBAR:
        out.append(f'<div class="grp">{title}</div>')
        for it in items:
            icon, name = it[0], it[1]
            active = " active" if name == "Менеджер аккаунтов" else ""
            new = ' <span class="newpill">Новое</span>' if name == "Маркетплейс" else ""
            out.append(f'<div class="mi{active}"><span class="ic">{icon}</span>{name}{new}</div>')
    return "".join(out)


def main():
    outp = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "panel_replica.html"
    tags = "".join(
        f'<div class="tag {cls}" title="{tip}"><b>{n}</b><span>{title}</span></div>'
        for title, tip, n, cls in STAT_TAGS)
    btns = "".join(f'<button>{b}</button>' for b in BULK_BTNS)
    html = f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<title>GramGPT - Менеджер аккаунтов</title><style>
*{{box-sizing:border-box;margin:0}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#fafaf9;color:#1c1917;font-size:13px}}
.wrap{{display:flex;min-height:100vh}}
.side{{width:224px;background:#fff;border-right:1px solid #e7e5e4;padding:14px 10px;flex-shrink:0}}
.logo{{font-size:17px;padding:4px 8px 14px}} .logo b{{color:#0088cc}} .ver{{color:#a8a29e;font-size:10px;margin-left:6px}}
.grp{{color:#a8a29e;font-size:10px;text-transform:uppercase;letter-spacing:.08em;margin:12px 8px 6px}}
.mi{{padding:7px 9px;border-radius:8px;color:#44403c;cursor:default;display:flex;align-items:center;gap:8px}}
.mi .ic{{width:18px;text-align:center;opacity:.75}}
.mi.active{{background:#eaf1fa;color:#0088cc;font-weight:600}}
.newpill{{background:#dcfce7;color:#16a34a;font-size:9px;padding:1px 6px;border-radius:8px;margin-left:auto}}
.main{{flex:1;padding:18px 22px;min-width:0}}
.head{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px}}
.head h1{{font-size:19px}} .head .sub{{color:#78716c;font-size:12px;margin-top:2px}}
.umenu{{display:flex;gap:8px;align-items:center;color:#57534e}}
.umenu .ava{{width:30px;height:30px;border-radius:50%;background:#0088cc;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700}}
.tags{{display:grid;grid-template-columns:repeat(9,1fr);gap:8px;margin-bottom:14px}}
.tag{{background:#fff;border:1px solid #e7e5e4;border-radius:10px;padding:9px 10px;display:flex;flex-direction:column;gap:2px}}
.tag b{{font-size:17px}} .tag span{{color:#78716c;font-size:10.5px}}
.tag.ok b{{color:#16a34a}} .tag.work b{{color:#0088cc}} .tag.warn b{{color:#d97706}} .tag.bad b{{color:#dc2626}}
.toolbar{{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}}
.toolbar button{{background:#fff;border:1px solid #e7e5e4;border-radius:8px;padding:6px 11px;font-size:11.5px;color:#44403c;cursor:default}}
.toolbar button:hover{{border-color:#0088cc;color:#0088cc}}
.cols{{display:grid;grid-template-columns:1fr 380px;gap:14px;align-items:start}}
.card{{background:#fff;border:1px solid #e7e5e4;border-radius:12px;padding:14px}}
.card h2{{font-size:14px;margin-bottom:10px}} .card h3{{font-size:14px;margin-bottom:10px}}
.beta{{background:#fef3c7;color:#b45309;font-size:9px;padding:2px 7px;border-radius:8px;vertical-align:middle}}
table{{border-collapse:collapse;width:100%;font-size:11.5px}}
th{{color:#a8a29e;text-align:left;font-weight:500;padding:5px 8px;border-bottom:1px solid #e7e5e4;font-size:10.5px}}
td{{padding:6px 8px;border-bottom:1px solid #f5f5f4}}
.mono{{font-family:Consolas,monospace;font-size:10.5px;color:#57534e}}
.st{{padding:2px 8px;border-radius:9px;font-size:10px}}
.s-ok{{background:#dcfce7;color:#16a34a}} .s-warn{{background:#fef3c7;color:#b45309}} .s-bad{{background:#fee2e2;color:#dc2626}}
.tier{{font-size:9px;padding:2px 7px;border-radius:8px;margin-left:5px}}
.t-excellent{{background:#dcfce7;color:#16a34a}} .t-good{{background:#eaf1fa;color:#0088cc}}
.t-risky{{background:#fef3c7;color:#b45309}} .t-dead{{background:#fee2e2;color:#dc2626}}
.ggr .ggr-flex{{display:flex;gap:16px;align-items:center;margin-bottom:10px}}
.bigscore{{font-size:42px;font-weight:800;color:#0088cc}}
.glabel{{font-weight:600;font-size:12px;margin-top:6px}} .gcaption{{color:#78716c;font-size:11px}}
.shap td{{padding:3px 6px}} .sbar{{width:130px;height:7px;background:#f5f5f4;border-radius:4px}}
.sbar i{{display:block;height:7px;background:#0088cc;border-radius:4px}}
.foot-note{{color:#a8a29e;font-size:10px;margin-top:8px}}
.ggrnum{{color:#0088cc;font-weight:700}}
</style></head><body><div class="wrap">
<div class="side">{sidebar_html()}</div>
<div class="main">
<div class="head"><div><h1>Менеджер аккаунтов</h1><div class="sub">Управление вашими Telegram аккаунтами</div></div>
<div class="umenu"><span>Мой аккаунт</span><span>·</span><span style="color:#0088cc">Купить подписку</span><div class="ava">R</div></div></div>
<div class="tags">{tags}</div>
<div class="toolbar">{btns}</div>
<div class="cols">
<div class="card"><h2>Аккаунты <span style="color:#a8a29e;font-weight:400">· зарегистрированные · все</span></h2>
<table><tr><th>Аккаунт</th><th>Страна</th><th>Зарегистрирован</th><th>Прокси</th><th>Статус</th><th>С 2FA</th><th>GGR Рейтинг</th><th>Потенциал</th><th>Себестоимость</th></tr>
{fleet_rows()}</table>
<p class="foot-note">Экспорт даёт архив — можно продать (LZT / свои скрипты) или переимпортировать в панель через drag-and-drop.</p></div>
{ggr_card()}
</div></div></div></body></html>"""
    outp.write_text(html, encoding="utf-8")
    print(f"panel replica written: {outp} ({outp.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
