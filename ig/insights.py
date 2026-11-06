"""Analytics: every post's numbers and the account's, saved for /ig-audit and as a readable report.
  python -m ig.insights   → reports/insights.json (all posts) and reports/latest.md (ranked table)
Metric names on the Instagram API change between versions; each is asked for on its own, and one the API refuses is skipped."""
import datetime as dt, json, os, statistics
from . import api

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'reports')
REEL = ['views', 'reach', 'likes', 'comments', 'shares', 'saved', 'total_interactions', 'ig_reels_avg_watch_time', 'ig_reels_video_view_total_time', 'follows', 'profile_visits']
POST = ['views', 'reach', 'likes', 'comments', 'shares', 'saved', 'total_interactions']


def metrics(mid, names):
    out = {}
    for n in names:
        try:
            for d in api.get(f'{mid}/insights', metric=n).get('data', []):
                v = d.get('values', [{}])[0].get('value', d.get('total_value', {}).get('value'))
                out[d['name']] = v
        except api.IGError:
            pass                                                    # not available for this post type or API version
    return out


def main(posts=50):
    uid = api.user_id()
    acct = api.account()
    rows = []
    for m in api.get(f'{uid}/media', fields='id,caption,media_type,media_product_type,permalink,timestamp,like_count,comments_count', limit=posts).get('data', []):
        reel = m.get('media_product_type') == 'REELS'
        rows.append({**m, 'caption': (m.get('caption') or '')[:80], 'insights': metrics(m['id'], REEL if reel else POST)})
    os.makedirs(OUT, exist_ok=True)
    try:                                                            # when followers are online, by hour (Pacific time);
        of = api.get(f'{uid}/insights', metric='online_followers', period='lifetime').get('data', [])  # needs ~100 followers
        online = (of[0].get('values') or [{}])[-1].get('value') or {} if of else {}
    except api.IGError:
        online = {}
    snap = {'at': dt.datetime.now(dt.timezone.utc).isoformat(), 'account': acct, 'online_followers': online, 'posts': rows}
    json.dump(snap, open(os.path.join(OUT, 'insights.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # ranked by views against the account's own median (an outlier multiple, as /ig-audit reads it)
    views = [r['insights'].get('views') or 0 for r in rows]
    med = statistics.median(views) if views else 0
    lines = [f'# @{acct.get("username")} · {acct.get("followers_count")} followers · {snap["at"][:10]}', '',
             f'Median views: {med:,.0f}', '', '| × median | views | reach | likes | shares | saves | posted | caption |', '|---|---|---|---|---|---|---|---|']
    for r in sorted(rows, key=lambda r: r['insights'].get('views') or 0, reverse=True):
        i = r['insights']; v = i.get('views') or 0
        lines.append(f'| {v / med:.1f} | {v:,} | {i.get("reach", "")} | {i.get("likes", r.get("like_count", ""))} | {i.get("shares", "")} | {i.get("saved", "")} | {r["timestamp"][:10]} | {r["caption"].replace("|", " ")[:50]} |' if med else
                     f'| – | {v:,} | {i.get("reach", "")} | {i.get("likes", "")} | {i.get("shares", "")} | {i.get("saved", "")} | {r["timestamp"][:10]} | {r["caption"][:50]} |')
    open(os.path.join(OUT, 'latest.md'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print(f'{len(rows)} posts → reports/insights.json, reports/latest.md')


if __name__ == '__main__':
    main()
