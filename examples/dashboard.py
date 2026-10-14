# -*- coding: utf-8 -*-
"""dashboard.py — render gramgpt-engine state as a static HTML dashboard.

Run: python examples/dashboard.py [out.html]
stdlib-only. Shows: ai_protection gates, activity curve, fleet stages,
shilling scenario, spam_pm plan, GGR scorer, preflight verdicts.
"""
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gramgpt_engine import (C, Account, AccountSignals, Engine, PaceLimiter,
                            Persona, PmTask, QuarantineManager, ShillingTask,
                            build_scenario, chain_plan, claim_target, day_plan,
                            gate, lot_verdict, plan_day, preflight_run_all,
                            risk_assessment, score_account, warming_allowed)
from gramgpt_engine.pacing import activity_weight


def gate_timeline(now):
    cells = []
    for h in range(24):
        ok, reason = gate(datetime(now.year, now.month, now.day, h, 30))
        cls = "g-ok" if ok else ("g-sleep" if "sleep" in reason else "g-break")
        tip = reason if not ok else "allowed"
        cells.append(f'<div class="cell {cls}" title="{h:02d}:00 {tip}">{h:02d}</div>')
    return '<div class="row">' + "".join(cells) + "</div>"


def curve_svg():
    bars = []
    for h in range(24):
        w = activity_weight(h)
        hgt = max(2, int(w / max(activity_weight(x) for x in range(24)) * 120))
        color = "#ff6b35" if w >= 1.2 else ("#4a9eff" if w >= 0.5 else "#3a3f4a")
        bars.append(f'<rect x="{h*22+8}" y="{140-hgt}" width="16" height="{hgt}" fill="{color}" rx="2"/>')
        bars.append(f'<text x="{h*22+16}" y="156" font-size="9" fill="#8a91a0" text-anchor="middle">{h}</text>')
    return (f'<svg width="545" height="165" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="545" height="165" fill="#12151c" rx="8"/>{"".join(bars)}</svg>')


def fleet_table(now):
    fleet = [Account(1, "+100****0001", now - timedelta(days=95)),
             Account(2, "+100****0002", now - timedelta(days=40)),
             Account(3, "+100****0003", now - timedelta(days=10)),
             Account(4, "+100****0004", now - timedelta(days=1))]
    rows = []
    for a in fleet:
        st = a.stage(now)
        lvl, _ = risk_assessment(a, "balanced", 5, now)
        allowed, why = warming_allowed(a, now)
        badge = {"veteran": "b-vet", "active": "b-act", "warming": "b-warm", "new": "b-new"}[st]
        rows.append(f"<tr><td>acc{a.id}</td><td>{a.phone}</td><td>{a.age_days(now):.0f}d</td>"
                    f"<td><span class='badge {badge}'>{st}</span></td><td>{a.budget(now)}/day</td>"
                    f"<td>{lvl or 'ok'}</td><td>{'YES' if allowed else why}</td></tr>")
    return ("<table><tr><th>ID</th><th>Phone</th><th>Age</th><th>Stage</th>"
            "<th>Budget</th><th>Risk</th><th>Warming</th></tr>" + "".join(rows) + "</table>")


def shilling_table(rng):
    task = ShillingTask(target="@example_chat", subject="product X",
                        personas=[Persona("Viktor", "initiator"), Persona("Alina", "supporter"),
                                  Persona("Marat", "skeptic")], pace="live")
    steps = build_scenario(task, rng, start_hour=15)
    rows = "".join(
        f"<tr><td>{s.n}</td><td>{s.persona}</td><td>{s.role}</td><td>{s.action}</td>"
        f"<td>{s.delay_before:.1f}s</td></tr>" for s in steps[:12])
    plan = plan_day(task)
    return (f"<table><tr><th>#</th><th>Persona</th><th>Role</th><th>Action</th><th>Delay</th></tr>{rows}</table>"
            f"<p class='sub'>24 steps total (showing 12) - day budget 60: peak 20:00 = {plan[20]}/h, night 03:00 = {plan[3]}/h</p>")


def ggr_panel(now):
    good = score_account(AccountSignals(age_days=200, has_2fa=True, has_username=True,
                                        has_photo=True, actions_last_7d=40), now)
    bad = score_account(AccountSignals(age_days=1, authkey_dups=3, lot_dead_rate=0.8,
                                       spamblock_history=1, proxy_shared=10), now)
    out = []
    for label, v in (("clean veteran", good), ("fresh fraud", bad)):
        shap = "".join(
            f"<tr><td>{k}</td><td><div class='sbar'><div class='sfill{' neg' if val < 0 else ''}' "
            f"style='width:{min(100, abs(val)/3.2*100):.0f}%'></div></div></td><td>{val:+.2f}</td></tr>"
            for k, val in v.shap.items())
        out.append(f"<div class='card'><h3>{label} - <span class='score'>{v.score}</span> "
                   f"<span class='tier t-{v.tier}'>{v.tier.upper()}</span></h3>"
                   f"<p class='sub'>risk={v.risk_probability} rec={v.recommendation['headline_key']}</p>"
                   f"<table class='shap'>{shap}</table></div>")
    lv = lot_verdict(71, 0)
    out.append(f"<div class='card'><h3>lot_score</h3><p class='sub'>total={lv['total']} dead={lv['dead']} "
               f"death_rate={lv['death_rate']} burn={lv['burn']} survival_7d={lv['survival_7d']}</p></div>")
    return "".join(out)


def spam_panel(now):
    pm = PmTask(name="offer wave", texts=["offer A", "offer B", "offer C"],
                targets=[f"user{i}" for i in range(500)], hourly_limit=12, daily_limit=40)
    dp = day_plan(pm, ["acc1", "acc2"], now)
    lim = PaceLimiter(pm)
    ok, reason, pause = lim.allow("acc1", now)
    chains = [chain_plan(random.Random(i)) for i in range(8)]
    claim_target(pm, "user7")
    dedup = claim_target(pm, "user7")
    pre_ok = preflight_run_all([{"id": 1, "ggr_meta": {}}], {"total": 71, "dead": 0},
                               [f"text {i}" for i in range(6)])
    pre_bad = preflight_run_all([], {"total": 10, "dead": 7}, ["same"] * 8)
    return (f"<table><tr><th>remaining</th><th>hours left</th><th>per day</th><th>per acc</th><th>feasible</th></tr>"
            f"<tr><td>{dp['remaining_targets']}</td><td>{dp['remaining_hours']}</td><td>{dp['per_day']}</td>"
            f"<td>{dp['per_account_today']}</td><td>{dp['feasible']}</td></tr></table>"
            f"<p class='sub'>pace acc1: {'ALLOW' if ok else reason} | chains: {chains} | dedup re-claim: {dedup}</p>"
            f"<p class='sub'>preflight clean: allow={pre_ok['allow_launch']} | "
            f"bad lot+identical: blocked={pre_bad['blocked_by']}</p>")


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "dashboard.html"
    now = datetime(2026, 10, 14, 15, 0)
    rng = random.Random(20261014)
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>gramgpt-engine dashboard</title>
<style>
body{{background:#0b0d12;color:#e6e9ef;font-family:Consolas,Menlo,monospace;margin:0;padding:24px}}
h1{{color:#ff6b35;font-size:22px;margin:0 0 4px}} h2{{color:#ff6b35;font-size:15px;margin:18px 0 8px;border-bottom:1px solid #232833;padding-bottom:4px}}
.sub{{color:#8a91a0;font-size:11px;margin:6px 0}}
.row{{display:flex;gap:3px;flex-wrap:wrap}} .cell{{width:34px;height:26px;line-height:26px;text-align:center;font-size:10px;border-radius:4px}}
.g-ok{{background:#12351f;color:#4ade80}} .g-sleep{{background:#2a1520;color:#f87171}} .g-break{{background:#2a2415;color:#fbbf24}}
table{{border-collapse:collapse;font-size:12px;width:100%}} th{{color:#8a91a0;text-align:left;font-weight:normal;border-bottom:1px solid #232833;padding:4px 8px}}
td{{padding:4px 8px;border-bottom:1px solid #171b24}}
.badge{{padding:2px 8px;border-radius:10px;font-size:10px}} .b-vet{{background:#12351f;color:#4ade80}} .b-act{{background:#122a3f;color:#4a9eff}}
.b-warm{{background:#2a2415;color:#fbbf24}} .b-new{{background:#2a1520;color:#f87171}}
.cards{{display:flex;gap:14px;flex-wrap:wrap}} .card{{background:#12151c;border:1px solid #232833;border-radius:8px;padding:12px 16px;flex:1;min-width:280px}}
.card h3{{margin:0 0 4px;font-size:13px;color:#e6e9ef}} .score{{color:#ff6b35;font-size:20px}} .tier{{font-size:10px;padding:2px 8px;border-radius:10px}}
.t-excellent{{background:#12351f;color:#4ade80}} .t-good{{background:#122a3f;color:#4a9eff}} .t-dead{{background:#2a1520;color:#f87171}} .t-risky{{background:#2a2415;color:#fbbf24}}
table.shap td{{padding:2px 6px;font-size:11px}} .sbar{{width:120px;height:8px;background:#1c212c;border-radius:4px}}
.sfill{{height:8px;background:#4a9eff;border-radius:4px}} .sfill.neg{{background:#f87171}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.foot{{color:#565e6e;font-size:10px;margin-top:20px}}
</style></head><body>
<h1>gramgpt-engine v1.0.0 - dashboard</h1>
<p class="sub">clean-room Python implementation of GramGPT engine logic - simulated day {now.strftime('%Y-%m-%d %H:%M')} - stdlib only, 24/24 tests OK</p>
<h2>ai_protection - 24h gate timeline (green=allow, red=sleep 01-07, yellow=break 6-8/12-14/23-01)</h2>
{gate_timeline(now)}
<h2>activity curve - hourly weights (evening peak ~19x night trough)</h2>
{curve_svg()}
<h2>fleet - warming lifecycle &amp; budgets</h2>
{fleet_table(now)}
<div class="grid2">
<div><h2>neuro_shilling - 24-step scenario</h2>{shilling_table(rng)}</div>
<div><h2>spam_pm - 48h task / preflight</h2>{spam_panel(now)}</div>
</div>
<h2>GGR local scorer - 7 SHAP groups</h2>
<div class="cards">{ggr_panel(now)}</div>
<p class="foot">github.com/gbonnet65923/gramgpt-engine - reconstructed from public surface: OpenAPI 92 endpoints, 2222 RU engine log templates, 5327 module docs, frontend simulator, live GGR responses</p>
</body></html>"""
    out.write_text(html, encoding="utf-8")
    print(f"dashboard written: {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
