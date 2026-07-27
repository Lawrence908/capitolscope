"""
Tests for the security hardening in Phase 7a: an explicit CORS allowlist (no
wildcard-with-credentials) and the SecurityHeadersMiddleware.
"""

from types import SimpleNamespace

import pytest

import schemas  # noqa: F401  (resolve circular-import ordering)
from starlette.responses import Response

from api.middleware import SecurityHeadersMiddleware

pytestmark = pytest.mark.unit


class TestCorsAllowlist:
    def test_default_is_explicit_not_wildcard(self, make_settings):
        s = make_settings()
        assert "*" not in s.CORS_ORIGINS, "wildcard + credentials reflects any origin (unsafe)"
        assert "https://capitolscope.chrislawrence.ca" in s.CORS_ORIGINS
        assert "http://localhost:8121" in s.CORS_ORIGINS


def _mw() -> SecurityHeadersMiddleware:
    return SecurityHeadersMiddleware(app=lambda scope, receive, send: None)


def _req(path: str):
    return SimpleNamespace(url=SimpleNamespace(path=path))


class TestSecurityHeaders:
    @pytest.mark.asyncio
    async def test_headers_added_on_api_response(self):
        async def call_next(_req):
            return Response("{}", media_type="application/json")

        resp = await _mw().dispatch(_req("/api/v1/health"), call_next)
        assert resp.headers["X-Frame-Options"] == "DENY"
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert "max-age=" in resp.headers["Strict-Transport-Security"]
        assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "default-src 'none'" in resp.headers["Content-Security-Policy"]

    @pytest.mark.asyncio
    async def test_csp_skipped_on_docs_but_other_headers_stay(self):
        async def call_next(_req):
            return Response("<html></html>", media_type="text/html")

        resp = await _mw().dispatch(_req("/docs"), call_next)
        assert "Content-Security-Policy" not in resp.headers  # would break Swagger's CDN assets
        assert resp.headers["X-Frame-Options"] == "DENY"  # non-CSP headers still applied
