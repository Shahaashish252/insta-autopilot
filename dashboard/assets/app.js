const D = DATA, REPO = D.repo, $ = s => document.querySelector(s), app = $('#app');
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = n => n == null ? '–' : n >= 1e6 ? (n / 1e6).toFixed(1) + 'M' : n >= 1e4 ? (n / 1e3).toFixed(1) + 'K' : Number(n).toLocaleString('en-IN');
const ist = (t, o) => t ? new Date(t).toLocaleString('en-IN', Object.assign({timeZone:'Asia/Kolkata', day:'numeric', month:'short', hour:'numeric', minute:'2-digit'}, o || {})) : '';
const ago = t => { if (!t) return ''; const s = (Date.now() - new Date(t)) / 1000, f = Math.abs(s), fut = s < 0;
  const v = f < 60 ? 'just now' : f < 3600 ? Math.round(f / 60) + ' min' : f < 86400 ? Math.round(f / 3600) + ' h' : Math.round(f / 86400) + ' d';
  return v === 'just now' ? v : fut ? 'in ' + v : v + ' ago'; };
const secs = (a, b) => a ? Math.max(0, ((b ? new Date(b) : new Date()) - new Date(a)) / 1000) : null;
const dur = x => x == null ? '' : x >= 60 ? `${Math.floor(x / 60)} min ${String(Math.round(x % 60)).padStart(2, '0')} s` : `${Math.round(x)} s`;
const raw = p => fetch(`https://api.github.com/repos/${REPO}/contents/${p}${p.includes('?') ? '&' : '?'}t=${Date.now()}`, {headers:{Accept:'application/vnd.github.raw'}, cache:'no-store'});
const reels = D.reels, posted = reels.filter(r => r.status === 'posted'), sched = reels.filter(r => r.status === 'scheduled').sort((a, b) => a.publish_at.localeCompare(b.publish_at));
const sum = k => posted.reduce((a, r) => a + (r.ins[k] || 0), 0);
const scores = reels.map(r => r.hook_score).filter(x => x != null);

// ───────── shell
function shell(inner) {
  const acc = D.account.username, wfBad = D.workflows.some(w => w.last && w.last.conclusion === 'failure'), off = D.workflows.filter(w => w.state !== 'active' && w.name !== 'refresh-token').length;
  const home = document.body.dataset.view === 'home';
  const tab = (h, t) => `<a href="${home ? '' : 'index.html'}${h}">${t}</a>`;
  app.innerHTML = `<div class="top"><div class="wrap"><div class="logo">अ</div><div class="brand"><b>Anek Arthi Studio</b><small>reels made, posted & grown on GitHub</small></div><div class="sp"></div>
    ${acc ? `<a class="chip" href="https://instagram.com/${esc(acc)}" target="_blank" rel="noopener"><span class="dot ok"></span>@${esc(acc)}</a>` : '<span class="chip"><span class="dot warn"></span>not connected</span>'}
    <span class="chip" title="GitHub automation" style="display:var(--hide-sm,inline-flex)"><span class="dot ${wfBad ? 'bad' : off ? 'warn' : 'ok'}"></span>${wfBad ? 'a job failed' : off ? off + ' paused' : 'all systems on'}</span>
    <button class="icon-btn" id="theme" aria-label="Switch light or dark">◐</button></div>
    <div class="wrap"><nav class="tabs">${tab('#overview', 'Overview')}${tab('#reels', 'Reels')}${tab('#schedule', 'Schedule')}${tab('#growth', 'Growth')}${tab('#comments', 'Comments')}${tab('#system', 'Automation')}<a href="making.html" class="${home ? '' : 'on'}">Making ◐</a></nav></div></div>
    <main class="wrap">${inner}</main><footer>Updated ${ist(D.updated)} IST · <a href="https://github.com/${esc(REPO)}" target="_blank" rel="noopener">GitHub repo</a> · refreshes by itself</footer>
    <dialog id="dlg"></dialog>`;
  $('#theme').onclick = () => { const r = document.documentElement, dark = r.dataset.theme ? r.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
    r.dataset.theme = dark ? 'light' : 'dark'; try { localStorage.setItem('theme', r.dataset.theme); } catch (e) {} };
  if (matchMedia('(max-width:600px)').matches) document.documentElement.style.setProperty('--hide-sm', 'none');
}

// ───────── home
function home() {
  const nx = sched[0];
  const kpi = (ic, label, v, s) => `<div class="card kpi fade"><span class="ic">${ic}</span><div class="label">${label}</div><div class="v">${v}</div><div class="s">${s}</div></div>`;
  const views = sum('views'), shares = sum('shares'), saves = sum('saved'), comments = sum('comments');
  const per = (x) => views ? (1000 * x / views).toFixed(0) : '–';
  shell(`
  <div class="hero" id="overview">
    ${nx ? `<div class="card next fade"><button class="cv" data-open="${esc(nx.name)}" aria-label="Watch ${esc(nx.title)}">${nx.cover ? `<img src="${esc(nx.cover)}" alt="">` : ''}</button>
      <div><div class="label">Next post</div><h3>${esc(nx.title)}</h3><div class="when">${ist(nx.publish_at, {weekday:'short'})} IST</div>
      <div class="count" data-count="${esc(nx.publish_at)}"></div><div class="small" style="opacity:.85">${sched.length} scheduled · posts by itself from GitHub</div></div></div>`
      : `<div class="card next fade"><div class="cv"></div><div><div class="label">Next post</div><h3>Nothing scheduled</h3><div class="when">GitHub makes the next reel at 05:00 or 14:00 IST.</div></div></div>`}
    <div class="card make fade" id="now"><div class="label">Making</div><p class="muted">Loading the live progress…</p></div>
  </div>
  <div class="kpis">
    ${kpi('👥', 'Followers', fmt(D.account.followers_count), `${fmt(D.account.media_count)} posts on Instagram`)}
    ${kpi('▶', 'Views', fmt(views), `${posted.length} reels posted`)}
    ${kpi('↗', 'Shares', fmt(shares), `${per(shares)} per 1,000 views`)}
    ${kpi('🔖', 'Saves', fmt(saves), `${per(saves)} per 1,000 views`)}
    ${kpi('💬', 'Comments', fmt(comments), `<span id="kreplied">…</span> answered by Claude`)}
    ${kpi('🎯', 'Hook score', scores.length ? Math.round(scores.reduce((a, b) => a + b) / scores.length) : '–', scores.length ? `avg of ${scores.length} new reels · bar 65` : 'scored from the next reel')}
  </div>

  <section><div class="grid g2">
    <div class="card chart"><div class="sh"><div><h2>Views per reel</h2><p>Each posted reel; the line is the channel median.</p></div></div>${chart()}</div>
    <div class="card"><div class="sh"><div><h2>What people do</h2><p>Per 1,000 views, all posted reels. Shares grow a new channel fastest.</p></div></div>
      <div class="rates">${[['Shares', shares, 120], ['Saves', saves, 60], ['Comments', comments, 60], ['Likes', sum('likes'), 150], ['Follows', sum('follows'), 20]].map(([n, x, top]) =>
        `<div class="rate"><div class="row"><span>${n}</span><b>${views ? (1000 * x / views).toFixed(1) : '–'}</b></div><div class="meter"><b style="width:${views ? Math.min(100, 100 * (1000 * x / views) / top) : 0}%"></b></div></div>`).join('')}</div></div>
  </div></section>

  <section id="reels"><div class="sh"><div><h2>Reels</h2><p>From the moment each is made to its numbers. Tap one to watch it and see everything.</p></div></div>
    <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:14px"><div class="filters" id="filters">
      ${[['all', 'All'], ['scheduled', 'Scheduled'], ['posted', 'Posted'], ['draft', 'On hold']].map(([k, t]) => `<button data-f="${k}" class="${k === 'all' ? 'on' : ''}">${t} <span class="muted">${k === 'all' ? reels.length : reels.filter(r => r.status === k).length}</span></button>`).join('')}
    </div><input class="search" id="q" placeholder="Search a word…" aria-label="Search reels"></div>
    <div class="gallery" id="gallery"></div></section>

  <section id="schedule"><div class="grid g2">
    <div class="card"><div class="sh"><div><h2>Schedule</h2><p>Posted automatically at these times. A reel that misses its slot moves to the next one.</p></div></div>
      ${sched.length ? `<ul class="tline">${sched.map(r => { const d = new Date(r.publish_at);
        return `<li><div class="d"><b>${d.toLocaleString('en-IN', {timeZone:'Asia/Kolkata', day:'numeric'})}</b><span>${d.toLocaleString('en-IN', {timeZone:'Asia/Kolkata', weekday:'short'})}</span></div>
        ${r.cover ? `<img src="${esc(r.cover)}" alt="">` : '<img alt="">'}<div class="t"><b>${esc(r.title)}</b><small>${ist(r.publish_at, {day:undefined, month:undefined})} IST${r.hook_score != null ? ` · hook ${r.hook_score}` : ''}</small></div><span class="pill" data-rel="${esc(r.publish_at)}">${ago(r.publish_at)}</span></li>`; }).join('')}</ul>` : '<div class="empty">Nothing scheduled yet.</div>'}</div>
    <div class="card"><div class="sh"><div><h2>Best time to post</h2><p>Learned from when your followers are online and how each slot did.</p></div></div>
      <div class="slots">${(D.best.slots || []).map(s => `<span>${esc(s)}</span>`).join('') || '<span>—</span>'}</div><p class="small muted" style="margin:6px 0 0">${esc(D.best.why)}</p>
      <hr style="border:0;border-top:1px solid var(--line);margin:16px 0"><div class="label">Making</div><p class="small" style="margin:6px 0 0">A new reel at 05:00 and 14:00 IST whenever fewer than 3 are waiting. <a href="https://github.com/${esc(REPO)}/actions/workflows/make.yml" target="_blank" rel="noopener">Make one now ↗</a></p></div>
  </div></section>

  <section id="growth"><div class="sh"><div><h2>Growth</h2><p>Every Sunday Claude reviews the numbers and the niche; every new reel reads these notes.</p></div></div>
    <div class="grid g3">
      <div class="card notes"><div class="label" style="margin-bottom:8px">What works on this channel</div>${D.learnings || '<p class="muted">After the first weekly review.</p>'}</div>
      <div class="card notes"><div class="label" style="margin-bottom:8px">Hook formulas working in the niche</div>${D.swipe || '<p class="muted">After the first weekly review.</p>'}</div>
      <div class="card"><div class="label">Accounts we learn from</div>
        <p class="small muted" style="margin:6px 0">${D.watch.ok.length} read · ${D.watch.outliers} outlier reels found${D.watch.at ? ' · ' + ago(D.watch.at) : ''}. Add more in <code>maker/watch.json</code>.</p>
        <div class="acc">${D.watch.ok.map(a => `<a class="chip" href="https://instagram.com/${esc(a.account)}" target="_blank" rel="noopener"><span class="dot ok"></span>@${esc(a.account)} <span class="muted">${fmt(a.followers)}</span></a>`).join('')}
        ${D.watch.failed.map(a => `<span class="chip" title="${esc(a.why)}"><span class="dot warn"></span>@${esc(a.account)} <span class="muted">can't read</span></span>`).join('')}</div>
        <hr style="border:0;border-top:1px solid var(--line);margin:16px 0"><div class="label">Every reel is checked for</div>
        <ul class="list small"><li>🎯 3 hooks compete; the best (65+) opens the reel</li><li>✍️ caption: one ask, 3 hashtags, words people search</li><li>🔁 last line loops into the first</li><li>🧑 no machine-sounding phrases</li></ul></div>
    </div></section>

  <section id="comments"><div class="grid g2">
    <div class="card"><div class="sh"><div><h2>Comments</h2><p id="cmeta">Claude answers new comments every 30 minutes.</p></div></div><div id="clist"><p class="muted">Loading…</p></div></div>
    <div class="card"><div class="sh"><div><h2>Held for you</h2><p>Ones Claude thinks a person should answer.</p></div></div><div id="cheld"><p class="muted">Loading…</p></div></div>
  </div></section>

  <section id="system"><div class="grid g2">
    <div class="card"><div class="sh"><div><h2>Automation</h2><p>Each job on GitHub and how its last run went.</p></div><a class="btn" href="https://github.com/${esc(REPO)}/actions" target="_blank" rel="noopener">All runs ↗</a></div>
      <div class="wf">${D.workflows.map(w => { const l = w.last || {}, c = w.state !== 'active' ? 'warn' : l.conclusion === 'failure' ? 'bad' : l.status && l.status !== 'completed' ? 'live' : 'ok';
        return `<a href="${esc(l.url || `https://github.com/${REPO}/actions`)}" target="_blank" rel="noopener"><b><span class="dot ${c}"></span>${esc(w.name)}</b><small>${w.state !== 'active' ? esc(w.state.replace(/_/g, ' ')) : l.createdAt ? `${esc(l.conclusion || l.status)} · ${ago(l.createdAt)}` : 'no runs yet'}</small></a>`; }).join('')}</div></div>
    <div class="card"><div class="sh"><div><h2>Activity</h2><p>Everything that happened, newest first.</p></div></div>
      <ul class="feed">${D.activity.map(a => `<li><span class="ic">${{made:'🎬', posted:'📤', run:'⚙️', fail:'⚠️', reply:'💬'}[a.kind] || '•'}</span><div><b>${esc(a.title)}</b><small>${esc(a.sub)}</small></div><time title="${ist(a.at)}">${ago(a.at)}</time></li>`).join('') || '<li class="empty">No activity yet.</li>'}</ul></div>
  </div></section>`);
  gallery('all', '');
  $('#filters').onclick = e => { const b = e.target.closest('button'); if (!b) return; document.querySelectorAll('#filters button').forEach(x => x.classList.toggle('on', x === b)); gallery(b.dataset.f, $('#q').value); };
  $('#q').oninput = e => gallery(document.querySelector('#filters .on').dataset.f, e.target.value);
  tabsSpy(); live(); commentsLive();
}

function chart() {
  const rs = posted.filter(r => r.ins.views != null).sort((a, b) => (a.posted_at || '').localeCompare(b.posted_at || ''));
  if (!rs.length) return '<div class="empty">Numbers appear a few hours after the first reels are posted.</div>';
  const W = 600, H = 220, pad = 30, max = Math.max(...rs.map(r => r.ins.views)) * 1.15 || 1, bw = Math.min(70, (W - pad * 2) / rs.length * .62);
  const med = [...rs.map(r => r.ins.views)].sort((a, b) => a - b)[Math.floor(rs.length / 2)], y = v => H - pad - (H - pad * 2) * v / max;
  const bars = rs.map((r, i) => { const x = pad + (i + .5) * (W - pad * 2) / rs.length - bw / 2;
    return `<g><title>${esc(r.title)}: ${r.ins.views} views</title><rect x="${x}" y="${y(r.ins.views)}" width="${bw}" height="${H - pad - y(r.ins.views)}" rx="8" fill="url(#bg)"/>
      <text x="${x + bw / 2}" y="${y(r.ins.views) - 6}" text-anchor="middle" style="fill:var(--ink);font-weight:700">${fmt(r.ins.views)}</text>
      <text x="${x + bw / 2}" y="${H - pad + 16}" text-anchor="middle">${esc(r.title.split(' → ')[0])}</text></g>`; }).join('');
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Views per reel"><defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ff7a2f"/><stop offset="1" stop-color="#d6336c"/></linearGradient></defs>
    <line x1="${pad}" x2="${W - pad}" y1="${H - pad}" y2="${H - pad}" stroke="var(--line)"/><line x1="${pad}" x2="${W - pad}" y1="${y(med)}" y2="${y(med)}" stroke="var(--mute)" stroke-dasharray="4 4" opacity=".6"/>${bars}</svg>`;
}

function gallery(f, q) {
  const order = {scheduled: 0, draft: 1, posted: 2, made: 3};
  const rs = reels.filter(r => (f === 'all' || r.status === f) && (!q || (r.title + ' ' + r.name + ' ' + (r.caption || '')).toLowerCase().includes(q.toLowerCase())))
    .sort((a, b) => order[a.status] - order[b.status] || (a.status === 'posted' ? (b.posted_at || '').localeCompare(a.posted_at || '') : (a.publish_at || '').localeCompare(b.publish_at || '')));
  $('#gallery').innerHTML = rs.map(r => `<article class="card reel fade">
    <button class="cv" data-open="${esc(r.name)}" aria-label="Open ${esc(r.title)}">${r.cover ? `<img src="${esc(r.cover)}" alt="" loading="lazy">` : ''}
      <span class="badge ${r.status}"><span class="dot"></span>${esc(r.label)}</span>${r.hook_score != null ? `<span class="score" title="hook score">🎯 ${r.hook_score}</span>` : ''}
      ${r.video ? '<span class="play">▶</span>' : ''}<span class="ttl"><b>${esc(r.title)}</b><small>${r.status === 'posted' ? 'posted ' + ago(r.posted_at) : r.publish_at ? ist(r.publish_at) : ''}${r.dur ? ' · ' + Math.round(r.dur) + ' s' : ''}</small></span></button>
    <div class="body">${r.status === 'posted' ? `<div class="stats"><span>▶ <b>${fmt(r.ins.views)}</b></span><span>↗ <b>${fmt(r.ins.shares)}</b></span><span>💬 <b>${fmt(r.ins.comments)}</b></span><span>♥ <b>${fmt(r.ins.likes)}</b></span></div>`
      : `<div class="stats">${r.hook_formula ? `<span>${esc(r.hook_formula)}</span>` : `<span>${esc(r.style || '')}</span>`}</div>`}
      <div class="pipe" title="${esc(r.stages.map(s => s[0] + (s[1] ? ' ✓' : '')).join(' · '))}">${r.stages.map(s => `<i class="${s[1] ? 'on' : ''}"></i>`).join('')}</div>
      <div class="acts"><button class="btn pri" data-open="${esc(r.name)}">${r.video ? '▶ Watch' : 'Details'}</button>${r.permalink ? `<a class="btn" href="${esc(r.permalink)}" target="_blank" rel="noopener">Instagram ↗</a>` : ''}</div></div></article>`).join('') || '<div class="empty">No reels here.</div>';
}

function openReel(name) {
  const r = reels.find(x => x.name === name); if (!r) return; const dlg = $('#dlg');
  dlg.innerHTML = `<button class="x" aria-label="Close">✕</button><div class="dlg">${r.video ? `<video controls playsinline autoplay src="${esc(r.video)}" poster="${esc(r.cover || '')}"></video>` : r.cover ? `<img src="${esc(r.cover)}" alt="" style="width:100%;display:block">` : '<div class="empty">Video not on this device</div>'}
    <div class="side"><span class="label">${esc(r.label)}${r.dur ? ' · ' + Math.round(r.dur) + ' s' : ''}</span><h3>${esc(r.title)}</h3>
    <p class="small muted" style="margin:0 0 10px">${r.status === 'posted' ? 'Posted ' + ist(r.posted_at) + (r.by_hand ? ' (by hand)' : '') : r.publish_at ? 'Posts ' + ist(r.publish_at, {weekday:'short'}) + ' IST' : ''}${r.permalink ? ` · <a href="${esc(r.permalink)}" target="_blank" rel="noopener">open on Instagram ↗</a>` : ''}</p>
    ${r.status === 'posted' ? `<div class="stats" style="margin-bottom:12px">${[['▶', 'views'], ['👁', 'reach'], ['♥', 'likes'], ['💬', 'comments'], ['↗', 'shares'], ['🔖', 'saved'], ['➕', 'follows']].map(([i, k]) => `<span>${i} <b>${fmt(r.ins[k])}</b> ${k}</span>`).join('')}</div>` : ''}
    <div class="label">Stages</div><div class="stagelist">${r.stages.map(s => `<div class="${s[1] ? 'on' : ''}">${s[1] ? '✓' : '○'} ${esc(s[0])}${s[2] ? `<small>${esc(s[2])}</small>` : ''}</div>`).join('')}</div>
    ${r.hooks.length ? `<div class="label" style="margin-top:12px">Hook contest</div><ul class="hooks">${r.hooks.sort((a, b) => b.score - a.score).map(h => `<li><div class="ring" style="--p:${h.score}"><span>${h.score}</span></div><div><b>${esc(h.line)}</b><br><small class="muted">${esc(h.formula)}${h.line === r.hook_line ? ' · <span class="ok">used</span>' : ''}</small></div></li>`).join('')}</ul>`
      : r.hook_line ? `<div class="label" style="margin-top:12px">Hook</div><p style="margin:4px 0">${esc(r.hook_line)}</p>` : ''}
    ${r.caption ? `<div class="label" style="margin-top:12px">Caption</div><pre>${esc(r.caption)}</pre>` : ''}</div></div>`;
  dlg.showModal();
  const close = () => dlg.close(); dlg.querySelector('.x').onclick = close;
}
document.addEventListener('click', e => { const b = e.target.closest('[data-open]'); if (b) openReel(b.dataset.open); const d = $('#dlg'); if (e.target === d) d.close(); });
document.addEventListener('close', e => { const v = e.target.querySelector && e.target.querySelector('video'); if (v) { v.pause(); v.removeAttribute('src'); v.load(); } }, true);

function tabsSpy() {
  const links = [...document.querySelectorAll('.tabs a[href^="#"]')], obs = new IntersectionObserver(es => es.forEach(en => { if (en.isIntersecting) links.forEach(l => l.classList.toggle('on', l.getAttribute('href') === '#' + en.target.id)); }), {rootMargin: '-40% 0px -55% 0px'});
  links.forEach(l => { const s = document.getElementById(l.getAttribute('href').slice(1)); if (s) obs.observe(s); });
}

// ───────── live parts (read from the repo, so the website is current between rebuilds)
const ICON = {done:'✓', running:'◐', failed:'✕', skipped:'–', waiting:''};
async function progress() {
  const r = await raw('progress.json?ref=status');
  if (!r.ok) throw new Error(r.status === 404 ? 'No reel has been made on GitHub with live progress yet.' : `GitHub said ${r.status}` + (r.status === 403 ? ' (too many refreshes; it comes back within the hour)' : ''));
  return r.json();
}
const pct = p => { const st = p.stages || [], d = st.filter(s => s.state === 'done' || s.state === 'skipped').length, r = st.some(s => s.state === 'running') ? .5 : 0; return p.status === 'done' ? 100 : st.length ? Math.round(100 * (d + r) / st.length) : 0; };
function poll(render) { let t; const go = async () => { try { const p = await progress(); render(p, null); clearTimeout(t); if (p.status === 'running') t = setTimeout(go, 30000); } catch (e) { render(null, e.message); } }; go(); }
function live() {
  poll((p, err) => { const el = $('#now'); if (!el) return;
    if (err) { el.innerHTML = `<div class="label">Making</div><p class="muted small">${esc(err)}</p>`; return; }
    const cur = (p.stages || []).find(s => s.state === 'running'), on = p.status === 'running';
    el.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center"><span class="label">${on ? 'Making now' : 'Last make'}</span><span class="chip"><span class="dot ${on ? 'live' : p.status === 'done' ? 'ok' : p.status === 'failed' ? 'bad' : ''}"></span>${esc(p.status)}</span></div>
      <div class="word">${esc(p.word || (on ? 'Claude is choosing a word…' : '—'))}</div>${p.hook ? `<div class="small muted">hook: ${esc(p.hook)}</div>` : ''}
      <div class="prog"><b style="width:${pct(p)}%"></b></div>
      <div class="small">${on ? `<b>${esc(cur ? cur.label : 'Starting')}</b>${cur && cur.detail ? ' · ' + esc(cur.detail) : ''} · <span data-since="${esc(p.started)}"></span>` : esc(p.detail || '') + (p.took ? ' · took ' + dur(p.took) : '')}</div>
      <div class="mini-steps">${(p.stages || []).map(s => `<i class="${s.state}" title="${esc(s.label)}"></i>`).join('')}</div>
      <p class="small" style="margin:12px 0 0"><a href="making.html">Every step, the script and the history →</a></p>`; });
}
async function commentsLive() {
  const get = f => raw('comments/' + f).then(r => r.ok ? r.json() : []).catch(() => []);
  const [sent, held, hidden] = await Promise.all([get('sent.json'), get('held.json'), get('hidden.json')]);
  const k = $('#kreplied'); if (k) k.textContent = sent.length;
  $('#cmeta').textContent = `Claude answers new comments every 2 hours · ${sent.length} replied · ${hidden.length} hidden as spam`;
  $('#clist').innerHTML = sent.length ? `<ul class="list">${sent.slice(-8).reverse().map(c => `<li><small class="muted">@${esc(c.from)} · ${ago(c.sent_at)}${c.reel ? ' · ' + esc(c.reel) : ''}</small><br>${esc(c.text)}<span class="reply">↳ ${esc(c.reply)}</span></li>`).join('')}</ul>` : '<div class="empty">No comments answered yet.</div>';
  $('#cheld').innerHTML = held.length ? `<ul class="list">${held.slice(-8).reverse().map(c => `<li><b>@${esc(c.from)}</b> ${esc(c.text)}<br><small class="muted">${esc(c.why)}${c.permalink ? ` · <a href="${esc(c.permalink)}" target="_blank" rel="noopener">answer on Instagram ↗</a>` : ''}</small></li>`).join('')}</ul>` : '<div class="empty">Nothing waiting for you. 🎉</div>';
}

// ───────── making page
function making() {
  shell(`<div class="grid g2" style="margin-top:18px"><div><div class="card make" id="main"><p class="muted">Loading…</p></div>
      <div class="card" style="margin-top:14px"><div class="sh"><div><h2>Earlier makes</h2></div></div><div id="hist"><p class="muted">Loading…</p></div></div></div>
    <div><div class="card"><div class="sh"><div><h2>Hook contest</h2><p>Three openings, scored; the best opens the reel.</p></div></div><div id="hooks"><p class="muted small">Appears once Claude has written the script.</p></div></div>
      <div class="card" style="margin-top:14px"><div class="sh"><div><h2>The script</h2></div></div><div id="script"><p class="muted small">Appears once Claude has written it.</p></div></div></div></div>`);
  poll((p, err) => {
    if (err) { $('#main').innerHTML = `<p class="muted">${esc(err)}</p>`; $('#hist').innerHTML = ''; return; }
    const on = p.status === 'running';
    $('#main').innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center"><span class="label">${on ? 'Making now' : 'Last make'}</span><span class="chip"><span class="dot ${on ? 'live' : p.status === 'done' ? 'ok' : p.status === 'failed' ? 'bad' : ''}"></span>${esc(p.status)}</span></div>
      <div class="word" style="font-size:30px">${esc(p.word || (on ? 'Claude is choosing a word…' : '—'))}</div>${p.hook ? `<div class="muted">hook card: ${esc(p.hook)}</div>` : ''}
      <div class="prog"><b style="width:${pct(p)}%"></b></div>
      <p class="small muted" style="margin:0 0 6px">started ${ist(p.started)} · ${on ? 'running for <span data-since="' + esc(p.started) + '"></span>' : 'took ' + dur(p.took)}${p.publish_at ? ' · posts ' + ist(p.publish_at) + ' IST' : ''}${p.run_url ? ` · <a href="${esc(p.run_url)}" target="_blank" rel="noopener">run log ↗</a>` : ''}</p>
      ${p.detail && !on ? `<p style="margin:0 0 6px"><b>${esc(p.detail)}</b></p>` : ''}
      <ol class="steps">${(p.stages || []).map((s, i) => `<li class="${s.state}"><span class="n">${ICON[s.state] || i + 1}</span><div><b>${esc(s.label)}</b><span class="about">${esc(s.about)}</span>${s.detail ? `<span class="det">${esc(s.detail)}</span>` : ''}</div><time>${s.started ? dur(secs(s.started, s.ended)) : ''}</time></li>`).join('')}</ol>
      ${(p.attempts || []).length ? `<div class="label" style="margin-top:12px">Tries that were rejected</div><ul class="list small">${p.attempts.map(a => `<li>${esc(a)}</li>`).join('')}</ul>` : ''}
      ${p.caption ? `<details style="margin-top:10px"><summary class="small muted" style="cursor:pointer">Caption</summary><pre style="white-space:pre-wrap;font:inherit;font-size:14px">${esc(p.caption)}</pre></details>` : ''}`;
    $('#hooks').innerHTML = (p.hooks || []).length ? `<ul class="hooks">${[...p.hooks].sort((a, b) => b.score - a.score).map(h => `<li><div class="ring" style="--p:${h.score}"><span>${h.score}</span></div><div><b>${esc(h.line)}</b><br><small class="muted">${esc(h.formula)} · card: ${esc(h.card)}</small></div></li>`).join('')}</ul>` : '<p class="muted small">Appears once Claude has written the script.</p>';
    $('#script').innerHTML = (p.lines || []).length ? '<ol class="script">' + p.lines.map(l => `<li><small>${esc(l.id)}</small><div>${esc(l.text)}${l.cue ? `<span class="cue">${esc(l.cue)}</span>` : ''}${l.write ? `<em>✎ ${esc(l.write)}</em>` : ''}</div></li>`).join('') + '</ol>' : '<p class="muted small">Appears once Claude has written it.</p>';
    const h = p.history || [];
    $('#hist').innerHTML = h.length ? '<table><tr><th>When</th><th>Reel</th><th>Result</th></tr>' + h.map(x => `<tr><td>${ist(x.started)}</td><td>${esc(x.word || '—')}${x.publish_at ? `<br><small class="muted">posts ${ist(x.publish_at)}</small>` : ''}</td><td><span class="chip"><span class="dot ${x.status === 'done' ? 'ok' : x.status === 'failed' ? 'bad' : ''}"></span>${esc(x.status)}</span><br><small class="muted">${dur(x.took)}</small>${x.run_url ? ` <a href="${esc(x.run_url)}" target="_blank" rel="noopener">↗</a>` : ''}</td></tr>`).join('') + '</table>' : '<p class="muted">None yet.</p>';
  });
}

// ───────── tickers
setInterval(() => {
  document.querySelectorAll('[data-since]').forEach(el => el.textContent = dur(secs(el.dataset.since)));
  document.querySelectorAll('[data-rel]').forEach(el => el.textContent = ago(el.dataset.rel));
  document.querySelectorAll('[data-count]').forEach(el => { let s = Math.max(0, (new Date(el.dataset.count) - Date.now()) / 1000);
    const u = [['days', 86400], ['hrs', 3600], ['min', 60], ['sec', 1]].map(([n, k]) => { const v = Math.floor(s / k); s -= v * k; return [n, v]; });
    el.innerHTML = u.filter(([n, v], i) => i > 0 || v > 0).map(([n, v]) => `<div><b>${String(v).padStart(2, '0')}</b><span>${n}</span></div>`).join(''); });
}, 1000);
setInterval(() => { if (!document.querySelector('dialog[open]') && document.visibilityState === 'visible') location.reload(); }, RELOAD);
(document.body.dataset.view === 'making' ? making : home)();
