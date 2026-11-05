"""A small client for the official Instagram API (Instagram Login, graph.instagram.com). Standard library only.
Reads IG_ACCESS_TOKEN (a long-lived token) and IG_USER_ID from the environment; with DRY_RUN=1, or no token, every
call that would change something is printed instead of sent."""
import json, os, sys, time, urllib.error, urllib.parse, urllib.request

GRAPH = os.environ.get('IG_GRAPH', 'https://graph.instagram.com/v21.0')
TOKEN = os.environ.get('IG_ACCESS_TOKEN', '')
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
        try: msg = json.loads(body).get('error', {}).get('message', body)
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


def user_id():
    return os.environ.get('IG_USER_ID') or get('me', fields='user_id')['user_id']


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
    return post(f'{uid}/media_publish', creation_id=c['id']).get('id')


def publish_image_story(image_url):
    uid = user_id() if not DRY else 'ME'
    c = post(f'{uid}/media', media_type='STORIES', image_url=image_url)
    wait_ready(c['id'])
    return post(f'{uid}/media_publish', creation_id=c['id']).get('id')


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
    print(json.dumps(get('me', fields='user_id,username,account_type,media_count,followers_count'), indent=1))
