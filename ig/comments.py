"""Comments, in two steps so nothing is said without you:
  python -m ig.comments fetch   new comments on recent posts → comments/inbox.json (unanswered ones, newest first)
  python -m ig.comments reply   posts the replies in comments/replies.json marked "approved": true, then logs them
replies.json: [{"comment_id": "…", "reply": "…", "approved": true}]  (drafted by Claude with /ig-reply, approved by you)"""
import datetime as dt, json, os, sys
from . import api

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, 'comments')
load = lambda f, d: json.load(open(os.path.join(DIR, f), encoding='utf-8')) if os.path.isfile(os.path.join(DIR, f)) else d
save = lambda f, v: json.dump(v, open(os.path.join(DIR, f), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def fetch(posts=12):
    me = api.get('me', fields='username')['username']
    media = api.get(f'{api.user_id()}/media', fields='id,caption,permalink,timestamp,comments_count', limit=posts).get('data', [])
    answered = {r['comment_id'] for r in load('sent.json', [])}
    inbox = []
    for m in media:
        if not m.get('comments_count'): continue
        for c in api.paged(f'{m["id"]}/comments', fields='id,text,username,timestamp,replies{username}'):
            mine = any(r.get('username') == me for r in c.get('replies', {}).get('data', []))
            if c.get('username') == me or mine or c['id'] in answered: continue
            inbox.append({'comment_id': c['id'], 'from': c.get('username'), 'text': c.get('text'), 'at': c.get('timestamp'),
                          'post': (m.get('caption') or '')[:60], 'permalink': m.get('permalink')})
    inbox.sort(key=lambda c: c['at'] or '', reverse=True)
    save('inbox.json', inbox)
    print(f'{len(inbox)} comments waiting for a reply → comments/inbox.json')


def reply():
    todo, sent = load('replies.json', []), load('sent.json', [])
    left = []
    for r in todo:
        if not r.get('approved') or not r.get('reply'):
            left.append(r); continue
        rid = api.post(f'{r["comment_id"]}/replies', message=r['reply']).get('id')
        print(f'replied to {r["comment_id"]}: {r["reply"][:60]}')
        if not api.DRY: sent.append({**r, 'reply_id': rid, 'sent_at': dt.datetime.now(dt.timezone.utc).isoformat()})
        else: left.append(r)
    save('replies.json', left); save('sent.json', sent)


if __name__ == '__main__':
    {'fetch': fetch, 'reply': reply}.get(sys.argv[1] if len(sys.argv) > 1 else '', lambda: sys.exit(__doc__))()
