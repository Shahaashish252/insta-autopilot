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
    if (r.get('post') or {}).get('held'): return 'draft', 'On hold'
    if r.get('post'): return 'draft', 'Needs approval' if s[2][1] else 'Needs caption'
    return 'made', 'Not queued'


# ───────── the page: Python gathers everything into DATA; the browser draws it (and keeps the live parts live)
def md(text):
    """The few bits of markdown the weekly notes use: bullets, headings, **bold**, `code`."""
    import re
    out, inlist = [], False
    for line in (text or '').split('-->', 1)[-1].splitlines():
        line = line.rstrip()
        if not line.strip() or line.startswith('# '):
            continue
        t = E(re.sub(r'^\s*[-*]\s+', '', line).strip())
        t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t); t = re.sub(r'`(.+?)`', r'<code>\1</code>', t)
        if re.match(r'^\s*[-*] ', line):
            if not inlist: out.append('<ul>'); inlist = True
            out.append(f'<li>{t}</li>')
        else:
            if inlist: out.append('</ul>'); inlist = False
            out.append(f'<p>{t}</p>')
    if inlist: out.append('</ul>')
    return ''.join(out)


def data():
    rows, ins = reels()
    runs = json.loads(gh('run', 'list', '-R', REPO, '--limit', '60', '--json', 'workflowName,status,conclusion,createdAt,event,url') or '[]')
    wfs = [l.split('\t') for l in gh('workflow', 'list', '-R', REPO, '--all').splitlines() if l.strip()]
    sent = jload(os.path.join(ROOT, 'comments', 'sent.json'), []) or []
    acct = ins.get('account', {}) or {}
    best = jload(os.path.join(ROOT, 'reports', 'best_time.json'), {}) or {}
    viral = jload(os.path.join(ROOT, 'reports', 'viral.json'), {}) or {}
    watch = (jload(os.path.join(ROOT, 'maker', 'watch.json'), {}) or {}).get('accounts', [])
    note = lambda f: md(open(os.path.join(ROOT, 'maker', f), encoding='utf-8').read()) if os.path.isfile(os.path.join(ROOT, 'maker', f)) else ''

    out = []
    for r in rows:
        k, label = status_of(r); p = r.get('post') or {}; i = ((r.get('ins') or {}).get('insights') or {})
        folder = os.path.join(ROOT, r.get('where') or 'queue', r['name'])
        spec = jload(os.path.join(folder, 'spec.json'), {}) or {}
        out.append({'name': r['name'], 'title': r['title'], 'status': k, 'label': label, 'style': r.get('style'), 'dur': r.get('dur'),
                    'cover': r.get('cover'), 'video': r.get('video'), 'made': r['made'].isoformat() if r.get('made') else None,
                    'publish_at': p.get('publish_at'), 'posted_at': p.get('posted_at'), 'by_hand': p.get('posted_by') == 'hand',
                    'permalink': (r.get('ins') or {}).get('permalink'), 'caption': p.get('caption'),
                    'stages': [[n, ok, note_] for n, ok, note_ in stages(r)],
                    'hook_line': ((spec.get('lines') or [{}])[0]).get('text'), 'hook_card': (spec.get('hook') or {}).get('text'),
                    'hook_formula': p.get('hook_formula'), 'hook_score': p.get('hook_score'), 'hooks': p.get('hooks') or [],
                    'ins': {k2: i.get(k2) for k2 in ('views', 'reach', 'likes', 'comments', 'shares', 'saved', 'follows', 'ig_reels_avg_watch_time')}})
    last = {}
    for run in runs: last.setdefault(run['workflowName'], run)
    workflows = [{'name': w[0], 'state': w[1], 'last': last.get(w[0])} for w in wfs if len(w) > 1]

    act = []
    for r in out:
        if r['made']: act.append({'at': r['made'], 'kind': 'made', 'title': f'Reel made · {r["title"]}', 'sub': f'{r["dur"]:.0f} s' if r.get('dur') else ''})
        if r['posted_at']: act.append({'at': r['posted_at'], 'kind': 'posted', 'title': f'Posted · {r["title"]}', 'sub': 'by hand' if r['by_hand'] else 'by GitHub'})
    for run in runs[:40]:
        act.append({'at': run['createdAt'], 'kind': 'run' if run.get('conclusion') in ('success', None) else 'fail',
                    'title': run['workflowName'], 'sub': f'{run.get("conclusion") or run.get("status")} · {run.get("event")}', 'url': run.get('url')})
    for c in sent[-20:]:
        act.append({'at': c['sent_at'], 'kind': 'reply', 'title': f'Replied to @{c.get("from")}', 'sub': (c.get('reply') or '')[:70]})
    act.sort(key=lambda a: a['at'] or '', reverse=True)

    return {'repo': REPO, 'updated': dt.datetime.now(IST).isoformat(), 'local': not SITE,
            'account': {k: acct.get(k) for k in ('username', 'followers_count', 'follows_count', 'media_count')},
            'best': {'slots': best.get('slots_ist', []), 'why': best.get('why', '')},
            'reels': out, 'workflows': workflows, 'activity': act[:60],
            'learnings': note('learnings.md'), 'swipe': note('swipe.md'),
            'watch': {'accounts': watch, 'ok': viral.get('accounts', []), 'failed': viral.get('failed', []), 'at': viral.get('at'),
                      'outliers': len(viral.get('outliers', []))}}


FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans+Devanagari:wght@400;600;700&display=swap" rel="stylesheet">')
ASSETS = os.path.join(HERE, 'assets')


def page(title, view, d):
    css = open(os.path.join(ASSETS, 'app.css'), encoding='utf-8').read()
    js = open(os.path.join(ASSETS, 'app.js'), encoding='utf-8').read()
    blob = json.dumps(d, ensure_ascii=False).replace('</', '<\\/')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{E(title)}</title><meta name="theme-color" content="#0f1015"><link rel="icon" href="data:image/svg+xml,{ICON_SVG}"><link rel="apple-touch-icon" href="{'icon.png' if SITE else 'assets/icon.png'}"><meta name="apple-mobile-web-app-title" content="Anek Arthi">{FONTS}<style>{css}</style>
<script>try{{const t=localStorage.getItem('theme');if(t)document.documentElement.dataset.theme=t}}catch(e){{}}</script></head>
<body data-view="{view}"><div id="app"></div><script>const DATA={blob};const RELOAD={60000 if '--watch' in sys.argv else 300000};</script><script>{js}</script></body></html>'''


ICON_SVG = ("%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Cdefs%3E%3ClinearGradient id='g' x1='0' y1='0' x2='1' y2='1'%3E"
            "%3Cstop offset='0' stop-color='%23ff8a3d'/%3E%3Cstop offset='1' stop-color='%23d6336c'/%3E%3C/linearGradient%3E%3C/defs%3E"
            "%3Crect width='64' height='64' rx='16' fill='url(%23g)'/%3E%3Ctext x='32' y='45' font-size='36' text-anchor='middle' fill='white' "
            "font-family='sans-serif' font-weight='700'%3E%E0%A4%85%3C/text%3E%3C/svg%3E")


def main():
    if not SITE: subprocess.run(['git', '-C', ROOT, 'pull', '-q', '--ff-only'], capture_output=True, timeout=60)
    os.makedirs(OUT, exist_ok=True)
    d = data()
    open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(page('Anek Arthi Studio', 'home', d))
    open(os.path.join(OUT, 'making.html'), 'w', encoding='utf-8').write(page('Making · Anek Arthi Studio', 'making', d))
    if SITE: open(os.path.join(OUT, '.nojekyll'), 'w').close(); shutil.copyfile(os.path.join(ASSETS, 'icon.png'), os.path.join(OUT, 'icon.png'))
    print(f'dashboard: {OUT}  ({len(d["reels"])} reels, {sum(1 for r in d["reels"] if r["video"])} playable, {len(d["activity"])} activities)')
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
