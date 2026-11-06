"""What is working right now in the niche (the ig-viral method, automated with Meta's official Business Discovery API):
for each account in maker/watch.json, its recent reels are ranked by how far they beat that account's OWN median
(likes + 3 × comments; raw numbers are not evidence, the multiple is). Outliers ≥ 2× are kept → reports/viral.json.
maker/learn.py then turns them into maker/swipe.md (the hook formulas, never the words) for the reel writer.
Only public numbers of professional accounts; at most 15 accounts, run weekly.   python -m ig.viral"""
import datetime as dt, json, os, statistics
from . import api

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCH, OUT = os.path.join(ROOT, 'maker', 'watch.json'), os.path.join(ROOT, 'reports', 'viral.json')
FIELDS = 'business_discovery.username({u}){{username,followers_count,media_count,media.limit(30){{caption,like_count,comments_count,timestamp,media_product_type,permalink}}}}'


def main():
    accounts = [a.lstrip('@').strip() for a in json.load(open(WATCH, encoding='utf-8')).get('accounts', []) if a.strip()][:15]
    uid, found, failed, reels = api.user_id(), [], [], []
    for u in accounts:
        try:
            bd = api.get(uid, fields=FIELDS.format(u=u))['business_discovery']
        except (api.IGError, KeyError) as e:
            failed.append({'account': u, 'why': str(e)[:160]}); print(f'skip @{u}: {str(e)[:120]}'); continue
        media = [m for m in bd.get('media', {}).get('data', []) if m.get('media_product_type') == 'REELS' and m.get('like_count') is not None]
        if len(media) < 5: failed.append({'account': u, 'why': 'fewer than 5 reels with public likes'}); continue
        eng = lambda m: m.get('like_count', 0) + 3 * m.get('comments_count', 0)
        med = statistics.median(eng(m) for m in media) or 1
        found.append({'account': u, 'followers': bd.get('followers_count'), 'median': med, 'reels': len(media)})
        for m in media:
            reels.append({'account': u, 'followers': bd.get('followers_count'), 'multiple': round(eng(m) / med, 2),
                          'likes': m.get('like_count'), 'comments': m.get('comments_count'), 'at': m.get('timestamp'),
                          'caption': (m.get('caption') or '')[:300], 'permalink': m.get('permalink')})
        print(f'@{u}: {bd.get("followers_count")} followers, {len(media)} reels, median {med:.0f}')
    out = sorted([r for r in reels if r['multiple'] >= 2], key=lambda r: -r['multiple'])[:40]
    json.dump({'at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'), 'accounts': found, 'failed': failed, 'outliers': out},
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(out)} outlier reels (≥ 2× their account) from {len(found)} accounts; {len(failed)} accounts skipped')


if __name__ == '__main__':
    main()
