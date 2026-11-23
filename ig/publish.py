"""Post whatever in queue/ is approved and due. Each queue item is a folder with post.json:
  {"type": "reel" | "story", "file": "reel.mp4", "caption": "…", "publish_at": "2026-11-06T19:00:00+05:30",
   "approved": true, "share_to_feed": true}
Nothing without "approved": true is ever posted. A posted item moves to posted/ with the media id and the time.
Reels made on GitHub keep their video out of git: "asset": "<file>" names a file on the repo's "media" release, which is
downloaded when it is due (the release keeps it, for the dashboard's player).
usage: python -m ig.publish [--now <item>]   (--now posts one approved item immediately)"""
import datetime as dt, json, os, shutil, subprocess, sys
from . import api

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE, POSTED = os.path.join(ROOT, 'queue'), os.path.join(ROOT, 'posted')


def items():
    if not os.path.isdir(QUEUE): return
    for name in sorted(os.listdir(QUEUE)):
        p = os.path.join(QUEUE, name, 'post.json')
        if os.path.isfile(p):
            yield name, os.path.join(QUEUE, name), json.load(open(p, encoding='utf-8'))


def due(meta, now):
    t = meta.get('publish_at')
    return bool(t) and dt.datetime.fromisoformat(t) <= now


def fetch_asset(folder, meta):
    """Download the reel's video from the "media" release (made on GitHub; not kept in git)."""
    path = os.path.join(folder, meta['asset'])
    if not os.path.isfile(path):
        subprocess.run(['gh', 'release', 'download', 'media', '--pattern', meta['asset'], '--dir', folder, '--clobber'], check=True)
    return path


def post_one(name, folder, meta):
    path = fetch_asset(folder, meta) if meta.get('asset') else os.path.join(folder, meta['file'])
    if not os.path.isfile(path): raise api.IGError(f'{name}: {meta.get("file")} is missing')
    kind = {'reel': 'REELS', 'story': 'STORIES'}[meta.get('type', 'reel')]
    if kind == 'STORIES' and path.lower().endswith(('.jpg', '.jpeg', '.png')):
        mid = api.publish_image_story(meta['image_url'])           # image stories need a public URL
    else:
        try: mid = api.publish_video(kind, path, meta.get('caption', ''), meta.get('share_to_feed', True))
        except Exception:
            if meta.get('asset') and os.path.isfile(path): os.remove(path)   # the release keeps it; never commit the video
            raise
    print(f'posted {name} as {kind}: media {mid}')
    if api.DRY: return
    meta.update(media_id=mid, posted_at=dt.datetime.now(dt.timezone.utc).isoformat())
    if meta.get('asset'): os.remove(path)                          # (the release keeps it: the dashboard plays it from there)
    json.dump(meta, open(os.path.join(folder, 'post.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    shutil.move(folder, os.path.join(POSTED, name))


LATE_H = 2      # a reel more than this late (GitHub skipped a run, Meta was down) moves to the next good slot
key = lambda c: ' '.join((c or '').split())[:60]


def on_instagram():
    """Captions of the account's recent posts -> media, so a reel you already posted by hand is never posted twice."""
    try:
        media = api.get(f'{api.user_id()}/media', fields='id,caption,timestamp', limit=30).get('data', [])
    except api.IGError as e:
        print('could not read recent posts:', e); raise
    return {key(m.get('caption')): m for m in media if m.get('caption')}


def mark_posted(name, folder, meta, m):
    meta.update(media_id=m['id'], posted_at=m.get('timestamp'), posted_by='hand')
    json.dump(meta, open(os.path.join(folder, 'post.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    shutil.move(folder, os.path.join(POSTED, name))
    print(f'{name}: already on Instagram (media {m["id"]}), marked as posted')
    if meta.get('auto_failed'): close_issue(name, m['id'])


OWNER = os.environ.get('GITHUB_REPOSITORY', 'Shahaashish252/insta-autopilot').split('/')[0]
SITE = os.environ.get('DASHBOARD_URL', f'https://{OWNER.lower()}.github.io/insta-autopilot/')


def gh(*args):
    try: return subprocess.run(['gh', *args], capture_output=True, text=True, encoding='utf-8', timeout=60)
    except (OSError, subprocess.SubprocessError) as e: print('gh failed:', e)


def hand_over(name, folder, meta, err):
    """The automatic try failed: stop trying, mark it for posting by hand, and email the owner (a GitHub issue)."""
    print(f'{name}: automatic posting failed ({str(err)[:160]}); handed over for posting by hand')
    meta.update(manual=True, auto_failed=dt.datetime.now(dt.timezone.utc).isoformat(), auto_error=str(err)[:300])
    json.dump(meta, open(os.path.join(folder, 'post.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    title = f'Post by hand: {meta.get("title", name)} ({name})'
    when = dt.datetime.fromisoformat(meta['publish_at']).astimezone(dt.timezone(dt.timedelta(hours=5, minutes=45)))
    nl = chr(10)
    body = nl.join([
        f'@{OWNER} Instagram refused the automatic post for **{meta.get("title", name)}** '
        f'(due {when:%a %d %b, %I:%M %p} Nepal time). GitHub will not try again.', '',
        f'**Post it by hand:** open the dashboard → Reels → {meta.get("title", name)} → **📤 Post** → **📋 Post by hand**',
        SITE, '',
        'First check your profile: if it is already there, do nothing. This issue closes by itself once the reel is on Instagram.', '',
        "<details><summary>Meta's answer</summary>", '', '```', str(err)[:600], '```', '</details>'])
    r = gh('issue', 'create', '--title', title, '--body', body)
    print('emailed you (GitHub issue):', (r.stdout or r.stderr).strip() if r else 'gh missing')


def close_issue(name, mid):
    r = gh('issue', 'list', '--state', 'open', '--search', f'{name} in:title', '--json', 'number,title')
    for i in json.loads(r.stdout or '[]') if r and r.returncode == 0 else []:
        if f'({name})' in i['title']:
            gh('issue', 'close', str(i['number']), '--comment', f'Posted ✓ (media {mid}).')


def reslot(name, folder, meta):
    from . import best_time
    t = best_time.next_slot()
    print(f'{name}: missed {meta["publish_at"]} by over {LATE_H} h -> moved to {t:%a %d %b %H:%M} IST')
    meta['publish_at'] = t.isoformat()
    json.dump(meta, open(os.path.join(folder, 'post.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def seconds_to_next():
    """Seconds until the next approved reel is due (0 if one is due now), or -1 if nothing is waiting."""
    now = dt.datetime.now(dt.timezone.utc)
    ts = [dt.datetime.fromisoformat(m['publish_at']) for _, _, m in items() if m.get('approved') and m.get('publish_at') and not m.get('manual')]   # hand-post reels never wake the poster (a past one made it loop)
    return max(0, int((min(ts) - now).total_seconds())) if ts else -1


def main():
    if '--next' in sys.argv: print(seconds_to_next()); return
    now = dt.datetime.now(dt.timezone.utc)
    only = sys.argv[sys.argv.index('--now') + 1] if '--now' in sys.argv else None
    done, live = 0, None
    for name, folder, meta in items():
        if only and name != only: continue
        if not meta.get('approved'):
            print(f'skip {name}: not approved'); continue
        if meta.get('manual') and not only:              # you post it (dashboard: Post by hand); once it is live, record it
            if due(meta, now):
                if live is None: live = {} if api.DRY else on_instagram()
                m = live.get(key(meta.get('caption')))
                if m and not api.DRY: mark_posted(name, folder, meta, m); continue
            print(f'skip {name}: you post this one by hand'); continue
        if not only and not due(meta, now):
            print(f'wait {name}: due {meta.get("publish_at") or "(no time set)"}'); continue
        if live is None: live = {} if api.DRY else on_instagram()
        if key(meta.get('caption')) in live:
            if not api.DRY: mark_posted(name, folder, meta, live[key(meta.get('caption'))])
            continue
        if not only and (done or now - dt.datetime.fromisoformat(meta['publish_at']) > dt.timedelta(hours=LATE_H)):
            reslot(name, folder, meta); continue                    # one reel per run, and never hours late
        try:
            post_one(name, folder, meta); done += 1
        except Exception as e:                                       # one try only: Meta flags repeated attempts
            if api.DRY or only: raise
            hand_over(name, folder, meta, e)
    print(f'{done} posted{" (dry run)" if api.DRY else ""}')


if __name__ == '__main__':
    main()
