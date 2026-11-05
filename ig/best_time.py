"""When to post: picks the two daily slots (IST) from the channel's own data, and the next free one for a new reel.
  python -m ig.best_time        → reports/best_time.json and a short explanation

The slots are the times the publish workflow wakes up (keep CANDIDATES and its cron in step). Evidence, best first:
 1. online_followers: when the followers are on Instagram (Meta reports it once the account has about 100 followers).
 2. the reels already posted: views against the account's own median, by the slot they went out in.
 3. nothing yet: test every slot in turn (the least-tried first), so 2 above fills in quickly.
With 2 reels a day, one slot is the best one found so far and the other keeps testing (explore/exploit)."""
import datetime as dt, json, os, statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT, OUT = os.path.join(ROOT, 'reports', 'insights.json'), os.path.join(ROOT, 'reports', 'best_time.json')
IST = dt.timezone(dt.timedelta(hours=5, minutes=30), 'IST')   # India has no daylight saving
CANDIDATES = ['08:00', '12:30', '17:00', '19:00', '21:00']     # IST; publish.yml wakes at exactly these
PRIOR = ['19:00', '12:30', '21:00', '17:00', '08:00']          # the usual Indian evening/lunch peaks, used to break ties
try:                                                            # online_followers hours are reported in Pacific time
    from zoneinfo import ZoneInfo; OF_TZ = ZoneInfo('America/Los_Angeles')
except Exception:                                               # (Windows without tzdata: standard time is close enough)
    OF_TZ = dt.timezone(dt.timedelta(hours=-8))
PER_DAY = int(os.environ.get('POSTS_PER_DAY', '2'))


def _mins(hhmm): h, m = map(int, hhmm.split(':')); return h * 60 + m


def nearest(t_ist):
    m = t_ist.hour * 60 + t_ist.minute
    return min(CANDIDATES, key=lambda c: min(abs(_mins(c) - m), 1440 - abs(_mins(c) - m)))


def online_scores(snap):
    """{slot: followers online in that hour}, from online_followers (empty below ~100 followers)."""
    of = (snap or {}).get('online_followers') or {}
    if not of or not any(of.values()): return {}
    day = dt.datetime.now(OF_TZ).date()
    out = {}
    for h, n in of.items():
        t = dt.datetime.combine(day, dt.time(int(h)), OF_TZ).astimezone(IST)
        for c in CANDIDATES:
            if t.hour == _mins(c) // 60: out[c] = out.get(c, 0) + (n or 0)
    return out


def post_scores(snap):
    """{slot: [views ÷ median, …]} for the account's reels."""
    posts = [p for p in (snap or {}).get('posts', []) if (p.get('insights') or {}).get('views') is not None]
    if not posts: return {}
    med = statistics.median([p['insights']['views'] for p in posts]) or 1
    out = {}
    for p in posts:
        t = dt.datetime.fromisoformat(p['timestamp'].replace('+0000', '+00:00')).astimezone(IST)
        out.setdefault(nearest(t), []).append(p['insights']['views'] / med)
    return out


def choose(snap=None):
    if snap is None:
        snap = json.load(open(REPORT, encoding='utf-8')) if os.path.isfile(REPORT) else {}
    online, perf = online_scores(snap), post_scores(snap)
    tried = {c: len(perf.get(c, [])) for c in CANDIDATES}
    if online:
        rank = sorted(CANDIDATES, key=lambda c: -online.get(c, 0))
        why = 'when your followers are online (Instagram\'s online_followers)'
        slots = rank[:PER_DAY]
    else:
        proven = {c: statistics.mean(v) for c, v in perf.items() if len(v) >= 2}
        if proven:
            best = max(proven, key=proven.get)
            explore = sorted((c for c in CANDIDATES if c != best), key=lambda c: (tried[c], PRIOR.index(c)))
            slots = [best] + explore[:PER_DAY - 1]
            why = f'{best} IST has done best so far ({proven[best]:.1f}× your median views); the other slot keeps testing'
        else:
            slots = sorted(CANDIDATES, key=lambda c: (tried[c], PRIOR.index(c)))[:PER_DAY]
            why = 'not enough posts yet to compare times: testing each slot in turn (least tried first)'
    slots = sorted(slots, key=_mins)
    res = {'at': dt.datetime.now(dt.timezone.utc).isoformat(), 'slots_ist': slots, 'why': why,
           'tried': tried, 'performance': {c: round(statistics.mean(v), 2) for c, v in perf.items()},
           'online_followers': online}
    return res


def taken():
    """publish_at times already used by queue items."""
    q = os.path.join(ROOT, 'queue'); out = set()
    for n in os.listdir(q) if os.path.isdir(q) else []:
        p = os.path.join(q, n, 'post.json')
        if os.path.isfile(p):
            t = json.load(open(p, encoding='utf-8')).get('publish_at')
            if t and t != 'auto': out.add(dt.datetime.fromisoformat(t).astimezone(IST).replace(second=0, microsecond=0))
    return out


def next_slot(slots=None, lead_min=40, used=None):
    """The first chosen slot at least lead_min from now that no queue item has."""
    slots = slots or choose()['slots_ist']
    used = taken() if used is None else used
    now = dt.datetime.now(IST)
    for d in range(0, 30):
        day = (now + dt.timedelta(days=d)).date()
        for s in slots:
            t = dt.datetime.combine(day, dt.time(*map(int, s.split(':'))), IST)
            if t >= now + dt.timedelta(minutes=lead_min) and t not in used: return t
    raise RuntimeError('no free slot in 30 days')


def assign_auto():
    """Give every queue item with "publish_at": "auto" the next free slot (oldest folder first)."""
    q = os.path.join(ROOT, 'queue'); slots = choose()['slots_ist']; used = taken(); n = 0
    for name in sorted(os.listdir(q)):
        p = os.path.join(q, name, 'post.json')
        if not os.path.isfile(p): continue
        meta = json.load(open(p, encoding='utf-8'))
        if meta.get('publish_at') != 'auto': continue
        t = next_slot(slots, used=used); used.add(t)
        meta['publish_at'] = t.isoformat(); n += 1
        json.dump(meta, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'{name}: {t:%a %d %b %H:%M} IST')
    return n


if __name__ == '__main__':
    r = choose()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(r, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"slots: {', '.join(r['slots_ist'])} IST ({r['why']})")
    assign_auto()
