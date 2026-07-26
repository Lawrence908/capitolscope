# CapitolScope Signals API

A machine-facing feed of congressional-trading intelligence for external systems
(Project Canary OSINT ingestion, Zeus reference/MCP, and any other client). Built
on public STOCK Act disclosures. Oriented at two jobs: **stock selection** and
**event-linked research**.

All figures are disclosed-range midpoints. These are signals and leads for
research, not investment advice or accusations.

## Base URL and auth

- Base: `https://capitolscope.chrislawrence.ca` (public, via Caddy) or
  `http://localhost:8120` on the daedalus host.
- Prefix: `/api/v1/signals`
- Every request MUST send the shared key in the `X-API-Key` header.
  - Missing / wrong key: `401`
  - Server has no key configured (`SIGNALS_API_KEY` unset): `503`
- The key lives in `/mnt/storage/apps/capitolscope/.env` as `SIGNALS_API_KEY`
  (gitignored). Retrieve it with:
  `grep SIGNALS_API_KEY /mnt/storage/apps/capitolscope/.env`

Example:

```bash
KEY=$(grep '^SIGNALS_API_KEY=' /mnt/storage/apps/capitolscope/.env | cut -d= -f2)
curl -s -H "X-API-Key: $KEY" \
  "https://capitolscope.chrislawrence.ca/api/v1/signals/digest?days=7" | jq .
```

## Response shape

Every response is `{"data": {...}, "meta": {...}}`. The `data` object carries a
`generated_at` ISO timestamp and the payload. Entities are typed with a `type`
field (`member` / `ticker` / `sector` / `trade`) so a consumer can route them
into its own entity model.

Heavy computes are cached 15 minutes in-process. The one expensive endpoint
(`/leaderboard`) is computed once and kept warm by a background loop, so callers
never hit a cold 60-second compute.

## Endpoints

| Endpoint | Purpose | Key params |
|----------|---------|-----------|
| `GET /digest` | One-call research brief: active tickers, notable recent trades, sector flow, herding clusters, most-active members. Best single call for a daily digest. | `days` (1-90, default 7) |
| `GET /active-tickers` | Tickers ranked by recent activity: members, buy/sell split, `net_direction` (accumulating/distributing), notional. What Congress is buying vs selling. | `days` (default 90), `limit` |
| `GET /recent-trades` | Filterable trade feed with sector and 30d return. | `days`, `ticker`, `party`, `direction` (buy/sell), `min_amount`, `limit` |
| `GET /sector-flow` | Net congressional dollar flow by GICS sector (rotation signal). | `days` (default 90) |
| `GET /clusters` | Recent herding events (N members, same ticker + side, 14-day window), notability-ranked. | `days` (default 30), `limit` |
| `GET /leaderboard` | Compact composite Scrutiny Score per member (six-factor). | `limit` |

Field notes:

- `return_30d` / `avg_return_30d` are **direction-aware** (a well-timed sale
  precedes a drop, so its signed return is positive).
- `net_direction` on a ticker: `accumulating` (more buys), `distributing`
  (more sells), or `mixed`.
- `flow` on a sector: `inflow` / `outflow` / `flat` by net notional.
- `notability_score` on a cluster is base-popularity-weighted (a herd on an
  obscure name outranks the same headcount on a megacap everyone holds).

## Consumer: Zeus (live)

Zeus has five MCP tools that wrap these endpoints (`~/zeus/zeus/mcp/tools.py`,
registered in `server.py`):

- `capitolscope_digest(days=7)`
- `capitolscope_active_tickers(days=90, limit=25)`
- `capitolscope_ticker(ticker, days=180, limit=60)` (uses `/recent-trades?ticker=`)
- `capitolscope_sector_flow(days=90)`
- `capitolscope_leaderboard(limit=20)`

Setup: the Zeus MCP server loads `.env` (via `load_dotenv()` in
`zeus/mcp/server.py`), which must define:

```
CAPITOLSCOPE_SIGNALS_URL=https://capitolscope.chrislawrence.ca
CAPITOLSCOPE_SIGNALS_KEY=<the SIGNALS_API_KEY value>
```

Each tool returns the unwrapped `data` dict, or `{"error": ...}` on failure so
agents degrade gracefully.

## Consumer: Project Canary (registration + fetcher)

Canary is an OSINT platform that ingests from a `Source` registry
(`app/models/source.py`) graded on the NATO admiralty scale.

### 1. Register the source

CapitolScope is a **primary source** (official STOCK Act disclosures), so grade
it reliability `A`. Information credibility is `2` (structured and derived from
primary documents, but not independently multi-source confirmed at the item
level). Add to `canary/scripts/seed_sources.py` `DEFAULT_SOURCES`, or insert
directly:

```python
{
    "name": "CapitolScope Congressional Trading Signals",
    "source_type": "api",
    "url": "https://capitolscope.chrislawrence.ca/api/v1/signals/digest",
    "reliability_grade": "A",   # official public disclosures (primary)
    "default_info_grade": "2",  # structured / derived from primary docs
    "language": "en",
    "fetch_interval_mins": 720, # twice daily; data updates slowly (disclosure lag)
}
```

### 2. Provide the key to canary

The `Source` model has no header/secret field, so the fetcher reads the key from
canary's own environment. Add to `canary/.env`:

```
CAPITOLSCOPE_SIGNALS_KEY=<the SIGNALS_API_KEY value>
```

### 3. Build the fetcher (canary side)

Canary's existing fetchers are type-specific (`rss_fetcher`, `newsapi_fetcher`,
`gdelt_fetcher` under `app/services/ingestion/`); there is no generic `api`
fetcher yet. A `capitolscope_fetcher` should:

1. `GET /digest` (and optionally `/active-tickers`, `/clusters`) with the
   `X-API-Key` header.
2. Emit **entities**: each `member` -> person entity; each `ticker` /
   `security_name` -> organization entity; each `sector` -> topic entity.
3. Emit **articles** (canary's unit of collected content) from notable items:
   one per cluster ("N members bought TICKER") and per high-notional trade, with
   a BLUF summary and the source `url` back to the ticker/member.
4. Carry the source's `reliability_grade`/`default_info_grade` onto the produced
   items so downstream correlation and reporting inherit the grading.

Because the payload is already structured JSON with typed entities, the fetcher
is a thin mapping layer, not an NLP-extraction job.

## Operational notes

- Rate: gentle. The 15-minute cache means repeated polls are cheap; a
  `fetch_interval_mins` of 12+ hours is plenty given disclosure lag.
- Disclaimer: the `/digest` payload includes a `note` field restating that this
  is public-disclosure signal data for research, not investment advice.
- Underlying engines and data model: see the analytics domain
  (`app/src/domains/analytics/`) and `docs` on the scrutiny score.
