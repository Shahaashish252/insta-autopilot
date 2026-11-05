"""Comments on the channel's posts.
  python -m ig.comments auto      new comments → Claude decides each (reply / hide / hold) → replies sent, spam hidden,
                                  sensitive ones held for you (comments/held.json). The comments workflow runs this.
  python -m ig.comments fetch     only collect unanswered comments → comments/inbox.json
  python -m ig.comments reply     send the replies in comments/replies.json marked "approved": true (your own replies)
  python -m ig.comments test "<comment text>" [reel title]    show what Claude would do, sends nothing
Logs: comments/sent.json (every reply sent), comments/hidden.json, comments/held.json (waiting for you)."""
import datetime as dt, json, os, re, shutil, subprocess, sys, tempfile
from . import api

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, 'comments')
MAX_PER_RUN = int(os.environ.get('MAX_REPLIES', '40'))
load = lambda f, d: json.load(open(os.path.join(DIR, f), encoding='utf-8')) if os.path.isfile(os.path.join(DIR, f)) else d
save = lambda f, v: json.dump(v, open(os.path.join(DIR, f), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
now = lambda: dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')


def fetch(posts=15, write=True):
    me = api.account('username')['username']
    media = api.get(f'{api.user_id()}/media', fields='id,caption,permalink,timestamp,comments_count', limit=posts).get('data', [])
    done = {r['comment_id'] for f in ('sent.json', 'hidden.json', 'held.json') for r in load(f, [])}
    titles = {}
    for where in ('queue', 'posted'):                                  # the reel's word (e.g. सब्र → सब), for context
        d = os.path.join(ROOT, where)
        for n in os.listdir(d) if os.path.isdir(d) else []:
            m = json.load(open(os.path.join(d, n, 'post.json'), encoding='utf-8')) if os.path.isfile(os.path.join(d, n, 'post.json')) else {}
            if m.get('media_id'): titles[m['media_id']] = m.get('title')
    inbox = []
    for m in media:
        if not m.get('comments_count'): continue
        for c in api.paged(f'{m["id"]}/comments', fields='id,text,username,timestamp,replies{username}'):
            mine = any(r.get('username') == me for r in c.get('replies', {}).get('data', []))
            if c.get('username') == me or mine or c['id'] in done: continue
            inbox.append({'comment_id': c['id'], 'from': c.get('username'), 'text': c.get('text'), 'at': c.get('timestamp'),
                          'reel': titles.get(m['id']) or '', 'post': (m.get('caption') or '')[:160], 'permalink': m.get('permalink')})
    inbox.sort(key=lambda c: c['at'] or '')
    if write: save('inbox.json', inbox)
    print(f'{len(inbox)} new comments')
    return inbox


# ───────── Claude decides
BRIEF = """You answer comments on @anek.arthi, an Instagram channel of short Hindi word-play reels (शब्द-चित्र): one Hindi word
changes by one letter or matra and becomes a life lesson (सब्र → सब, चिंता → चिता, कल → काल). The audience is young Hindi
speakers in India. You speak as the channel: warm, humble, brief, like an elder sibling, never salesy.

For EACH comment choose one action:
- "reply": almost every genuine comment. 1 short sentence (max ~20 words), in the commenter's own language and script
  (Hindi → Devanagari Hindi; Hinglish in Latin letters → Hinglish; English → simple English). Be specific to what they
  said or to the reel's word; vary the wording, never a template. At most one emoji, often none. If they suggest a word,
  thank them and say you'll try it. If they ask a question about the word or lesson, answer it in one line. If they
  disagree politely, acknowledge their view kindly. No links, no hashtags, no "follow us", no asking for shares, no
  promises, no personal data, no medical/legal/money advice. Never mention being an AI or automated.
- "hide": spam, scams, links/promotions, sexual content, hate, slurs, harassment or abuse. No reply.
- "hold": anything a human should answer: someone in distress (sadness, hopelessness, self-harm, grief), a complaint
  about the channel, a business or collab offer, a question about personal details, legal/medical/money matters,
  religion or politics arguments, or when you are unsure. No reply.

Answer with ONLY a JSON array, one object per comment, same order:
[{"comment_id": "...", "action": "reply|hide|hold", "reply": "the reply text (only for reply)", "why": "3-8 words"}]"""


def ai(prompt, model='sonnet'):
    cli = shutil.which('claude')
    if not cli: raise RuntimeError('claude CLI not found')
    env = {k: v for k, v in os.environ.items() if not k.startswith('ANTHROPIC_') and not k.startswith('CLAUDE_CODE_USE_')}
    r = subprocess.run([cli, '-p', '--model', model, '--output-format', 'text', '--tools', '', '--safe-mode'], input=prompt, text=True,
                       encoding='utf-8', capture_output=True, cwd=tempfile.gettempdir(), env=env, timeout=600)
    if r.returncode: raise RuntimeError(f'claude failed: {(r.stderr or r.stdout)[:300]}')
    out = r.stdout; a, b = out.find('['), out.rfind(']')
    return json.loads(out[a:b + 1])


def decide(batch):
    items = [{'comment_id': c['comment_id'], 'from': c.get('from'), 'comment': c.get('text'), 'reel': c.get('reel'),
              'reel_caption': (c.get('post') or '')[:160]} for c in batch]
    out = ai(BRIEF + '\n\nThe comments:\n' + json.dumps(items, ensure_ascii=False, indent=1))
    by = {d.get('comment_id'): d for d in out if isinstance(d, dict)}
    res = []
    for c in batch:
        d = by.get(c['comment_id']) or {'action': 'hold', 'why': 'no decision returned'}
        act, rep = d.get('action'), (d.get('reply') or '').strip()
        # last guard before anything is said in public
        if act == 'reply' and (not rep or len(rep) > 220 or re.search(r'https?://|www\.|#|@\w', rep)): act, d['why'] = 'hold', 'reply failed the safety check'
        if act not in ('reply', 'hide', 'hold'): act = 'hold'
        res.append({**c, 'action': act, 'reply': rep if act == 'reply' else '', 'why': d.get('why', '')})
    return res


def auto():
    inbox = fetch(write=False)
    if not inbox: save('inbox.json', []); return
    sent, hidden, held = load('sent.json', []), load('hidden.json', []), load('held.json', [])
    todo = inbox[:MAX_PER_RUN]
    for i in range(0, len(todo), 15):                                   # 15 comments per Claude call
        for d in decide(todo[i:i + 15]):
            try:
                if d['action'] == 'reply':
                    rid = api.post(f'{d["comment_id"]}/replies', message=d['reply']).get('id')
                    sent.append({**d, 'reply_id': rid, 'sent_at': now(), 'by': 'auto'})
                    print(f'replied to @{d["from"]}: {d["text"][:50]!r} → {d["reply"]!r}')
                elif d['action'] == 'hide':
                    api.post(d['comment_id'], hide='true')
                    hidden.append({**d, 'hidden_at': now()}); print(f'hid @{d["from"]}: {d["text"][:50]!r} ({d["why"]})')
                else:
                    held.append({**d, 'held_at': now()}); print(f'held for you: @{d["from"]}: {d["text"][:50]!r} ({d["why"]})')
            except api.IGError as e:
                print(f'could not act on {d["comment_id"]}: {e}')
    if api.DRY: return
    save('sent.json', sent); save('hidden.json', hidden); save('held.json', held)
    save('inbox.json', inbox[MAX_PER_RUN:])                             # anything over the cap: next run


def reply():
    """Your own replies: comments/replies.json entries with "approved": true (e.g. to the held ones)."""
    todo, sent, held = load('replies.json', []), load('sent.json', []), load('held.json', [])
    left = []
    for r in todo:
        if not r.get('approved') or not r.get('reply'):
            left.append(r); continue
        rid = api.post(f'{r["comment_id"]}/replies', message=r['reply']).get('id')
        print(f'replied to {r["comment_id"]}: {r["reply"][:60]}')
        if not api.DRY:
            sent.append({**r, 'reply_id': rid, 'sent_at': now(), 'by': 'you'})
            held = [h for h in held if h['comment_id'] != r['comment_id']]
        else: left.append(r)
    save('replies.json', left); save('sent.json', sent); save('held.json', held)


def test():
    text = sys.argv[2]; reel = sys.argv[3] if len(sys.argv) > 3 else 'सब्र → सब'
    for d in decide([{'comment_id': 't1', 'from': 'someone', 'text': text, 'reel': reel, 'post': ''}]):
        print(json.dumps({k: d[k] for k in ('action', 'reply', 'why')}, ensure_ascii=False))


if __name__ == '__main__':
    {'auto': auto, 'fetch': fetch, 'reply': reply, 'test': test}.get(sys.argv[1] if len(sys.argv) > 1 else '', lambda: sys.exit(__doc__))()
