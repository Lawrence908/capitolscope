"""
Share pages (api.share) and card endpoints (api.og): meta injection, HTML
escaping of untrusted disclosure text, fallbacks, headers.

The DB loaders and the SPA index.html fetch are stubbed; no network or DB.
"""

import re
import uuid
from datetime import date

import pytest

import schemas  # noqa: F401  (resolve circular-import ordering)
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import og as og_api
from api import share as share_api
from api.middleware import SecurityHeadersMiddleware
from core.database import get_db_session
from domains.social.formatting import MemberCardData, TradeCardData
from domains.social.loader import AssetSummary, LoadedTrade

pytestmark = pytest.mark.unit

INDEX = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="Default description" />
    <meta property="og:title" content="Default OG title" />
    <meta property="og:image" content="https://example.test/api/v1/og/default.png" />
    <meta name="twitter:card" content="summary_large_image" />
    <title>Default title</title>
    <script defer src="/a/s.js" data-website-id="x"></script>
  </head>
  <body><div id="root"></div><script type="module" src="/js/index-abc.js"></script></body>
</html>
"""

EVIL = '"><script>alert(1)</script><img src=x onerror=alert(2)>'
TRADE_ID = uuid.UUID("41664389-385e-4527-ae62-5aaf5bb4830a")
MEMBER_ID = uuid.UUID("e657dbb1-8b20-4ee3-af52-ad60e4ba3459")


def _trade(**kw) -> TradeCardData:
    base = dict(
        member_name="John Boozman",
        chamber="Senate",
        party="R",
        state="AR",
        ticker="VEA",
        asset_name="Vanguard FTSE Developed Markets ETF",
        transaction_type="S",
        amount_min=100_100,
        amount_max=1_500_000,
        transaction_date=date(2025, 11, 21),
        notification_date=date(2026, 8, 24),
        filing_status="N",
    )
    base.update(kw)
    return TradeCardData(**base)


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://cs.example.test/")
    monkeypatch.setenv("OG_CACHE_DIR", str(tmp_path))

    async def fake_index():
        return INDEX

    state = {"trade": _trade(), "member": MemberCardData(name="John Boozman", chamber="Senate", party="R", state="AR", trade_count=109, avg_days=98.0, late_count=30)}

    async def fake_load_trade(session, tid):
        return LoadedTrade(card=state["trade"], member_id=str(MEMBER_ID)) if tid == TRADE_ID else None

    async def fake_load_member(session, mid):
        return state["member"] if mid == MEMBER_ID else None

    async def fake_load_asset(session, ticker):
        if ticker == "NVDA":
            return AssetSummary(ticker="NVDA", name=EVIL, trade_count=234, member_count=52, last_disclosed=date(2026, 9, 14))
        return None

    monkeypatch.setattr(share_api, "get_index_html", fake_index)
    for mod in (share_api, og_api):
        monkeypatch.setattr(mod, "load_trade", fake_load_trade)
        monkeypatch.setattr(mod, "load_member", fake_load_member)
    monkeypatch.setattr(share_api, "load_asset", fake_load_asset)

    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    app.include_router(share_api.router, prefix="/share")
    app.include_router(og_api.router, prefix="/api/v1/og")

    async def no_db():
        yield None

    app.dependency_overrides[get_db_session] = no_db
    c = TestClient(app)
    c.state = state
    return c


def _meta(doc: str, key: str) -> list:
    return re.findall(rf'<meta (?:name|property)="{re.escape(key)}" content="([^"]*)" />', doc)


class TestInjectMeta:
    def test_replaces_defaults_once_and_keeps_charset_first(self):
        meta = share_api.PageMeta(title="T", description="D", url="https://x/t/1", image="https://x/i.png", image_alt="A")
        doc = share_api.inject_meta(INDEX, meta)
        assert doc.count("<title>") == 1 and "<title>T</title>" in doc
        assert "Default" not in doc
        assert _meta(doc, "og:title") == ["T"]
        assert _meta(doc, "twitter:card") == ["summary_large_image"]
        assert doc.index('<meta charset="UTF-8" />') < doc.index("<title>T</title>")
        assert '<script type="module" src="/js/index-abc.js">' in doc and "/a/s.js" in doc

    def test_works_without_head_markup(self):
        meta = share_api.default_meta("/")
        assert "<title>" in share_api.inject_meta("<html><body></body></html>", meta)


class TestSharePages:
    def test_trade_page(self, client):
        r = client.get(f"/share/t/{TRADE_ID}")
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
        doc = r.text
        assert "<title>Sen. John Boozman (R-AR) sold VEA | CapitolScope</title>" in doc
        assert _meta(doc, "og:url") == [f"https://cs.example.test/t/{TRADE_ID}"]
        (img,) = _meta(doc, "og:image")
        assert img.startswith(f"https://cs.example.test/api/v1/og/trade/{TRADE_ID}.png?v=")
        assert _meta(doc, "twitter:image") == [img]
        assert _meta(doc, "og:type") == ["article"]
        assert _meta(doc, "og:image:height") == ["675"]
        assert f'<link rel="canonical" href="https://cs.example.test/t/{TRADE_ID}" />' in doc
        (desc,) = _meta(doc, "og:description")
        assert "$1,001 to $15,000" in desc and "276 days to disclose" in desc

    def test_spa_shell_headers_allow_scripts(self, client):
        r = client.get(f"/share/t/{TRADE_ID}")
        assert "content-security-policy" not in r.headers
        assert r.headers["x-frame-options"] == "SAMEORIGIN"
        assert r.headers["cache-control"] == "no-cache"

    def test_malicious_member_name_is_escaped(self, client):
        client.state["trade"] = _trade(member_name=EVIL, asset_name=EVIL, ticker=None)
        client.state["member"] = MemberCardData(name=EVIL, trade_count=1)
        for path in (f"/share/t/{TRADE_ID}", f"/share/members/{MEMBER_ID}", "/share/assets/NVDA"):
            doc = client.get(path).text
            assert "<script>alert(1)</script>" not in doc, path
            assert "<img src=x" not in doc, path
            assert "&lt;script&gt;alert(1)&lt;/script&gt;" in doc, path
            # Only the SPA's own two scripts remain.
            assert doc.count("<script") == 2, path

    def test_member_page(self, client):
        doc = client.get(f"/share/members/{MEMBER_ID}").text
        assert "<title>Sen. John Boozman, R-AR: stock trades | CapitolScope</title>" in doc
        assert _meta(doc, "og:type") == ["profile"]
        (img,) = _meta(doc, "og:image")
        assert f"/api/v1/og/member/{MEMBER_ID}.png?v=" in img
        assert "30 filings past the 45-day limit" in _meta(doc, "og:description")[0]

    def test_asset_page(self, client):
        doc = client.get("/share/assets/nvda").text
        assert "<title>NVDA: congressional trades | CapitolScope</title>" in doc
        assert _meta(doc, "og:url") == ["https://cs.example.test/assets/NVDA"]

    @pytest.mark.parametrize(
        "path",
        [
            "/share/t/not-a-uuid",
            f"/share/t/{uuid.uuid4()}",
            f"/share/members/{uuid.uuid4()}",
            "/share/members/compare",
            "/share/assets/ZZZZ",
            "/share/assets/%3Cb%3E",
        ],
    )
    def test_unknown_ids_get_default_shell(self, client, path):
        r = client.get(path)
        assert r.status_code == 200
        assert _meta(r.text, "og:image") == ["https://cs.example.test/api/v1/og/default.png"]
        assert "<b>" not in r.text

    def test_index_fetch_failure_uses_fallback(self, monkeypatch):
        import asyncio

        import httpx

        share_api._index.reset()

        class Boom:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def get(self, *a, **k):
                raise httpx.ConnectError("down")

        monkeypatch.setattr(share_api.httpx, "AsyncClient", Boom)
        html = asyncio.run(share_api.get_index_html())
        assert html == share_api.FALLBACK_INDEX
        share_api._index.reset()


class TestOgEndpoints:
    def test_trade_png(self, client):
        r = client.get(f"/api/v1/og/trade/{TRADE_ID}.png")
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/png"
        assert r.headers["cache-control"] == "public, max-age=86400"
        assert r.content[:8] == b"\x89PNG\r\n\x1a\n"
        r2 = client.get(f"/api/v1/og/trade/{TRADE_ID}.png", headers={"If-None-Match": r.headers["etag"]})
        assert r2.status_code == 304

    def test_member_and_default_png(self, client):
        assert client.get(f"/api/v1/og/member/{MEMBER_ID}.png").headers["content-type"] == "image/png"
        assert client.get("/api/v1/og/default.png").headers["content-type"] == "image/png"

    @pytest.mark.parametrize(
        "path",
        ["/api/v1/og/trade/not-a-uuid.png", f"/api/v1/og/trade/{uuid.uuid4()}.png", f"/api/v1/og/member/{uuid.uuid4()}.png"],
    )
    def test_unknown_or_invalid_ids_404(self, client, path):
        assert client.get(path).status_code == 404
