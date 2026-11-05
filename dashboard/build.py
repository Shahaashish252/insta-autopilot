"""Reel dashboard: every reel from the moment it is made to its numbers after posting, in one local page.
  python dashboard/build.py [--open] [--watch]   → dashboard/index.html (--watch: rebuild every minute; the page reloads itself)
Reads: the film folders (FILMS, default ../lemo-opuscar/films), queue/ and posted/ here, comments/, reports/, and GitHub
(workflow runs and which secrets exist, through the gh CLI, if it is logged in). Writes nothing anywhere else."""
import datetime as dt, html, json, os, subprocess, sys, webbrowser

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
FILMS = os.environ.get('FILMS', os.path.join(os.path.dirname(ROOT), 'lemo-opuscar', 'films'))
REPO = os.environ.get('REPO', 'Shahaashish252/insta-autopilot')
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
E = lambda s: html.escape(str(s or ''))


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
    return t.astimezone(IST).strftime('%d %b, %I:%M %p').replace(' 0', ' ')


# ───────── reels: made → caption → queued → approved → scheduled → posted → numbers
def reels():
    out = {}
    for name in sorted(os.listdir(FILMS)) if os.path.isdir(FILMS) else []:
        d = os.path.join(FILMS, name); mp4 = os.path.join(d, name + '.mp4')
        if not os.path.isfile(mp4): continue
        spec = jload(os.path.join(d, 'spec.json'), {}) or {}
        ev = jload(os.path.join(d, 'events.json'), {}) or {}
        title = spec.get('title', '').split(' · ')[0] or name
        out[name] = {'name': name, 'title': title, 'made': mtime(mp4), 'dur': ev.get('dur'), 'mb': os.path.getsize(mp4) / 1e6,
                     'poster': os.path.relpath(os.path.join(d, 'poster.jpg'), HERE).replace('\\', '/') if os.path.isfile(os.path.join(d, 'poster.jpg')) else '',
                     'checked': os.path.isfile(os.path.join(d, 'out', 'readcheck.txt')), 'srt': any(f.endswith('.srt') for f in os.listdir(d)),
                     'style': 'Shabd Sketch' if os.path.isfile(os.path.join(d, 'js', 'scene.js')) else 'Chalkboard'}
    for where in ('queue', 'posted'):
        base = os.path.join(ROOT, where)
        for name in sorted(os.listdir(base)) if os.path.isdir(base) else []:
            meta = jload(os.path.join(base, name, 'post.json'))
            if not meta: continue
            r = out.setdefault(name, {'name': name, 'title': meta.get('title', name), 'style': ''})
            r.update(post=meta, where=where, qtime=mtime(os.path.join(base, name, 'post.json')))
            if meta.get('title'): r['title'] = meta['title']
            if meta.get('made_at') and not r.get('made'):              # made on GitHub (maker/make.py): no local film folder
                r.update(made=dt.datetime.fromisoformat(meta['made_at']).astimezone(IST), dur=meta.get('duration'), checked=True, srt=True,
                         style='Shabd Sketch · made on GitHub')
            if not r.get('poster') and os.path.isfile(os.path.join(base, name, 'cover.jpg')):
                r['poster'] = os.path.relpath(os.path.join(base, name, 'cover.jpg'), HERE).replace('\\', '/')
    ins = jload(os.path.join(ROOT, 'reports', 'insights.json'), {}) or {}
    by_id = {p['id']: p for p in ins.get('posts', [])}
    for r in out.values():
        mid = (r.get('post') or {}).get('media_id')
        if mid in by_id: r['ins'] = by_id[mid]
    return list(out.values()), ins


def stages(r):
    p = r.get('post') or {}
    posted = r.get('where') == 'posted'
    due = p.get('publish_at')
    return [('Made', bool(r.get('made')), when(r.get('made')) if r.get('made') else ''),
            ('Checked', bool(r.get('checked')), 'voice · reading · loudness' if r.get('checked') else ''),
            ('Queued', bool(p), ''),
            ('Caption', bool(p.get('caption')), f'{len(p.get("caption", ""))} chars' if p.get('caption') else ''),
            ('Approved', bool(p.get('approved')), '' if p.get('approved') else ('waiting for you' if p else '')),
            ('Scheduled', bool(due) and bool(p.get('approved')), when(due) if due else ''),
            ('Posted', posted, when(p.get('posted_at')) if posted else ''),
            ('Numbers', bool(r.get('ins')), f'{(r.get("ins", {}).get("insights", {}) or {}).get("views", 0):,} views' if r.get('ins') else '')]


def status_of(r):
    s = stages(r)
    if s[6][1]: return 'posted', 'Posted'
    if s[5][1]: return 'scheduled', 'Scheduled'
    if s[2][1]: return 'draft', 'Needs approval' if s[3][1] else 'Needs caption'
    return 'made', 'Not queued'


# ───────── making: the make workflow's runs, step by step (live while one is running)
STAGES = [('Tools', 'Set up the studio', 'ffmpeg, renderer, Claude Code'),
          ('Fresh numbers', 'Channel numbers and best time', 'views by slot → when to post'),
          ('Make the reel', 'Write → voice → music → picture → checks', 'Claude writes the word and script; voice, speech check, mix, 1080×1920 render, reading check'),
          ('Save', 'Queued for posting', 'video to the media release, post.json with its slot')]


def secs(a, b):
    try: return (dt.datetime.fromisoformat(b.replace('Z', '+00:00')) - dt.datetime.fromisoformat(a.replace('Z', '+00:00'))).total_seconds()
    except (AttributeError, ValueError): return None


def dur(x):
    if x is None: return ''
    x = int(x); return f'{x // 60} min {x % 60:02d} s' if x >= 60 else f'{x} s'


def making():
    runs = json.loads(gh('run', 'list', '-R', REPO, '-w', 'make.yml', '--limit', '8', '--json', 'databaseId,status,conclusion,createdAt,updatedAt,event,url') or '[]')
    made = jload(os.path.join(ROOT, 'maker', 'made.json'), []) or []
    out = []
    for i, r in enumerate(runs):
        live = r['status'] != 'completed'
        steps = []
        if live or i == 0:                                              # step detail for the newest run and any running one
            jobs = json.loads(gh('run', 'view', str(r['databaseId']), '-R', REPO, '--json', 'jobs') or '{}').get('jobs', [])
            raw = jobs[0].get('steps', []) if jobs else []
            now = dt.datetime.now(dt.timezone.utc).isoformat()
            for key, label, sub in STAGES:
                st = next((x for x in raw if x['name'].startswith(key)), None)
                if not st: continue
                state = 'running' if st['status'] == 'in_progress' else ('done' if st.get('conclusion') == 'success' else
                        'failed' if st.get('conclusion') == 'failure' else 'skipped' if st.get('conclusion') == 'skipped' else 'waiting')
                el = secs(st.get('startedAt'), st.get('completedAt') if st['status'] == 'completed' else now) if st.get('startedAt') and not st['startedAt'].startswith('0001') else None
                steps.append((label, sub, state, el))
        word = next((m['word'] for m in made if r['createdAt'] <= m.get('at', '') <= (r.get('updatedAt') or '9')), '')
        out.append({**r, 'live': live, 'steps': steps, 'word': word, 'took': secs(r['createdAt'], r.get('updatedAt'))})
    return out


def main():
    subprocess.run(['git', '-C', ROOT, 'pull', '-q', '--ff-only'], capture_output=True, timeout=60)   # what GitHub made/posted
    rows, ins = reels()
    mk = making()
    runs = json.loads(gh('run', 'list', '-R', REPO, '--limit', '25', '--json', 'workflowName,status,conclusion,createdAt,event,url') or '[]')
    secrets = {l.split('\t')[0] for l in gh('secret', 'list', '-R', REPO).splitlines() if l.strip()}
    wfs = [l.split('\t') for l in gh('workflow', 'list', '-R', REPO, '--all').splitlines() if l.strip()]
    inbox = jload(os.path.join(ROOT, 'comments', 'inbox.json'), []) or []
    sent = jload(os.path.join(ROOT, 'comments', 'sent.json'), []) or []
    acct = ins.get('account', {})
    best = jload(os.path.join(ROOT, 'reports', 'best_time.json'), {}) or {}
    now = dt.datetime.now(IST)

    # activity timeline: everything with a time
    act = []
    for r in rows:
        if r.get('made'): act.append((r['made'], 'made', f'Reel made: {r["title"]}', f'{r.get("dur") or "?"} s · {r.get("style", "")}'))
        p = r.get('post') or {}
        if r.get('qtime'): act.append((r['qtime'], 'queue', f'Queued: {r["title"]}', 'approved' if p.get('approved') else 'draft, waiting for approval'))
        if p.get('posted_at'): act.append((dt.datetime.fromisoformat(p['posted_at']).astimezone(IST), 'posted', f'Posted: {r["title"]}', p.get('media_id', '')))
    for run in runs:
        t = dt.datetime.fromisoformat(run['createdAt'].replace('Z', '+00:00')).astimezone(IST)
        act.append((t, 'run', f'GitHub · {run["workflowName"]}', f'{run.get("conclusion") or run.get("status")} ({run.get("event")})'))
    for c in sent:
        act.append((dt.datetime.fromisoformat(c['sent_at']).astimezone(IST), 'reply', 'Replied to a comment', c.get('reply', '')[:60]))
    act.sort(key=lambda a: a[0], reverse=True)

    counts = {k: sum(1 for r in rows if status_of(r)[0] == k) for k in ('made', 'draft', 'scheduled', 'posted')}
    nxt = sorted((r for r in rows if status_of(r)[0] == 'scheduled'), key=lambda r: r['post']['publish_at'])
    connected = 'IG_ACCESS_TOKEN' in secrets

    def card(r):
        k, label = status_of(r)
        pills = ''.join(f'<li class="st {"on" if ok else ""}"><span class="dot"></span><b>{E(n)}</b><small>{E(note)}</small></li>' for n, ok, note in stages(r))
        p = r.get('post') or {}
        link = f'<a href="{E(r["ins"].get("permalink"))}" target="_blank">Open on Instagram ↗</a>' if r.get('ins', {}).get('permalink') else ''
        cap = f'<details><summary>Caption</summary><pre>{E(p.get("caption"))}</pre></details>' if p.get('caption') else ''
        img = f'<img src="{E(r["poster"])}" alt="">' if r.get('poster') else '<div class="noimg"></div>'
        return f'''<article class="reel"><div class="thumb">{img}</div><div class="body">
<div class="head"><h3>{E(r["title"])}</h3><span class="badge {k}">{E(label)}</span></div>
<p class="meta">{E(r.get("style"))}{f" · {r['dur']:.0f} s" if r.get("dur") else ""}{f" · {r['mb']:.0f} MB" if r.get("mb") else ""} · <code>{E(r["name"])}</code></p>
<ol class="pipe">{pills}</ol>{cap}{link}</div></article>'''

    ICON = {'done': '✓', 'running': '◐', 'failed': '✕', 'skipped': '–', 'waiting': '○'}
    def mk_steps(m):
        return '<ol class="steps">' + ''.join(f'<li class="st {k}"><i>{ICON[k]}</i><div><b>{E(a)}</b><small>{E(b)}</small></div><time>{E(dur(t))}</time></li>' for a, b, k, t in m['steps']) + '</ol>'
    def mk_line(m):
        res = 'running' if m['live'] else m.get('conclusion') or ''
        what = m['word'] or ('test render' if m['event'] == 'workflow_dispatch' and not m['word'] and res == 'success' else '')
        return f'<li><span class="badge {"scheduled" if m["live"] else "posted" if res == "success" else "made" if res in ("cancelled", "skipped") else "draft"}">{E(res)}</span> {E(when(m["createdAt"]))} {("· <b>" + E(what) + "</b>") if what else ""} <small>{E(dur(m["took"])) if not m["live"] else ""}</small> <a href="{E(m["url"])}" target="_blank">↗</a></li>'
    head = next((m for m in mk if m['live']), mk[0] if mk else None)
    mk_html = ((('<p class="muted">Making a reel on GitHub right now…</p>' if head['live'] else '<p class="muted">Last make:</p>') + mk_steps(head)) if head and head['steps'] else '') +               ('<p class="muted" style="margin-top:10px">Recent makes</p><ul class="mk">' + ''.join(mk_line(m) for m in mk) + '</ul>' if mk else '<p class="muted">No reel made on GitHub yet. It runs at 05:00 and 14:00 IST.</p>')
    wf_rows = ''.join(f'<tr><td>{E(w[0])}</td><td><span class="badge {"posted" if w[1] == "active" else "draft"}">{E(w[1].replace("_", " "))}</span></td></tr>' for w in wfs)
    act_rows = ''.join(f'<li class="a {k}"><time>{E(when(t))}</time><b>{E(a)}</b><span>{E(b)}</span></li>' for t, k, a, b in act[:40]) or '<li>No activity yet.</li>'
    inbox_rows = ''.join(f'<li><b>@{E(c.get("from"))}</b> {E(c.get("text"))}<small>{E(c.get("post"))}</small></li>' for c in inbox[:8]) or '<li class="muted">No comments waiting.</li>'
    setup = [('GitHub repo (private)', bool(wfs)), ('Instagram token saved', connected), ('Instagram account id (optional)', 'IG_USER_ID' in secrets),
             ('Claude can write reels (CLAUDE_CODE_OAUTH_TOKEN)', 'CLAUDE_CODE_OAUTH_TOKEN' in secrets), ('Analytics pulled', bool(ins)), ('Comments synced', os.path.isfile(os.path.join(ROOT, 'comments', 'inbox.json')))]
    setup_rows = ''.join(f'<li class="{"ok" if ok else "todo"}">{"✓" if ok else "○"} {E(n)}</li>' for n, ok in setup)

    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Reel Dashboard</title>{'<meta http-equiv="refresh" content="60">' if '--watch' in sys.argv else ''}<style>
:root{{--bg:#f6f1e7;--card:#fffdf8;--ink:#221d19;--mute:#7a6f63;--line:#e6dccb;--red:#c0392b;--green:#2f7d4f;--amber:#b7791f;--blue:#2f5f8f}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#17140f;--card:#211d17;--ink:#f1eadf;--mute:#a59886;--line:#3a3328;--red:#e0675a;--green:#5fb683;--amber:#e0a84a;--blue:#7fb0e0}}}}
:root[data-theme=dark]{{--bg:#17140f;--card:#211d17;--ink:#f1eadf;--mute:#a59886;--line:#3a3328;--red:#e0675a;--green:#5fb683;--amber:#e0a84a;--blue:#7fb0e0}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI","Noto Sans Devanagari",sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:28px 16px 60px}}
header{{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:end;gap:12px;margin-bottom:22px}}
h1{{margin:0;font-size:26px}}h2{{font-size:15px;text-transform:uppercase;letter-spacing:.06em;color:var(--mute);margin:30px 0 12px}}
.sub{{color:var(--mute);margin:2px 0 0}}.conn{{padding:6px 12px;border-radius:99px;border:1px solid var(--line);background:var(--card);font-weight:600}}
.conn.ok{{color:var(--green)}}.conn.no{{color:var(--amber)}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}}
.steps{{list-style:none;margin:0;padding:0}}.st{{display:grid;grid-template-columns:22px 1fr auto;gap:8px;padding:7px 0;border-bottom:1px solid var(--line)}}.st i{{font-style:normal;font-weight:700}}.st small{{display:block;color:var(--mute);font-size:12px}}.st time{{color:var(--mute);font-size:12px;white-space:nowrap}}.st.done i{{color:var(--green)}}.st.running i{{color:var(--blue);animation:spin 1.2s linear infinite;display:inline-block}}.st.running b{{color:var(--blue)}}.st.failed i,.st.failed b{{color:var(--red)}}.st.waiting,.st.skipped{{opacity:.55}}@keyframes spin{{to{{transform:rotate(360deg)}}}}.mk{{list-style:none;margin:0;padding:0;font-size:13px}}.mk li{{padding:4px 0}}
.kpi{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}}.kpi b{{display:block;font-size:28px}}.kpi span{{color:var(--mute);font-size:13px}}
.grid{{display:grid;grid-template-columns:2fr 1fr;gap:18px}}@media (max-width:900px){{.grid{{grid-template-columns:1fr}}}}
.reel{{display:flex;gap:14px;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px;margin-bottom:12px}}
.thumb img,.noimg{{width:84px;height:150px;object-fit:cover;border-radius:8px;background:var(--line);display:block}}
.body{{flex:1;min-width:0}}.head{{display:flex;justify-content:space-between;gap:8px;align-items:center}}h3{{margin:0;font-size:19px}}
.meta{{color:var(--mute);font-size:13px;margin:2px 0 8px}}code{{font-size:12px}}
.badge{{font-size:12px;font-weight:700;padding:3px 9px;border-radius:99px;white-space:nowrap;border:1px solid currentColor}}
.badge.posted{{color:var(--green)}}.badge.scheduled{{color:var(--blue)}}.badge.draft{{color:var(--amber)}}.badge.made{{color:var(--mute)}}
.pipe{{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(8,minmax(0,1fr));gap:4px}}
@media (max-width:640px){{.pipe{{grid-template-columns:repeat(4,1fr)}}.reel{{flex-direction:column}}.thumb img,.noimg{{width:100%;height:160px}}}}
.st{{position:relative;padding-top:16px;font-size:12px;color:var(--mute)}}.st b{{display:block;font-weight:600}}.st small{{display:block;font-size:11px;overflow-wrap:anywhere}}
.st .dot{{position:absolute;top:2px;left:0;width:11px;height:11px;border-radius:50%;border:2px solid var(--line);background:var(--card)}}
.st.on{{color:var(--ink)}}.st.on .dot{{background:var(--green);border-color:var(--green)}}
details{{margin-top:8px}}summary{{cursor:pointer;color:var(--mute);font-size:13px}}pre{{white-space:pre-wrap;font:inherit;font-size:13px;background:var(--bg);padding:10px;border-radius:8px}}
a{{color:var(--blue)}}.panel{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin-bottom:14px}}
.panel ul,.tl{{list-style:none;padding:0;margin:0}}.panel li{{padding:5px 0;border-bottom:1px dashed var(--line);font-size:14px}}.panel li:last-child{{border:0}}
.ok{{color:var(--green)}}.todo{{color:var(--amber)}}.muted{{color:var(--mute)}}small{{color:var(--mute)}}
.tl li{{display:grid;grid-template-columns:118px 1fr;gap:2px 10px;padding:7px 0;border-bottom:1px solid var(--line)}}.tl time{{color:var(--mute);font-size:12px;grid-row:span 2}}
.tl b{{font-size:14px}}.tl span{{color:var(--mute);font-size:12px}}.a.posted b{{color:var(--green)}}.a.made b{{color:var(--red)}}
table{{width:100%;border-collapse:collapse}}td{{padding:5px 0;border-bottom:1px dashed var(--line)}}
</style></head><body><main>
<header><div><h1>Reel Dashboard</h1><p class="sub">From making the video to the numbers after posting · updated {E(when(now))}</p></div>
<span class="conn {"ok" if connected else "no"}">{"● Instagram connected" + (f" · @{E(acct.get('username'))}" if acct.get("username") else "") if connected else "○ Instagram not connected yet"}</span></header>
<section class="kpis">
<div class="kpi"><b>{len(rows)}</b><span>reels made</span></div>
<div class="kpi"><b>{counts["draft"]}</b><span>waiting for your approval</span></div>
<div class="kpi"><b>{counts["scheduled"]}</b><span>scheduled{f" · next {E(when(nxt[0]['post']['publish_at']))}" if nxt else ""}</span></div>
<div class="kpi"><b>{counts["posted"]}</b><span>posted</span></div>
<div class="kpi"><b>{acct.get("followers_count", "–")}</b><span>followers</span></div>
<div class="kpi"><b>{len(inbox)}</b><span>comments to answer</span></div>
</section>
<div class="grid"><div><h2>Every reel, stage by stage</h2>{"".join(card(r) for r in sorted(rows, key=lambda r: ({"scheduled": 0, "draft": 1, "posted": 2, "made": 3}[status_of(r)[0]], (r.get("post") or {}).get("publish_at") or "")))}</div>
<aside><h2>Making{" now" if any(m["live"] for m in mk) else ""}</h2><div class="panel making">{mk_html}</div>
<h2>Setup</h2><div class="panel"><ul>{setup_rows}</ul></div>
<h2>Automation on GitHub</h2><div class="panel"><table>{wf_rows or "<tr><td class=muted>gh CLI not logged in</td></tr>"}</table>
<p><a href="https://github.com/{E(REPO)}/actions" target="_blank">All runs ↗</a></p></div>
<h2>Best time to post</h2><div class="panel">{('<p><b>' + E(' and '.join(best.get('slots_ist', []))) + ' IST</b></p><p class=muted>' + E(best.get('why', '')) + '</p>') if best else '<p class=muted>Not worked out yet (the make workflow does it).</p>'}</div>
<h2>Comments to answer</h2><div class="panel"><ul>{inbox_rows}</ul></div>
<h2>Activity</h2><div class="panel"><ol class="tl">{act_rows}</ol></div></aside></div>
</main></body></html>'''
    out = os.path.join(HERE, 'index.html')
    open(out, 'w', encoding='utf-8').write(page)
    print(f'dashboard: {out}  ({len(rows)} reels, {len(act)} activities)')
    if '--open' in sys.argv: webbrowser.open('file:///' + out.replace('\\', '/'))


if __name__ == '__main__':
    if '--watch' in sys.argv:                         # keep rebuilding; the open page reloads itself every minute
        import time
        first = True
        while True:
            try: main()
            except Exception as e: print('refresh failed:', e)
            if first and '--open' in sys.argv: sys.argv.remove('--open')
            first = False
            time.sleep(55)
    else:
        main()
