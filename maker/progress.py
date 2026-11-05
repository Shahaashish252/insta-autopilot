"""Live progress of the reel being made, for the dashboard: progress.json on the repo's "status" branch (written through
the GitHub API, so it never collides with main). The dashboard page reads it every 30 s while a make is running.
  python -m maker.progress start                      a new make begins (the workflow's first step)
  python -m maker.progress <stage> <state> [detail]   e.g. setup done "ffmpeg, renderer, Claude Code"
  python -m maker.progress finish <done|failed|skipped> [detail]
Outside GitHub Actions (no GITHUB_REPOSITORY/GH_TOKEN) it only prints."""
import base64, datetime as dt, json, os, sys, time, urllib.error, urllib.request

REPO, TOKEN = os.environ.get('GITHUB_REPOSITORY'), os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
BRANCH, PATH = 'status', 'progress.json'
STAGES = [('setup', 'Set up the studio', 'ffmpeg, the renderer, Claude Code'),
          ('numbers', 'Channel numbers and best time', 'fresh views, the posting slot'),
          ('write', 'Claude writes the reel', 'picks a new word, the hook, the script and the caption; checked against the rules'),
          ('voice', 'Voice', 'every line spoken by hi-IN-SwaraNeural'),
          ('speech', 'Speech check', 'Whisper listens back to every line'),
          ('timing', 'Timing', 'when each word, matra and pencil stroke happens'),
          ('music', 'Music and sound', 'guitar, bass, pencil, whooshes; mixed under the voice'),
          ('reading', 'Reading check', 'every written line long enough on screen to read'),
          ('picture', 'Picture', '1080×1920, 30 fps, frame by frame'),
          ('master', 'Master, subtitles, cover', 'loudness −14 LUFS, Hindi .srt, cover frame'),
          ('upload', 'Upload', 'the video to the media release'),
          ('queued', 'Scheduled', 'queued at the next best time')]
_state, _sha, _last = None, None, 0.0


def now(): return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')


def _api(method, url, body=None):
    req = urllib.request.Request(f'https://api.github.com/repos/{REPO}/{url}', method=method, data=json.dumps(body).encode() if body else None,
                                 headers={'Authorization': f'Bearer {TOKEN}', 'Accept': 'application/vnd.github+json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        if e.code == 404: return None
        raise


def _load():
    global _state, _sha
    if _state is not None: return _state
    _state = {}
    if REPO and TOKEN:
        try:
            r = _api('GET', f'contents/{PATH}?ref={BRANCH}')
            if r: _sha = r['sha']; _state = json.loads(base64.b64decode(r['content']))
        except Exception as e: print('[progress] read failed:', e)
    return _state


def _save(force=False):
    global _sha, _last
    s = _load(); s['updated'] = now()
    if not (REPO and TOKEN): return
    if not force and time.time() - _last < 15: return                # picture % updates: at most every 15 s
    try:
        if _api('GET', f'git/ref/heads/{BRANCH}') is None:          # first time: the branch, from main
            main = _api('GET', 'git/ref/heads/main')['object']['sha']
            _api('POST', 'git/refs', {'ref': f'refs/heads/{BRANCH}', 'sha': main})
        body = {'message': f"progress: {s.get('status')} {s.get('word') or ''}".strip(), 'branch': BRANCH,
                'content': base64.b64encode(json.dumps(s, ensure_ascii=False, indent=1).encode()).decode()}
        if _sha: body['sha'] = _sha
        _sha = _api('PUT', f'contents/{PATH}', body)['content']['sha']; _last = time.time()
    except Exception as e:                                            # usually a stale sha: refresh it for the next write
        print('[progress] write failed:', e)
        try: r = _api('GET', f'contents/{PATH}?ref={BRANCH}'); _sha = r['sha'] if r else None
        except Exception: _sha = None


def start():
    s = _load()
    hist = s.get('history', [])
    if s.get('run_id') and s.get('status'):                          # the previous make goes into the history
        hist = [{k: s.get(k) for k in ('run_id', 'run_url', 'started', 'updated', 'status', 'word', 'hook', 'publish_at', 'detail', 'took')}] + \
               [h for h in hist if h.get('run_id') != s.get('run_id')]
    run = os.environ.get('GITHUB_RUN_ID')
    s.clear(); s.update(run_id=run, run_url=f"https://github.com/{REPO}/actions/runs/{run}" if run else '', started=now(), status='running',
                        stages=[{'key': k, 'label': l, 'about': a, 'state': 'waiting'} for k, l, a in STAGES], history=hist[:15])
    stage('setup', 'running')


def stage(key, state, detail=None, force=None):
    s = _load()
    for st in s.get('stages', []):
        if st['key'] != key: continue
        if state == 'running' and st['state'] != 'running': st['started'] = now()
        if state in ('done', 'failed', 'skipped'): st['ended'] = now(); st.setdefault('started', st['ended'])
        changed = st['state'] != state; st['state'] = state
        if detail is not None: st['detail'] = detail
        print(f'[progress] {key}: {state}{" · " + detail if detail else ""}')
        _save(force=changed if force is None else force)
        return


def info(**kw):
    _load().update(kw); _save(force=True)


def finish(status, detail=''):
    s = _load()
    for st in s.get('stages', []):
        if st['state'] == 'running': st['state'] = 'failed' if status == 'failed' else 'done'; st['ended'] = now()
        elif st['state'] == 'waiting' and status != 'done': st['state'] = 'skipped'
    s.update(status=status, detail=detail, ended=now())
    try: s['took'] = (dt.datetime.fromisoformat(s['ended']) - dt.datetime.fromisoformat(s['started'])).total_seconds()
    except (KeyError, ValueError): pass
    print(f'[progress] finished: {status} {detail}'); _save(force=True)


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    if a[0] == 'start': start()
    elif a[0] == 'finish': finish(a[1], ' '.join(a[2:]))
    elif a[0] == 'fail':                                              # the workflow's failure() step: only if still running
        if _load().get('status') == 'running': finish('failed', ' '.join(a[1:]) or 'see the run log')
    else: stage(a[0], a[1], ' '.join(a[2:]) or None)
