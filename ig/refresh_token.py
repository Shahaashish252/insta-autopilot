"""Only for the older Instagram-login method (IG_GRAPH=graph.instagram.com): a system-user token from Unified login
never expires and needs no refresh. Long-lived Instagram-login tokens last 60 days; refreshing one (it must be at least a day old) gives another 60.
  python -m ig.refresh_token   prints the new token to stdout (the workflow stores it back into the IG_ACCESS_TOKEN secret)"""
import sys
from . import api

if __name__ == '__main__':
    r = api._call('GET', 'https://graph.instagram.com/refresh_access_token', {'grant_type': 'ig_refresh_token', 'access_token': api.TOKEN})
    if not r.get('access_token'): sys.exit(f'refresh failed: {r}')
    print(r['access_token'])
    print(f'expires in {r.get("expires_in", 0) // 86400} days', file=sys.stderr)
