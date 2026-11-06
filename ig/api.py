"""A small client for the official Instagram API, Unified login (Facebook Login for Business, graph.facebook.com), with
a system-user token that does not expire. Standard library only.
Reads IG_ACCESS_TOKEN and IG_USER_ID (the Instagram professional account's id; found automatically when not set) from
the environment; with DRY_RUN=1, or no token, every call that would change something is printed instead of sent.
IG_GRAPH=https://graph.instagram.com/v21.0 switches to the older Instagram-login method."""
import json, os, sys, time, urllib.error, urllib.parse, urllib.request

TOKEN = os.environ.get('IG_ACCESS_TOKEN', '').strip()
# the token says which API it belongs to: Instagram-login tokens start with "IG", Facebook/Unified-login ones with "EA"
GRAPH = os.environ.get('IG_GRAPH') or ('https://graph.instagram.com/v21.0' if TOKEN.startswith('IG') else 'https://graph.facebook.com/v21.0')
DRY = os.environ.get('DRY_RUN', '0') == '1' or not TOKEN


class IGError(RuntimeError):
    pass


def _call(method, url, params=None, data=None, headers=None, timeout=120):
    params = dict(params or {})
    if TOKEN and 'access_token' not in params and not (headers or {}).get('Authorization'):
        params['access_token'] = TOKEN
    full = url + ('?' + urllib.parse.urlencode(params) if params else '')
    req = urllib.request.Request(full, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', 'replace')
        try:
            er = json.loads(body).get('error', {})
            msg = er.get('message', body) + ''.join(f' | {k}={er[k]}' for k in ('type', 'code', 'error_subcode', 'error_user_title', 'error_user_msg', 'fbtrace_id') if er.get(k))
        except ValueError: msg = body
        raise IGError(f'{method} {url.split("?")[0]} → {e.code}: {msg}') from None
    return json.loads(body) if body else {}


def get(path, **params):
    if not TOKEN:
        raise IGError('IG_ACCESS_TOKEN is not set (add it as a GitHub secret; see README)')
    return _call('GET', f'{GRAPH}/{path}', params)


def post(path, **params):
    if DRY:
        print(f'[dry run] POST {path} {json.dumps({k: v for k, v in params.items() if k != "access_token"}, ensure_ascii=False)[:300]}')
        return {'id': 'DRY_RUN'}
    return _call('POST', f'{GRAPH}/{path}', params)


_UID = None
def user_id():
    """The Instagram account's id: IG_USER_ID, else found through the token's Pages or business assets."""
    global _UID
    if _UID: return _UID
    _UID = os.environ.get('IG_USER_ID')
    if _UID: return _UID
    if 'graph.instagram.com' in GRAPH: _UID = get('me', fields='user_id')['user_id']; return _UID
    tries = [('me/accounts', {'fields': 'instagram_business_account{id,username}'}),
             ('me/businesses', {'fields': 'owned_instagram_accounts{id,username},instagram_accounts{id,username}'})]
    for path, params in tries:
        try: data = get(path, **params).get('data', [])
        except IGError: continue
        for d in data:
            for k in ('instagram_business_account',):
                if d.get(k): _UID = d[k]['id']; return _UID
            for k in ('owned_instagram_accounts', 'instagram_accounts'):
                for a in d.get(k, {}).get('data', []): _UID = a['id']; return _UID
    raise IGError('could not find the Instagram account id: add it as the IG_USER_ID secret')


def account(fields='username,followers_count,follows_count,media_count'):
    return get(user_id(), fields=fields)


def wait_ready(container, tries=60, every=10):
    """Poll a media container until Instagram has processed the video (FINISHED) or failed."""
    if DRY: return 'FINISHED'
    for _ in range(tries):
        s = get(container, fields='status_code,status').get('status_code')
        if s == 'FINISHED': return s
        if s in ('ERROR', 'EXPIRED'): raise IGError(f'container {container}: {s}')
        time.sleep(every)
    raise IGError(f'container {container} not ready after {tries * every} s')


def upload_video(container_uri, path):
    """Resumable upload of a local video to the uri a container returned (no public URL needed)."""
    size = os.path.getsize(path)
    if DRY:
        print(f'[dry run] upload {path} ({size / 1e6:.1f} MB) → {container_uri[:60]}…'); return
    with open(path, 'rb') as f:
        data = f.read()
    _call('POST', container_uri, data=data, headers={'Authorization': f'OAuth {TOKEN}', 'offset': '0', 'file_size': str(size)}, timeout=600)


def publish_video(kind, path, caption='', share_to_feed=True):
    """kind: 'REELS' or 'STORIES'. Creates a container, uploads the file, waits, publishes. Returns the media id."""
    uid = user_id() if not DRY else 'ME'
    params = {'media_type': kind, 'upload_type': 'resumable'}
    if kind == 'REELS':
        params.update(caption=caption, share_to_feed='true' if share_to_feed else 'false')
    c = post(f'{uid}/media', **params)
    upload_video(c.get('uri', 'DRY_RUN'), path)
    wait_ready(c['id'])
    return publish_container(uid, c['id'])


def publish_container(uid, cid, tries=6, every=45):
    """media_publish, retried: Meta often answers "internal error, try again later" right after processing. Before each
    retry the container is checked, so a publish that went through despite the error is never repeated."""
    if DRY: return post(f'{uid}/media_publish', creation_id=cid).get('id')
    for i in range(tries):
        try:
            return post(f'{uid}/media_publish', creation_id=cid).get('id')
        except IGError as e:
            if i == tries - 1 or not any(k in str(e) for k in ('try again', 'code=-1', 'code=2 ', 'code=1 ', 'Internal', 'Fatal', '9007')): raise
            print(f'publish attempt {i + 1} failed ({str(e)[:90]}); checking and retrying in {every} s')
            time.sleep(every)
            if get(cid, fields='status_code').get('status_code') == 'PUBLISHED':
                for m in get(f'{uid}/media', fields='id', limit=1).get('data', []): return m['id']


def publish_image_story(image_url):
    uid = user_id() if not DRY else 'ME'
    c = post(f'{uid}/media', media_type='STORIES', image_url=image_url)
    wait_ready(c['id'])
    return publish_container(uid, c['id'])


def paged(path, **params):
    """Every item of a paged edge."""
    out, page = [], get(path, **params)
    while True:
        out += page.get('data', [])
        nxt = page.get('paging', {}).get('next')
        if not nxt: return out
        page = _call('GET', nxt)


if __name__ == '__main__':
    if not TOKEN: sys.exit('set IG_ACCESS_TOKEN first')
    print('instagram account id:', user_id()); print(json.dumps(account(), indent=1, ensure_ascii=False))
