"""Reel dashboard: every reel from the moment it is made to its numbers after posting, plus the reel being made right now.
  python dashboard/build.py [--open] [--watch]   → dashboard/index.html + making.html on this computer
  python dashboard/build.py --site _site         → the website version (GitHub Pages; pages.yml runs it): covers in c/,
                                                   videos in v/ (pages.yml downloads the release's videos there first)
Reads queue/ and posted/, reports/, comments/, maker/, the local film folders (FILMS, local only) and GitHub through the gh
CLI. The "making" parts are live: the page reads progress.json from the repo's status branch (maker/progress.py)."""
import datetime as dt, html, json, os, shutil, subprocess, sys, webbrowser

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
FILMS = os.environ.get('FILMS', os.path.join(os.path.dirname(ROOT), 'lemo-opuscar', 'films'))
REPO = os.environ.get('REPO', os.environ.get('GITHUB_REPOSITORY', 'Shahaashish252/insta-autopilot'))
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
SITE = sys.argv[sys.argv.index('--site') + 1] if '--site' in sys.argv else None
OUT = os.path.abspath(SITE) if SITE else HERE
E = lambda s: html.escape(str(s if s is not None else ''))


def jload(p, d=None):
    try: return json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError): return d


def mtime(p):
    return dt.datetime.fromtimestamp(os.path.getmtime(p), IST) if os.path.exists(p) else None


def gh(*args):
    try: return subprocess.run(['gh', *args], capture_output=True, text=True, encoding='utf-8', timeout=40).stdout
    except (OSError, subprocess.SubprocessError): return ''


def when(t):
    if not t: return ''
    if isinstance(t, str):
        try: t = dt.datetime.fromisoformat(t.replace('Z', '+00:00'))
        except ValueError: return t
    return t.astimezone(IST).strftime('%d %b, %I:%M %p').lstrip('0').replace(' 0', ' ')


def rel(p):
    return os.path.relpath(p, OUT).replace('\\', '/')


def media(name, kind, src):
    """A cover or a video, as a path the page can load: copied into the site (c/, v/), or the local file itself."""
    if not src or not os.path.isfile(src): return ''
    if not SITE: return rel(src)
    sub = 'c' if kind == 'cover' else 'v'; ext = os.path.splitext(src)[1]
    dst = os.path.join(OUT, sub, name + ext); os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.abspath(src) != os.path.abspath(dst): shutil.copyfile(src, dst)
    return f'{sub}/{name}{ext}'


# ───────── reels: made → checked → queued → caption → approved → scheduled → posted → numbers
def reels():
    out = {}
    for name in sorted(os.listdir(FILMS)) if os.path.isdir(FILMS) and not SITE else []:
        d = os.path.join(FILMS, name); mp4 = os.path.join(d, name + '.mp4')
        if not os.path.isfile(mp4): continue
        spec = jload(os.path.join(d, 'spec.json'), {}) or {}
        ev = jload(os.path.join(d, 'events.json'), {}) or {}
        out[name] = {'name': name, 'title': spec.get('title', '').split(' · ')[0] or name, 'made': mtime(mp4), 'dur': ev.get('dur'),
                     'mb': os.path.getsize(mp4) / 1e6, 'cover_src': os.path.join(d, 'poster.jpg'), 'video_src': mp4, 'checked': True,
                     'style': 'Shabd Sketch' if os.path.isfile(os.path.join(d, 'js', 'scene.js')) else 'Chalkboard'}
    for where in ('queue', 'posted'):
        base = os.path.join(ROOT, where)
        for name in sorted(os.listdir(base)) if os.path.isdir(base) else []:
            f = os.path.join(base, name); meta = jload(os.path.join(f, 'post.json'))
            if not meta: continue
            r = out.setdefault(name, {'name': name, 'title': meta.get('title', name), 'style': 'Shabd Sketch'})
            r.update(post=meta, where=where, qtime=mtime(os.path.join(f, 'post.json')))
            if meta.get('title'): r['title'] = meta['title']
            if os.path.isfile(os.path.join(f, 'cover.jpg')): r['cover_src'] = os.path.join(f, 'cover.jpg')   # the chosen cover wins
            for v in (meta.get('file'), meta.get('asset')):
                if v and os.path.isfile(os.path.join(f, v)): r.setdefault('video_src', os.path.join(f, v))
            if meta.get('asset') and SITE and os.path.isfile(os.path.join(OUT, 'v', meta['asset'])):
                r.setdefault('video_src', os.path.join(OUT, 'v', meta['asset']))
            if meta.get('made_at') and not r.get('made'):              # made on GitHub (maker/make.py)
                r.update(made=dt.datetime.fromisoformat(meta['made_at']).astimezone(IST), dur=meta.get('duration'), checked=True,
                         style='Shabd Sketch · made on GitHub' if meta.get('asset') and not meta.get('file') and name != 'sabr-sab' else 'Shabd Sketch')
            elif not r.get('made'): r.update(made=r['qtime'], checked=True)
    ins = jload(os.path.join(ROOT, 'reports', 'insights.json'), {}) or {}
    by_id = {p['id']: p for p in ins.get('posts', [])}
    for r in out.values():
        mid = (r.get('post') or {}).get('media_id')
        if mid in by_id: r['ins'] = by_id[mid]
        r['cover'] = media(r['name'], 'cover', r.get('cover_src'))
        r['video'] = media(r['name'], 'video', r.get('video_src'))
    return list(out.values()), ins


def stages(r):
    p = r.get('post') or {}
    posted = r.get('where') == 'posted'
    due = p.get('publish_at')
    v = ((r.get('ins') or {}).get('insights') or {}).get('views')
    return [('Made', bool(r.get('made')), when(r.get('made'))),
            ('Checked', bool(r.get('checked')), 'voice, reading, loudness' if r.get('checked') else ''),
            ('Caption', bool(p.get('caption')), f'{len(p.get("caption", ""))} chars' if p.get('caption') else ''),
            ('Approved', bool(p.get('approved')), '' if p.get('approved') or not p else 'waiting for you'),
            ('Scheduled', bool(due) and bool(p.get('approved')), when(due) if due and not posted else ''),
            ('Posted', posted, when(p.get('posted_at')) if posted else ''),
            ('Numbers', bool(r.get('ins')), f'{v:,} views' if v is not None else '')]


def status_of(r):
    s = stages(r)
    if s[5][1]: return 'posted', 'Posted'
    if s[4][1]: return 'scheduled', 'Scheduled'
    if r.get('post'): return 'draft', 'Needs approval' if s[2][1] else 'Needs caption'
    return 'made', 'Not queued'


# ───────── the page
CSS = '''
:root{--bg:#f6f1e7;--card:#fffdf8;--ink:#221d19;--mute:#76695c;--line:#e6dccb;--red:#c0392b;--green:#2f7d4f;--amber:#a86c12;--blue:#2f5f8f;--soft:#f0e8da}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#17140f;--card:#211d17;--ink:#f1eadf;--mute:#a59886;--line:#3a3328;--red:#e0675a;--green:#5fb683;--amber:#e0a84a;--blue:#7fb0e0;--soft:#2a251d}}
:root[data-theme=dark]{--bg:#17140f;--card:#211d17;--ink:#f1eadf;--mute:#a59886;--line:#3a3328;--red:#e0675a;--green:#5fb683;--amber:#e0a84a;--blue:#7fb0e0;--soft:#2a251d}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI","Noto Sans Devanagari","Nirmala UI",sans-serif}
main{max-width:1180px;margin:0 auto;padding:22px 16px 60px}
header{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:flex-end;gap:10px 16px;margin-bottom:18px}
h1{margin:0;font-size:24px}h2{font-size:13px;text-transform:uppercase;letter-spacing:.07em;color:var(--mute);margin:26px 0 10px}
.sub{color:var(--mute);margin:2px 0 0;font-size:13px}nav{display:flex;gap:8px;flex-wrap:wrap}
.pill{padding:6px 12px;border-radius:99px;border:1px solid var(--line);background:var(--card);font-weight:600;font-size:13px;text-decoration:none;color:var(--ink)}
.pill.ok{color:var(--green)}.pill.no{color:var(--amber)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}.kpi b{display:block;font-size:26px;line-height:1.2}.kpi span{color:var(--mute);font-size:13px}
.grid{display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr);gap:18px}@media (max-width:900px){.grid{grid-template-columns:1fr}}
.reel{display:grid;grid-template-columns:96px minmax(0,1fr);gap:14px;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px;margin-bottom:12px}
.thumb{position:relative;border:0;padding:0;background:var(--soft);border-radius:9px;overflow:hidden;width:96px;aspect-ratio:9/16;cursor:pointer;display:block}
.thumb img{width:100%;height:100%;object-fit:cover;display:block}.thumb .play{position:absolute;inset:auto 6px 6px auto;background:rgba(0,0,0,.65);color:#fff;border-radius:99px;font-size:12px;padding:2px 8px}
.thumb[disabled]{cursor:default}
.head{display:flex;justify-content:space-between;gap:8px;align-items:flex-start}h3{margin:0;font-size:20px;line-height:1.3}
.meta{color:var(--mute);font-size:13px;margin:2px 0 10px}code{font-size:12px}
.badge{font-size:12px;font-weight:700;padding:2px 9px;border-radius:99px;white-space:nowrap;border:1px solid currentColor}
.badge.posted,.badge.done{color:var(--green)}.badge.scheduled,.badge.running{color:var(--blue)}.badge.draft,.badge.failed{color:var(--amber)}.badge.made,.badge.skipped,.badge.cancelled{color:var(--mute)}
.pipe{list-style:none;padding:0;margin:0 0 8px;display:flex;flex-wrap:wrap;gap:6px}
.pipe li{display:flex;align-items:center;gap:6px;background:var(--soft);border-radius:8px;padding:4px 9px;font-size:12px;color:var(--mute);line-height:1.3}
.pipe li i{width:9px;height:9px;border-radius:50%;border:2px solid var(--line);flex:none;background:var(--card)}
.pipe li.on{color:var(--ink)}.pipe li.on i{background:var(--green);border-color:var(--green)}.pipe li small{color:var(--mute)}
.acts{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:6px}
.btn{font:inherit;font-size:13px;font-weight:600;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:5px 11px;cursor:pointer;text-decoration:none}
.btn.primary{background:var(--ink);color:var(--card);border-color:var(--ink)}
details{margin-top:6px}summary{cursor:pointer;color:var(--mute);font-size:13px}pre{white-space:pre-wrap;font:inherit;font-size:13px;background:var(--soft);padding:10px;border-radius:8px;margin:6px 0 0}
a{color:var(--blue)}.panel{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin-bottom:14px}
.panel ul,.tl{list-style:none;padding:0;margin:0}.panel li{padding:6px 0;border-bottom:1px dashed var(--line);font-size:14px}.panel li:last-child{border:0}
.ok{color:var(--green)}.todo{color:var(--amber)}.muted{color:var(--mute)}small{color:var(--mute)}
.tl li{display:grid;grid-template-columns:110px minmax(0,1fr);gap:0 10px}.tl time{color:var(--mute);font-size:12px;grid-row:span 2}.tl b{font-size:14px}.tl span{color:var(--mute);font-size:12px}
.a.posted b{color:var(--green)}.a.made b{color:var(--red)}
table{width:100%;border-collapse:collapse}td,th{padding:6px 4px;border-bottom:1px dashed var(--line);text-align:left;font-size:14px;vertical-align:top}th{color:var(--mute);font-weight:600;font-size:12px}
.bar{height:8px;background:var(--soft);border-radius:99px;overflow:hidden;margin:8px 0}.bar b{display:block;height:100%;background:var(--blue);border-radius:99px;transition:width .4s}
.now b.word{font-size:22px}
dialog{border:0;border-radius:14px;padding:0;background:#000;max-width:min(420px,94vw);width:100%}dialog::backdrop{background:rgba(0,0,0,.7)}
dialog video{display:block;width:100%;max-height:86vh;background:#000}dialog .bar2{display:flex;justify-content:space-between;align-items:center;background:var(--card);padding:8px 12px}
.steps{list-style:none;margin:0;padding:0}.steps li{display:grid;grid-template-columns:26px minmax(0,1fr) auto;gap:4px 10px;padding:10px 0;border-bottom:1px solid var(--line)}
.steps li i{font-style:normal;font-weight:700;text-align:center}.steps .about{display:block;color:var(--mute);font-size:12px}.steps .det{display:block;font-size:13px;overflow-wrap:anywhere}
.steps time{color:var(--mute);font-size:12px;white-space:nowrap}.steps .done i{color:var(--green)}.steps .running i{color:var(--blue);display:inline-block;animation:spin 1.2s linear infinite}
.steps .running b{color:var(--blue)}.steps .failed i,.steps .failed b{color:var(--red)}.steps .waiting,.steps .skipped{opacity:.5}@keyframes spin{to{transform:rotate(360deg)}}
.script li{display:grid;grid-template-columns:40px minmax(0,1fr);gap:2px 8px}.script .cue{color:var(--red);font-size:12px;font-weight:700}.script em{color:var(--mute);font-style:normal;font-size:13px}
@media (max-width:520px){h1{font-size:21px}.reel{grid-template-columns:78px minmax(0,1fr);gap:10px}.thumb{width:78px}h3{font-size:18px}.tl li{grid-template-columns:1fr}.tl time{grid-row:auto}}
'''

LIVE_JS = '''
const REPO = %(repo)s, ICON = {done:'✓', running:'◐', failed:'✕', skipped:'–', waiting:'○'};
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const ist = t => t ? new Date(t).toLocaleString('en-IN', {timeZone:'Asia/Kolkata', day:'numeric', month:'short', hour:'numeric', minute:'2-digit'}) : '';
const secs = (a, b) => a ? Math.max(0, ((b ? new Date(b) : new Date()) - new Date(a)) / 1000) : null;
const dur = x => x == null ? '' : x >= 60 ? `${Math.floor(x / 60)} min ${String(Math.round(x %% 60)).padStart(2, '0')} s` : `${Math.round(x)} s`;
async function progress() {
  const r = await fetch(`https://api.github.com/repos/${REPO}/contents/progress.json?ref=status&t=${Date.now()}`, {headers:{Accept:'application/vnd.github.raw'}, cache:'no-store'});
  if (!r.ok) throw new Error(r.status === 404 ? 'No reel has been made on GitHub with live progress yet.' : `GitHub said ${r.status}` + (r.status === 403 ? ' (too many refreshes: it comes back within the hour)' : ''));
  return r.json();
}
function stepsHTML(p) {
  return '<ol class="steps">' + (p.stages || []).map(s => `<li class="${s.state}"><i>${ICON[s.state] || '○'}</i><div><b>${esc(s.label)}</b><span class="about">${esc(s.about)}</span>${s.detail ? `<span class="det">${esc(s.detail)}</span>` : ''}</div><time>${s.started ? dur(secs(s.started, s.ended)) : ''}</time></li>`).join('') + '</ol>';
}
function pct(p) { const st = p.stages || []; const d = st.filter(s => s.state === 'done' || s.state === 'skipped').length, r = st.some(s => s.state === 'running') ? .5 : 0; return st.length ? Math.round(100 * (d + r) / st.length) : 0; }
function poll(render) {
  let timer;
  const go = async () => { try { const p = await progress(); render(p, null); clearTimeout(timer); if (p.status === 'running') timer = setTimeout(go, 30000); } catch (e) { render(null, e.message); } };
  go(); setInterval(() => document.querySelectorAll('[data-since]').forEach(el => el.textContent = dur(secs(el.dataset.since))), 1000);
}
'''


def page(title, body, script=''):
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><style>{CSS}</style></head>
<body><main>{body}</main><script>{LIVE_JS % {'repo': json.dumps(REPO)}}{script}
setInterval(() => {{ if (!document.querySelector('dialog[open]')) location.reload(); }}, {60000 if '--watch' in sys.argv else 300000});</script></body></html>'''


def main():
    if not SITE: subprocess.run(['git', '-C', ROOT, 'pull', '-q', '--ff-only'], capture_output=True, timeout=60)
    os.makedirs(OUT, exist_ok=True)
    rows, ins = reels()
    runs = json.loads(gh('run', 'list', '-R', REPO, '--limit', '30', '--json', 'workflowName,status,conclusion,createdAt,event,url') or '[]')
    wfs = [l.split('\t') for l in gh('workflow', 'list', '-R', REPO, '--all').splitlines() if l.strip()]
    inbox = jload(os.path.join(ROOT, 'comments', 'held.json'), []) or []
    sent = jload(os.path.join(ROOT, 'comments', 'sent.json'), []) or []
    made = jload(os.path.join(ROOT, 'maker', 'made.json'), []) or []
    acct = ins.get('account', {}); best = jload(os.path.join(ROOT, 'reports', 'best_time.json'), {}) or {}
    now = dt.datetime.now(IST)

    act = []
    for r in rows:
        if r.get('made'): act.append((r['made'], 'made', f'Reel made: {r["title"]}', f'{r["dur"]:.0f} s · {r.get("style", "")}' if r.get('dur') else r.get('style', '')))
        p = r.get('post') or {}
        if p.get('posted_at'): act.append((dt.datetime.fromisoformat(p['posted_at']).astimezone(IST), 'posted', f'Posted: {r["title"]}', 'on Instagram'))
    for run in runs:
        t = dt.datetime.fromisoformat(run['createdAt'].replace('Z', '+00:00')).astimezone(IST)
        act.append((t, 'run', f'GitHub · {run["workflowName"]}', f'{run.get("conclusion") or run.get("status")} ({run.get("event")})'))
    for c in sent:
        act.append((dt.datetime.fromisoformat(c['sent_at']).astimezone(IST), 'reply', 'Replied to a comment', c.get('reply', '')[:60]))
    act.sort(key=lambda a: a[0], reverse=True)

    counts = {k: sum(1 for r in rows if status_of(r)[0] == k) for k in ('made', 'draft', 'scheduled', 'posted')}
    nxt = sorted((r for r in rows if status_of(r)[0] == 'scheduled'), key=lambda r: r['post']['publish_at'])
    connected = bool(acct)

    def card(r):
        k, label = status_of(r)
        pills = ''.join(f'<li class="{"on" if ok else ""}"><i></i><span>{E(n)}{f" <small>{E(note)}</small>" if note else ""}</span></li>' for n, ok, note in stages(r))
        p = r.get('post') or {}
        perma = (r.get('ins') or {}).get('permalink')
        cap = f'<details><summary>Caption</summary><pre>{E(p.get("caption"))}</pre></details>' if p.get('caption') else ''
        img = f'<img src="{E(r["cover"])}" alt="" loading="lazy">' if r.get('cover') else ''
        vid = r.get('video')
        thumb = (f'<button class="thumb" data-video="{E(vid)}" data-title="{E(r["title"])}" aria-label="Play {E(r["title"])}">{img}<span class="play">▶</span></button>' if vid
                 else f'<button class="thumb" disabled>{img}</button>')
        acts = ''.join([f'<button class="btn primary" data-video="{E(vid)}" data-title="{E(r["title"])}">▶ Watch</button>' if vid else
                        '<span class="muted" style="font-size:13px">video not on this device</span>',
                        f'<a class="btn" href="{E(perma)}" target="_blank" rel="noopener">Instagram ↗</a>' if perma else ''])
        return f'''<article class="reel">{thumb}<div>
<div class="head"><h3>{E(r["title"])}</h3><span class="badge {k}">{E(label)}</span></div>
<p class="meta">{E(r.get("style"))}{f" · {r['dur']:.0f} s" if r.get("dur") else ""} · <code>{E(r["name"])}</code></p>
<ol class="pipe">{pills}</ol><div class="acts">{acts}</div>{cap}</div></article>'''

    order = {'scheduled': 0, 'draft': 1, 'posted': 2, 'made': 3}
    cards = ''.join(card(r) for r in sorted(rows, key=lambda r: (order[status_of(r)[0]], (r.get('post') or {}).get('publish_at') or (r.get('post') or {}).get('posted_at') or '')))
    wf_rows = ''.join(f'<tr><td>{E(w[0])}</td><td><span class="badge {"done" if w[1] == "active" else "made"}">{E(w[1].replace("_", " "))}</span></td></tr>' for w in wfs)
    act_rows = ''.join(f'<li class="a {k}"><time>{E(when(t))}</time><b>{E(a)}</b><span>{E(b)}</span></li>' for t, k, a, b in act[:40]) or '<li>No activity yet.</li>'
    inbox_rows = ''.join(f'<li><b>@{E(c.get("from"))}</b> {E(c.get("text"))}<br><small>held: {E(c.get("why"))}</small></li>' for c in inbox[:8]) or '<li class="muted">Loading…</li>'
    making_href = 'making.html'
    header = lambda sub: f'''<header><div><h1>Reel Dashboard</h1><p class="sub">{sub} · updated {E(when(now))}</p></div>
<nav><a class="pill" href="index.html">Reels</a><a class="pill" href="{making_href}">Making ◐</a>
<span class="pill {"ok" if connected else "no"}">{("● @" + E(acct.get("username"))) if connected else "○ Instagram not connected"}</span></nav></header>'''

    body = header('From making the video to the numbers after posting') + f'''
<section class="kpis">
<div class="kpi"><b>{len(rows)}</b><span>reels</span></div>
<div class="kpi"><b>{counts["scheduled"]}</b><span>scheduled{f" · next {E(when(nxt[0]['post']['publish_at']))}" if nxt else ""}</span></div>
<div class="kpi"><b>{counts["posted"]}</b><span>posted</span></div>
<div class="kpi"><b>{counts["draft"]}</b><span>waiting for approval</span></div>
<div class="kpi"><b>{acct.get("followers_count", "–")}</b><span>followers</span></div>
<div class="kpi"><b id="kheld">{len(inbox)}</b><span>comments held for you</span></div>
</section>
<div class="grid"><div><h2>Making</h2><div class="panel now" id="now"><p class="muted">Loading the live progress…</p></div>
<h2>Every reel, stage by stage</h2>{cards}</div>
<aside><h2>Best time to post</h2><div class="panel">{('<p style="margin:0"><b>' + E(' and '.join(best.get('slots_ist', []))) + ' IST</b></p><p class="muted" style="margin:4px 0 0;font-size:13px">' + E(best.get('why', '')) + '</p>') if best else '<p class="muted">Worked out by each make.</p>'}</div>
<h2>Automation on GitHub</h2><div class="panel"><table>{wf_rows or '<tr><td class="muted">not available</td></tr>'}</table>
<p style="margin:8px 0 0"><a href="https://github.com/{E(REPO)}/actions" target="_blank" rel="noopener">All runs ↗</a></p></div>
<h2>Comments</h2><div class="panel" id="comments"><ul>{inbox_rows}</ul></div>
<h2>Activity</h2><div class="panel"><ol class="tl">{act_rows}</ol></div></aside></div>
<dialog id="player"><video controls playsinline preload="none"></video><div class="bar2"><b id="ptitle"></b><button class="btn" id="pclose">Close</button></div></dialog>'''
    script = '''
const dlg = document.getElementById('player'), vid = dlg.querySelector('video');
document.addEventListener('click', e => { const b = e.target.closest('[data-video]'); if (!b) return;
  vid.src = b.dataset.video; document.getElementById('ptitle').textContent = b.dataset.title; dlg.showModal(); vid.play().catch(() => {}); });
const stop = () => { vid.pause(); vid.removeAttribute('src'); vid.load(); };
document.getElementById('pclose').onclick = () => dlg.close(); dlg.addEventListener('close', stop);
dlg.addEventListener('click', e => { if (e.target === dlg) dlg.close(); });
(async () => {                       // comments: live from the repo (replies every 15 min)
  const get = f => fetch(`https://api.github.com/repos/${REPO}/contents/comments/${f}?t=${Date.now()}`, {headers:{Accept:'application/vnd.github.raw'}, cache:'no-store'}).then(r => r.ok ? r.json() : []).catch(() => []);
  const [sent, held, hidden] = await Promise.all([get('sent.json'), get('held.json'), get('hidden.json')]);
  const el = document.getElementById('comments'), ago = x => ist(x);
  document.getElementById('kheld').textContent = held.length;
  el.innerHTML = `<p style="margin:0 0 8px;font-size:13px" class="muted">Claude answers new comments every 15 minutes · ${sent.length} replied · ${hidden.length} hidden as spam/abuse · ${held.length} held for you</p>`
    + (held.length ? `<b style="font-size:13px">Held for you (answer these yourself)</b><ul>${held.slice(-6).reverse().map(c => `<li><b>@${esc(c.from)}</b> ${esc(c.text)}<br><small>${esc(c.why)} · ${esc(c.reel || '')} ${c.permalink ? `· <a href="${esc(c.permalink)}" target="_blank" rel="noopener">open ↗</a>` : ''}</small></li>`).join('')}</ul>` : '')
    + (sent.length ? `<b style="font-size:13px">Latest replies</b><ul>${sent.slice(-8).reverse().map(c => `<li><small>@${esc(c.from)} · ${ago(c.sent_at)}${c.reel ? ' · ' + esc(c.reel) : ''}</small><br>${esc(c.text)}<br><span style="color:var(--green)">↳ ${esc(c.reply)}</span></li>`).join('')}</ul>` : '<p class="muted" style="margin:0">No comments answered yet.</p>');
})();
poll((p, err) => {
  const el = document.getElementById('now');
  if (err) { el.innerHTML = `<p class="muted" style="margin:0">${esc(err)}</p><p style="margin:6px 0 0"><a href="making.html">Making page →</a></p>`; return; }
  const cur = (p.stages || []).find(s => s.state === 'running'), live = p.status === 'running';
  el.innerHTML = `<div class="head"><div><small>${live ? 'Making now' : 'Last make'} · started ${ist(p.started)}</small><br><b class="word">${esc(p.word || (live ? 'Claude is choosing a word…' : '—'))}</b></div><span class="badge ${p.status}">${esc(p.status)}</span></div>
    <div class="bar"><b style="width:${live ? pct(p) : p.status === 'done' ? 100 : pct(p)}%"></b></div>
    <p style="margin:0;font-size:14px">${live ? `<b>${esc(cur ? cur.label : 'Starting')}</b>${cur && cur.detail ? ' · ' + esc(cur.detail) : ''} · <span data-since="${esc(p.started)}"></span>` : esc(p.detail || '')}</p>
    <p style="margin:8px 0 0"><a href="making.html">Every step, the script and the history →</a></p>`;
});'''
    open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(page('Reel Dashboard', body, script))

    # making.html: everything about the reel being made (live) and the makes before it
    mbody = header('The reel being made on GitHub, step by step') + f'''
<div class="grid"><div><h2 id="mh">Making</h2><div class="panel" id="main"><p class="muted">Loading…</p></div></div>
<aside><h2>The script</h2><div class="panel" id="script"><p class="muted">Appears once Claude has written it.</p></div>
<h2>Earlier makes</h2><div class="panel" id="hist"><p class="muted">Loading…</p></div>
<h2>Schedule</h2><div class="panel"><p style="margin:0;font-size:14px">GitHub makes a reel at 05:00 and 14:00 IST when fewer than 3 are waiting, and posts at the best time ({E(' and '.join(best.get('slots_ist', [])) or '—')} IST now).</p>
<p style="margin:8px 0 0"><a href="https://github.com/{E(REPO)}/actions/workflows/make.yml" target="_blank" rel="noopener">Make one now on GitHub ↗</a></p></div></aside></div>'''
    mscript = '''
poll((p, err) => {
  const main = document.getElementById('main');
  if (err) { main.innerHTML = `<p class="muted">${esc(err)}</p>`; document.getElementById('hist').innerHTML = ''; return; }
  const live = p.status === 'running';
  document.getElementById('mh').textContent = live ? 'Making now' : 'Last make';
  main.innerHTML = `<div class="head"><div><b class="word" style="font-size:26px">${esc(p.word || (live ? 'Claude is choosing a word…' : '—'))}</b>${p.hook ? `<br><small>hook: ${esc(p.hook)}</small>` : ''}</div><span class="badge ${p.status}">${esc(p.status)}</span></div>
    <div class="bar"><b style="width:${p.status === 'done' ? 100 : pct(p)}%"></b></div>
    <p style="margin:0 0 6px;font-size:13px" class="muted">started ${ist(p.started)} · ${live ? 'running for <span data-since="' + esc(p.started) + '"></span>' : 'took ' + dur(p.took)}${p.publish_at ? ' · posts ' + ist(p.publish_at) + ' IST' : ''} · <a href="${esc(p.run_url)}" target="_blank" rel="noopener">run log ↗</a></p>
    ${p.detail && !live ? `<p style="margin:0 0 6px"><b>${esc(p.detail)}</b></p>` : ''}
    ${stepsHTML(p)}
    ${(p.attempts || []).length ? `<h2>Tries that were rejected</h2><ul>${p.attempts.map(a => `<li style="font-size:13px">${esc(a)}</li>`).join('')}</ul>` : ''}
    ${p.caption ? `<details><summary>Caption</summary><pre>${esc(p.caption)}</pre></details>` : ''}`;
  document.getElementById('script').innerHTML = (p.lines || []).length ? '<ol class="script" style="list-style:none;padding:0;margin:0">' + p.lines.map(l => `<li><small>${esc(l.id)}</small><div>${esc(l.text)}${l.write ? `<br><em>✎ ${esc(l.write)}</em>` : ''}${l.cue ? ` <span class="cue">${esc(l.cue)}</span>` : ''}</div></li>`).join('') + '</ol>' : '<p class="muted">Appears once Claude has written it.</p>';
  const h = p.history || [];
  document.getElementById('hist').innerHTML = h.length ? '<table><tr><th>When</th><th>Reel</th><th>Result</th></tr>' + h.map(x => `<tr><td>${ist(x.started)}</td><td>${esc(x.word || '—')}${x.publish_at ? `<br><small>posts ${ist(x.publish_at)}</small>` : ''}</td><td><span class="badge ${x.status}">${esc(x.status)}</span><br><small>${dur(x.took)}</small> <a href="${esc(x.run_url)}" target="_blank" rel="noopener">↗</a></td></tr>`).join('') + '</table>' : '<p class="muted">None yet.</p>';
});'''
    open(os.path.join(OUT, 'making.html'), 'w', encoding='utf-8').write(page('Making · Reel Dashboard', mbody, mscript))
    if SITE: open(os.path.join(OUT, '.nojekyll'), 'w').close()
    print(f'dashboard: {OUT}  ({len(rows)} reels, {sum(1 for r in rows if r.get("video"))} playable, {len(act)} activities)')
    if '--open' in sys.argv: webbrowser.open('file:///' + os.path.join(OUT, 'index.html').replace('\\', '/'))


if __name__ == '__main__':
    if '--watch' in sys.argv:                         # keep rebuilding; the open page reloads itself every minute
        import time
        while True:
            try: main()
            except Exception as e: print('refresh failed:', e)
            if '--open' in sys.argv: sys.argv.remove('--open')
            time.sleep(55)
    else:
        main()
