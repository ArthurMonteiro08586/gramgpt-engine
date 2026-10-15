# -*- coding: utf-8 -*-
"""build_panel_live.py — generate examples/panel_live.html:
Task Monitor UI on their REAL component CSS (task-monitor.BVhk1W4S.css verbatim,
data-v stripped), wired to the clone backend via fetch().

Usage: python examples/build_panel_live.py <css_dir> [out]
  css_dir = folder with downloaded gramgpt panel CSS chunks
"""
import re
import sys
import os

HEAD = """<!doctype html><html lang="ru"><head><meta charset="utf-8">
<title>GramGPT Clone — Live Task Monitor</title>
<style>
:root { color-scheme: dark; }
* { box-sizing: border-box; }
html,body { margin:0; }
body { background: radial-gradient(1100px 480px at 82% -12%, rgba(0,136,204,.10), transparent 60%),
       radial-gradient(840px 420px at 6% -8%, rgba(56,189,248,.07), transparent 58%),
       linear-gradient(180deg,#0a0f1a,#070a12);
       min-height:100vh; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; }
/* ==== VERBATIM: task-monitor.BVhk1W4S.css ==== */
__TM_CSS__
/* ==== VERBATIM: neuro-commenting module page/header ==== */
__NC_CSS__
.shell { max-width:1400px; margin:0 auto; padding:1rem 1.5rem 1.5rem; }
.shell .tm-root { height:860px; border-radius:1rem; background:transparent; }
.tm-log-header { align-items:center; display:flex; flex-wrap:wrap; gap:.7rem; padding:.8rem .95rem; border-bottom:1px solid var(--tm-hairline); }
.tm-toolbar { display:flex; gap:.6rem; align-items:center; margin-bottom:.8rem; }
.tm-toolbar input, .tm-toolbar select { background:#10141d; border:1px solid rgba(96,150,220,.25); color:#e7eef5; border-radius:.5rem; padding:.45rem .7rem; font-size:.8rem; }
.tm-toolbar button { background:#0088cc; color:#fff; border:0; border-radius:.5rem; padding:.5rem 1rem; font-size:.8rem; cursor:pointer; font-weight:600; }
.tm-toolbar button.ghost { background:transparent; border:1px solid rgba(96,150,220,.35); color:#9fb4cf; }
#tokenbox { width:340px; }
.tm-err { color:#f87171; font-size:.75rem; margin-left:.5rem; }
</style></head>
<body class="dark">
<div class="shell">
 <div class="page-header" style="margin-bottom:.8rem">
  <div>
   <h1 class="page-title" style="margin:0;font-size:1.25rem;font-weight:700;color:#e7eef5">Live Task Monitor <span style="font-size:.7rem;color:#38bdf8">clone backend :__PORT__</span></h1>
   <div class="page-subtitle" style="color:#94a3b8;font-size:.8rem;margin-top:.2rem" id="sub">подключение…</div>
  </div>
 </div>
 <div class="tm-toolbar">
  <input id="tokenbox" placeholder="Bearer ggk_live_… (token)">
  <button onclick="connect()">Подключить</button>
  <select id="module"><option>neuro_commenting</option><option>mass_react</option><option>mass_looking</option><option>bulk_join</option><option>group_spammer</option><option>neuro_chatting</option><option>neuro_dialogs</option><option>neuro_shilling</option><option>spam_pm</option><option>check_numbers</option><option>parsing</option><option>warming</option><option>account_op</option></select>
  <button class="ghost" onclick="launch()">▶ Запустить модуль</button>
  <span class="tm-err" id="err"></span>
 </div>
 <div class="tm-root">
  <aside class="tm-sidebar">
   <div class="tm-sidebar-head">
    <h2 class="tm-sidebar-title">Задачи</h2>
    <span class="tm-head-n" id="tn">0</span>
    <span class="tm-live-dot"></span>
   </div>
   <div class="tm-pills">
    <button class="tm-pill active">Все <span class="tm-seg-count" id="cnt-all">0</span></button>
    <button class="tm-pill">Активные <span class="tm-seg-count" id="cnt-run">0</span></button>
    <button class="tm-pill">Ошибки <span class="tm-seg-count" id="cnt-err">0</span></button>
   </div>
   <div class="tm-list" id="tasklist"></div>
  </aside>
  <main class="tm-cockpit">
   <div class="tm-task-head">
    <h1 class="tm-task-module"><span class="tm-dot live" id="hdot"></span><span id="hmod">—</span></h1>
    <span class="tm-task-meta" id="hmeta"></span>
    <div class="tm-head-stats">
     <div class="tm-hs-cell"><span class="tm-hs-k">логов</span><div class="tm-hs-v" id="hs-logs">0</div></div>
     <div class="tm-hs-cell"><span class="tm-hs-k">выполнено</span><div class="tm-hs-v" id="hs-done">0</div></div>
     <div class="tm-hs-cell"><span class="tm-hs-k">всего</span><div class="tm-hs-v" id="hs-total">0</div></div>
     <div class="tm-hs-cell"><span class="tm-hs-k">статус</span><div class="tm-hs-v" id="hs-status">—</div></div>
    </div>
   </div>
   <section class="tm-log-wrap">
    <div class="tm-log-header">
     <span class="tm-log-title">Журнал событий <span class="tm-live-dot"></span></span>
     <div class="tm-log-lvl">
      <button class="tm-log-btn active">Все</button>
      <button class="tm-log-btn">INFO</button>
      <button class="tm-log-btn warn">WARN</button>
      <button class="tm-log-btn err">ERR</button>
     </div>
    </div>
    <div class="tm-log-feed" id="logfeed"></div>
   </section>
  </main>
 </div>
</div>
<script>
let TOK = localStorage.getItem('gg_token') || '';
let SEL = null, AFTER = 0, TIMER = null;
document.getElementById('tokenbox').value = TOK;
const $ = id => document.getElementById(id);
function api(path, opt={}) {
  opt.headers = Object.assign({'Content-Type':'application/json',
    'Authorization':'Bearer '+TOK}, opt.headers||{});
  return fetch(path, opt).then(async r => {
    const j = await r.json().catch(()=>({}));
    if (!r.ok) throw new Error(j.detail ? JSON.stringify(j.detail).slice(0,140) : r.status);
    return j;
  });
}
function connect() {
  TOK = $('tokenbox').value.trim(); localStorage.setItem('gg_token', TOK);
  $('err').textContent = '';
  api('/api/v1/me/').then(me => {
    $('sub').textContent = `${me.username} • план ${me.plan} • баланс $${me.balance} • квота ${me.quota_used}/${me.quota_total}`;
    refreshTasks(true);
    if (TIMER) clearInterval(TIMER);
    TIMER = setInterval(()=>{ refreshTasks(); if (SEL) pullLogs(); }, 1500);
  }).catch(e => $('err').textContent = e.message);
}
function refreshTasks(resetSel) {
  api('/api/v1/tasks/').then(d => {
    $('tn').textContent = d.items.length;
    $('cnt-all').textContent = d.items.length;
    $('cnt-run').textContent = d.items.filter(t=>t.status==='running'||t.status==='waiting').length;
    $('cnt-err').textContent = d.items.filter(t=>t.status==='failed').length;
    $('tasklist').innerHTML = d.items.map(t => {
      const c = t.counters||{};
      const dot = t.status==='running'?'live':(t.status==='failed'||t.status==='cancelled'?'err':'done');
      return `<button class="tm-card${SEL===t.task_id?' selected':''}" onclick="select(${t.task_id})">
        <span class="tm-dot ${dot}"></span>
        <span class="tm-card-time">${new Date(t.created_at*1000).toTimeString().slice(0,5)}</span>
        <span class="tm-card-module"><span class="tm-card-name">${t.module}</span></span>
        <span class="tm-card-stats"><span>${c.done||0} шаг</span><b class="ok">${c.completed||0} готово</b><span>${t.status}</span></span>
        <span class="tm-card-user">#${t.task_id}</span></button>`;
    }).join('') || '<div style="color:#5b6b82;padding:1rem;font-size:.8rem">нет задач — запусти модуль</div>';
    if (resetSel && d.items.length && SEL===null) select(d.items[0].task_id);
    const cur = d.items.find(t=>t.task_id===SEL);
    if (cur) {
      const c = cur.counters||{};
      $('hmod').textContent = cur.module;
      $('hmeta').textContent = `#${cur.task_id} • ${(cur.payload.account_ids||[]).length} акк`;
      $('hdot').className = 'tm-dot ' + (cur.status==='running'?'live':(cur.status==='failed'?'err':'done'));
      $('hs-done').textContent = c.completed||0;
      $('hs-total').textContent = c.total||0;
      $('hs-status').textContent = cur.status;
      $('hs-status').className = 'tm-hs-v ' + (cur.status==='completed'?'ok':(cur.status==='failed'?'err':''));
    }
  }).catch(e=>$('err').textContent=e.message);
}
function select(id) { SEL = id; AFTER = 0; $('logfeed').innerHTML=''; $('hs-logs').textContent=0; pullLogs(); refreshTasks(); }
function pullLogs() {
  if (!SEL) return;
  api(`/api/v1/tasks/${SEL}/logs/?after_id=${AFTER}&limit=200`).then(d => {
    if (!d.items.length) return;
    AFTER = d.items[d.items.length-1].id;
    const feed = $('logfeed');
    for (const l of d.items) {
      const t = new Date(l.ts*1000).toTimeString().slice(0,8);
      const div = document.createElement('div');
      div.className = 'tm-log-row'; div.dataset.level = l.level;
      div.innerHTML = `<span class="tm-log-time">${t}</span>
        <button class="tm-log-acc">${l.account||'SYS'}</button>
        ${l.badge?`<span class="tm-log-badge">${l.badge}</span>`:'<span></span>'}
        <span class="tm-log-msg"></span>`;
      div.querySelector('.tm-log-msg').textContent = l.message;
      feed.appendChild(div);
    }
    $('hs-logs').textContent = parseInt($('hs-logs').textContent||0) + d.items.length;
    feed.scrollTop = feed.scrollHeight;
  }).catch(()=>{});
}
async function launch() {
  const mod = $('module').value;
  try {
    const acc = await api('/api/v1/accounts/?page_size=200');
    const ids = acc.items.filter(a=>a.status==='active').slice(0,30).map(a=>a.id);
    if (!ids.length) throw new Error('нет свободных аккаунтов');
    const payload = {account_ids: ids, dry_run: false, skip_unavailable: true, queue_if_busy: true};
    if (['mass_react','mass_looking','neuro_chatting','group_spammer','bulk_join'].includes(mod)) {
      payload.channels = ['@crypto_insights','@ai_news_ru'];
      if (mod==='mass_react') payload.reactions = ['👍','🔥'];
      if (mod==='group_spammer') payload.chain = [{text:'привет!'}, {text:'кто тут?'}];
    }
    if (mod==='check_numbers') payload.numbers = ['+380971234567','+380991112233'];
    if (mod==='parsing') { payload.kind='channels'; payload.mode='search'; payload.query='ai'; payload.results_limit=50; }
    const r = await api(`/api/v1/tools/launch_${mod}/`, {method:'POST', body: JSON.stringify(payload)});
    $('err').textContent=''; select(r.task_id); refreshTasks();
  } catch(e) { $('err').textContent = e.message; }
}
if (TOK) connect();
</script>
</body></html>
"""


def load_unscoped(path, keep=None):
    t = open(path, encoding="utf-8", errors="ignore").read()
    t = re.sub(r"\[data-v-[0-9a-fA-F]+\]", "", t)
    if keep:
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


def main():
    css_dir = sys.argv[1] if len(sys.argv) > 1 else \
        r"C:/Users/User/tmp/rev_targets/gramgpt/panel_css"
    out = sys.argv[2] if len(sys.argv) > 2 else \
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "panel_live.html")
    tm = load_unscoped(os.path.join(css_dir, "task-monitor.BVhk1W4S.css"))
    nc = load_unscoped(os.path.join(css_dir, "neuro-commenting.Bdlz8ued.css"),
                       keep=[".module-page", ".page-header", ".page-title", ".page-subtitle"])
    html = HEAD.replace("__TM_CSS__", tm).replace("__NC_CSS__", nc).replace("__PORT__", "8770")
    open(out, "w", encoding="utf-8").write(html)
    print(f"written {out} ({os.path.getsize(out)} bytes, tm_css={len(tm)}, nc_css={len(nc)})")


if __name__ == "__main__":
    main()
