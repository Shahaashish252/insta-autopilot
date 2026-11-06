"""Read-only check of what the access token can see: who it is, its permissions, its Pages and Instagram accounts.
Prints names and ids only, never the token.   python -m ig.diagnose"""
from . import api


def show(label, path, **params):
    try:
        r = api.get(path, **params)
        print(f'OK   {label}: {r}')
        return r
    except api.IGError as e:
        print(f'FAIL {label}: {e}')
        return {}


if __name__ == '__main__':
    print('graph:', api.GRAPH, '| token type:', api.TOKEN[:2] + '…' if api.TOKEN else 'missing')
    show('me', 'me', fields='id,name')
    perms = show('permissions', 'me/permissions')
    granted = [p['permission'] for p in perms.get('data', []) if p.get('status') == 'granted']
    print('     granted:', ', '.join(granted) or 'none')
    show('pages', 'me/accounts', fields='name,instagram_business_account{id,username}')
    biz = show('businesses', 'me/businesses', fields='id,name')
    for b in biz.get('data', []):
        show(f'business {b.get("name")} owned pages', f'{b["id"]}/owned_pages', fields='name,instagram_business_account{id,username}')
        show(f'business {b.get("name")} instagram', f'{b["id"]}/owned_instagram_accounts', fields='id,username')
        show(f'business {b.get("name")} instagram (assigned)', f'{b["id"]}/instagram_accounts', fields='id,username')


def publish_check():
    """Can this token publish? Creates one unpublished container from a public test video (never published; it expires)."""
    uid = api.user_id()
    show('publishing limit', f'{uid}/content_publishing_limit', fields='config,quota_usage')
    try:
        r = api._call('POST', f'{api.GRAPH}/{uid}/media', {'media_type': 'REELS', 'upload_type': 'resumable', 'caption': 'test (not published)'})
        print('OK   can create a reel container:', r.get('id'))
    except api.IGError as e:
        print('FAIL create a reel container:', e)
    show('app', 'app', fields='id,name')


if __name__ == '__main__' and 'publish' in __import__('sys').argv:
    publish_check()
