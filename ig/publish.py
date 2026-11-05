"""Post whatever in queue/ is approved and due. Each queue item is a folder with post.json:
  {"type": "reel" | "story", "file": "reel.mp4", "caption": "…", "publish_at": "2026-11-06T19:00:00+05:30",
   "approved": true, "share_to_feed": true}
Nothing without "approved": true is ever posted. A posted item moves to posted/ with the media id and the time.
usage: python -m ig.publish [--now <item>]   (--now posts one approved item immediately)"""
import datetime as dt, json, os, shutil, sys
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


def post_one(name, folder, meta):
    path = os.path.join(folder, meta['file'])
    if not os.path.isfile(path): raise api.IGError(f'{name}: {meta["file"]} is missing')
    kind = {'reel': 'REELS', 'story': 'STORIES'}[meta.get('type', 'reel')]
    if kind == 'STORIES' and path.lower().endswith(('.jpg', '.jpeg', '.png')):
        mid = api.publish_image_story(meta['image_url'])           # image stories need a public URL
    else:
        mid = api.publish_video(kind, path, meta.get('caption', ''), meta.get('share_to_feed', True))
    print(f'posted {name} as {kind}: media {mid}')
    if api.DRY: return
    meta.update(media_id=mid, posted_at=dt.datetime.now(dt.timezone.utc).isoformat())
    json.dump(meta, open(os.path.join(folder, 'post.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    shutil.move(folder, os.path.join(POSTED, name))


def main():
    now = dt.datetime.now(dt.timezone.utc)
    only = sys.argv[sys.argv.index('--now') + 1] if '--now' in sys.argv else None
    done = 0
    for name, folder, meta in items():
        if only and name != only: continue
        if not meta.get('approved'):
            print(f'skip {name}: not approved'); continue
        if not only and not due(meta, now):
            print(f'wait {name}: due {meta.get("publish_at") or "(no time set)"}'); continue
        post_one(name, folder, meta); done += 1
    print(f'{done} posted{" (dry run)" if api.DRY else ""}')


if __name__ == '__main__':
    main()
