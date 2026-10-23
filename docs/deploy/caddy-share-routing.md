# Caddy: route share pages to the API (link previews)

Status: **proposed, not applied.** Apply to
`/mnt/storage/services/daedalus-infra/proxy/sites/capitolscope.caddy`.

## Why

The SPA is client-rendered, so X, Slack, iMessage, Facebook and Discord only
ever see the static `index.html` meta. The API now serves the same SPA
`index.html` with page-specific `<title>`, description, `og:*`, `twitter:*`
and canonical tags at:

| Public URL | Rewritten to (API) | Card image |
|---|---|---|
| `GET /t/{trade_id}` | `/share/t/{trade_id}` | `/api/v1/og/trade/{trade_id}.png` (1200x675) |
| `GET /members/{member_id}` | `/share/members/{member_id}` | `/api/v1/og/member/{member_id}.png` (1200x630) |
| `GET /assets/{ticker}` | `/share/assets/{ticker}` | `/api/v1/og/default.png` (1200x630) |

Everything else (the bare `/members` list, `/members/{id}/...`, `/js/*`,
`/css/*`, Vite's hashed `/assets/*.woff2` etc.) keeps going to the frontend
container. Humans and crawlers get the same document (no user-agent
sniffing), so the SPA boots normally from the share response. Unknown or
malformed ids return the SPA shell with the default meta (status 200), so
the SPA renders its own not-found.

The `/share/*` responses carry no `Content-Security-Policy` (the API's
`default-src 'none'` would block the SPA) and `X-Frame-Options: SAMEORIGIN`,
matching the frontend's nginx. `Cache-Control: no-cache`, as nginx does for
`index.html`, so a deploy's new bundle hashes are picked up at once. The API
caches the fetched `index.html` in memory for 120 s and revalidates it with
its ETag (`CAPITOLSCOPE_SHARE_INDEX_TTL`).

## The change

Add the `@share` matcher and `handle @share` block **between** the existing
`handle @api` and the catch-all `handle` (handle blocks with named matchers
run in file order, and the catch-all must stay last):

```caddy
# CapitolScope
capitolscope.chrislawrence.ca:80 {
    import umami
    import shared_footer
    @api path_regexp ^/api/.*

    handle @api {
        # CORS is handled by the FastAPI app (origin-aware + supports
        # credentials). Do NOT set Access-Control-* here or the headers get
        # duplicated ("*, <origin>") and browsers reject the response.
        reverse_proxy capitolscope:8000 {
            header_up X-Real-IP {remote}
        }
    }

    # Link previews: trade permalinks, member profiles and asset pages get a
    # server-rendered copy of the SPA shell with page-specific og/twitter
    # meta (app/src/api/share.py). One path segment only, so the bare
    # /members list and deeper SPA routes are untouched; file-like paths
    # (Vite's hashed /assets/*.woff2 etc.) still go to the frontend.
    @share {
        method GET HEAD
        path_regexp share ^/(t|members|assets)/[^/]+$
        not path_regexp share_static (?i)\.(js|mjs|css|map|json|txt|xml|ico|png|jpe?g|gif|svg|webp|avif|woff2?|ttf|otf|eot)$
    }
    handle @share {
        rewrite * /share{path}
        reverse_proxy capitolscope:8000 {
            header_up X-Real-IP {remote}
        }
    }

    handle {
        reverse_proxy capitolscope-frontend:5173 {
            header_up X-Real-IP {remote}
        }
    }

    log {
        level INFO
        format json
        output file /data/logs/capitolscope.json {
            roll_size 15mb
            roll_keep 8
            roll_keep_for 168h
        }
    }
}
```

Notes:

- `rewrite * /share{path}` keeps the original query string (Caddy preserves
  it when the target has no `?`).
- The regex has no trailing-slash variant on purpose: `/t/{id}/` would be
  rewritten to `/share/t/{id}/` and FastAPI would answer with a redirect to
  `/share/...`, leaking the internal path. Trailing-slash URLs simply fall
  through to the SPA (default meta).
- Tickers containing dots (`BRK.B`) still match: only the listed static
  extensions are excluded.
- `/share/*` is not exposed publicly as its own path: requests for
  `/share/...` hit the catch-all and get the SPA (which has no such route).

## Apply

```bash
cd /mnt/storage/services/daedalus-infra/proxy
cp sites/capitolscope.caddy sites/capitolscope.caddy.bak-$(date +%F)
# edit sites/capitolscope.caddy as above, then:
docker exec caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
docker exec caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
```

(Container name and config path as used by the proxy stack's `compose.yaml`;
adjust if they differ.) Rollback: restore the `.bak` file and reload.

Prerequisite: the API image containing `api/og.py`, `api/share.py`, the fonts
under `app/src/assets/fonts/` and Pillow must be deployed first, otherwise
`/share/...` 404s and `/t/{id}` would show a JSON error.

## Test

```bash
BASE=https://capitolscope.chrislawrence.ca
TRADE=41664389-385e-4527-ae62-5aaf5bb4830a     # a late Senate filing
MEMBER=e657dbb1-8b20-4ee3-af52-ad60e4ba3459

# 1. Crawlers see page-specific meta
curl -s -A Twitterbot "$BASE/t/$TRADE" | grep -E '<title>|og:(title|description|image)"|twitter:card'
curl -s -A Slackbot-LinkExpanding "$BASE/members/$MEMBER" | grep -E '<title>|og:image"'
curl -s -A facebookexternalhit "$BASE/assets/NVDA" | grep -E '<title>|og:description"'

# 2. The card images resolve, are PNG, and are cacheable
curl -sI "$BASE/api/v1/og/trade/$TRADE.png" | grep -iE '^(HTTP|content-type|cache-control)'
curl -sI "$BASE/api/v1/og/default.png" | grep -iE '^(HTTP|content-type)'

# 3. Humans still get a working SPA from the same response
curl -sI "$BASE/t/$TRADE" | grep -iE '^(HTTP|content-type|content-security-policy|x-frame-options)'
#    expect 200, text/html, NO content-security-policy, x-frame-options SAMEORIGIN
curl -s "$BASE/t/$TRADE" | grep -o '/js/index-[^"]*\.js'     # bundle referenced
curl -sI "$BASE$(curl -s "$BASE/t/$TRADE" | grep -o '/js/index-[^"]*\.js' | head -1)" | head -1   # 200

# 4. Everything else is untouched
curl -s "$BASE/members" | grep -c 'og:image" content="https://capitolscope.chrislawrence.ca/api/v1/og/default.png'   # 1 (static default)
curl -s -o /dev/null -w '%{http_code}\n' -A Twitterbot "$BASE/t/not-a-real-id"   # 200, default meta

# 5. Validators
#    https://cards-dev.twitter.com/validator is retired; post the URL in a
#    private X draft or DM to preview. Facebook: https://developers.facebook.com/tools/debug/
#    Slack/Discord: paste the link in a private channel.
```
