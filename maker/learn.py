"""Weekly: what to do more of and what to stop (the ig-audit and ig-viral methods, automated).
Reads the channel's own numbers (reports/insights.json + each reel's hook, length and post time) and the niche's outlier
reels (reports/viral.json), asks Claude, and writes:
  maker/learnings.md   what works on THIS channel (hooks, lengths, words, times) → read by every new reel
  maker/swipe.md       hook formulas working in the niche right now (formulas only, never anyone's words)
  python -m maker.learn"""
import json, os, statistics, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from maker.make import ai, jload  # noqa: E402
from maker.hookscore import score  # noqa: E402


def own_reels():
    meta = {}
    for d in ('posted', 'queue'):
        for n in os.listdir(os.path.join(ROOT, d)) if os.path.isdir(os.path.join(ROOT, d)) else []:
            m = jload(os.path.join(ROOT, d, n, 'post.json'), {}); sp = jload(os.path.join(ROOT, d, n, 'spec.json'), {})
            if m.get('media_id'):
                n1 = (sp.get('lines') or [{}])[0].get('text')
                meta[m['media_id']] = {'word': m.get('title'), 'hook_line': n1, 'hook_card': (sp.get('hook') or {}).get('text'),
                                       'hook_formula': m.get('hook_formula'), 'hook_score': score(n1)[0] if n1 else None,
                                       'seconds': m.get('duration'), 'posted_at': m.get('posted_at'), 'by_hand': m.get('posted_by') == 'hand'}
    rows = []
    for p in jload(os.path.join(ROOT, 'reports', 'insights.json'), {}).get('posts', []):
        i = p.get('insights') or {}
        if i.get('views') is None: continue
        r = {**meta.get(p['id'], {}), 'caption_start': (p.get('caption') or '')[:80], 'at': p.get('timestamp'), **i}
        if r.get('ig_reels_avg_watch_time') and r.get('seconds'): r['watched_share'] = round(r['ig_reels_avg_watch_time'] / 1000 / r['seconds'], 2)
        for k in ('shares', 'saved', 'comments', 'follows'):
            if i.get(k) is not None and i.get('views'): r[f'{k}_per_1000_views'] = round(1000 * i[k] / i['views'], 1)
        rows.append(r)
    if rows:
        med = statistics.median(r['views'] for r in rows) or 1
        for r in rows: r['views_vs_median'] = round(r['views'] / med, 2)
    return sorted(rows, key=lambda r: -(r.get('views_vs_median') or 0))


def main():
    mine, viral = own_reels(), jload(os.path.join(ROOT, 'reports', 'viral.json'), {})
    prompt = f"""You coach @anek.arthi, an Instagram channel of 25-40 s Hindi word-play reels (one letter or matra changes a
word into a life lesson: कल → काल, चिंता → चिता). Goal: more views, shares, saves and new followers.

## The channel's own reels (best first; views_vs_median = against the channel's own median; watched_share = average
watch time / length; *_per_1000_views = rates)
{json.dumps(mine, ensure_ascii=False, indent=1) if mine else 'No numbers yet (new channel).'}

## Reels that beat their own account by 2× or more in the niche this week (caption starts only)
{json.dumps([{k: r[k] for k in ('account', 'followers', 'multiple', 'caption')} for r in viral.get('outliers', [])][:30], ensure_ascii=False, indent=1) if viral.get('outliers') else 'None collected yet.'}

Write two short notes in plain English with Hindi examples where useful. Be honest about how little data there is: with
under 10 reels, say which patterns are only hints. Never invent numbers. Never copy anyone's words; name formulas.
1. "learnings": max 12 bullets for the next reels' writer: what to do MORE of on this channel (hook types, word themes,
   length, the ask, caption start), what to STOP, and one experiment to try next week (one variable only).
2. "swipe": max 10 bullets: the hook formulas behind the niche's outliers (name, the shape as a fill-in template in
   Hindi, why it travels), most promising first. If none were collected, write "No niche data yet." only.

Answer with ONLY this JSON: {{"learnings": "markdown bullets", "swipe": "markdown bullets"}}"""
    o = ai(prompt)
    head = '<!-- written weekly by maker/learn.py from reports/insights.json and reports/viral.json; read by every new reel -->\n'
    open(os.path.join(ROOT, 'maker', 'learnings.md'), 'w', encoding='utf-8').write(head + '# What works on this channel\n\n' + o['learnings'].strip() + '\n')
    open(os.path.join(ROOT, 'maker', 'swipe.md'), 'w', encoding='utf-8').write(head + '# Hook formulas working in the niche now\n\n' + o['swipe'].strip() + '\n')
    print(o['learnings']); print(o['swipe'])


if __name__ == '__main__':
    main()
