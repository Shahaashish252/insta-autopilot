# insta-autopilot

Runs an Instagram Professional account from GitHub, through Instagram's **official API** (no password, no bots):

| What | How | When |
|---|---|---|
| Post reels and stories | `queue/<name>/post.json` with `"approved": true` and a `publish_at` time | checked every 30 min |
| Comments | new unanswered comments → `comments/inbox.json`; approved replies in `comments/replies.json` are sent | every 6 h, and on every push of `replies.json` |
| Analytics | every post's views, reach, likes, shares, saves, watch time → `reports/` | daily |
| Token | the 60-day access token renews itself | weekly |

**Nothing is posted or replied unless it is marked `"approved": true`.** Claude prepares; you approve.

## Queue a reel

```
queue/sapna-apna/
  reel.mp4
  cover.jpg
  post.json   {"type": "reel", "file": "reel.mp4", "caption": "…", "publish_at": "2026-11-06T19:00:00+05:30",
               "approved": true, "share_to_feed": true}
```

`type` is `reel` or `story` (a story takes a video file, or an image with a public `image_url`). When it has posted, the
folder moves to `posted/` with its `media_id`. To post one right away: Actions → publish → Run workflow → the folder name.

## One-time setup (about 15 minutes)

1. **Instagram**: a Professional account (Creator or Business). *Settings → Account type and tools.*
2. **Meta app**: <https://developers.facebook.com/apps> → *Create app* → use case **"Manage messaging & content on Instagram"**.
   Meta asks for a **Business portfolio** (free: a name and an email; a brand-new Facebook account may have to wait an hour).
3. *Use cases → Customize → API setup with Unified login* → **Create new configuration**: pick your Instagram account,
   keep `instagram_basic`, `instagram_content_publish`, `instagram_manage_comments`, add `instagram_manage_insights` if offered.
   Redirect and login URLs are not needed.
4. **Generate token** (a system-user token: it does not expire) and save it in this repo as the secret **`IG_ACCESS_TOKEN`**:
   <https://github.com/Shahaashish252/insta-autopilot/settings/secrets/actions/new>.
   If the page shows the Instagram account's id, save it too as **`IG_USER_ID`** (otherwise it is found from the token).
5. Check it: Actions → insights → Run workflow. `reports/latest.md` appears with your posts.

You can revoke access at any time: remove the app in the Business portfolio settings, or delete the secret.
The older Instagram-login method (`IG_GRAPH=https://graph.instagram.com/v21.0`, 60-day tokens renewed by the
refresh-token workflow with a `GH_PAT` secret) is closed to new Meta apps; the code still supports it.

## Limits to know

- Instagram allows a limited number of API posts per 24 hours per account (currently 50 for feed posts); reels must be
  3–90 s long for the feed tab, 9:16, H.264/AAC, under 300 MB.
- The API cannot add trending audio, collab tags or music stickers; posts use the reel's own sound.
- Nothing can promise virality. The daily report shows which posts beat your own median, and that is what the next
  word and the posting time should follow.

## Local use

```
python -m ig.api                 # who am I (needs IG_ACCESS_TOKEN in the environment)
DRY_RUN=1 python -m ig.publish   # what would be posted now, without posting
python -m ig.insights            # pull the report locally
```
Standard-library Python only; no packages to install.
