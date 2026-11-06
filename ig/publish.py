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
        mid = api.publish_video(kind, path, meta.get('caption', ''), meta.get('share_to_feed', True))
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


def reslot(name, folder, meta):
    from . import best_time
    t = best_time.next_slot()
    print(f'{name}: missed {meta["publish_at"]} by over {LATE_H} h -> moved to {t:%a %d %b %H:%M} IST')
    meta['publish_at'] = t.isoformat()
    json.dump(meta, open(os.path.join(folder, 'post.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def main():
    now = dt.datetime.now(dt.timezone.utc)
    only = sys.argv[sys.argv.index('--now') + 1] if '--now' in sys.argv else None
    done, live = 0, None
    for name, folder, meta in items():
        if only and name != only: continue
        if not meta.get('approved'):
            print(f'skip {name}: not approved'); continue
        if not only and not due(meta, now):
            print(f'wait {name}: due {meta.get("publish_at") or "(no time set)"}'); continue
        if live is None: live = {} if api.DRY else on_instagram()
        if key(meta.get('caption')) in live:
            if not api.DRY: mark_posted(name, folder, meta, live[key(meta.get('caption'))])
            continue
        if not only and (done or now - dt.datetime.fromisoformat(meta['publish_at']) > dt.timedelta(hours=LATE_H)):
            reslot(name, folder, meta); continue                    # one reel per run, and never hours late
        post_one(name, folder, meta); done += 1
    print(f'{done} posted{" (dry run)" if api.DRY else ""}')


if __name__ == '__main__':
    main()
