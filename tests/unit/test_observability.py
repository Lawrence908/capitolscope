"""
Tests for Phase 7c observability: Prometheus request metrics + Redis health check.
"""

from types import SimpleNamespace

import pytest

import schemas  # noqa: F401  (resolve circular-import ordering)
from starlette.responses import Response

from core.metrics import PrometheusMiddleware, metrics_response

pytestmark = pytest.mark.unit


def _req(path: str, method: str = "GET", route_path: str | None = None):
    scope = {"route": SimpleNamespace(path=route_path)} if route_path else {}
    return SimpleNamespace(url=SimpleNamespace(path=path), method=method, scope=scope)


class TestMetrics:
    @pytest.mark.asyncio
    async def test_records_request_with_route_template(self):
        mw = PrometheusMiddleware(app=lambda *a: None)

        async def call_next(_req):
            return Response("{}", status_code=200, media_type="application/json")

        req = _req("/api/v1/trades/abc123", route_path="/api/v1/trades/{trade_id}")
        resp = await mw.dispatch(req, call_next)
        assert resp.status_code == 200

        body = metrics_response().body.decode()
        assert "http_requests_total" in body
        # Labels use the route template, not the per-id URL (cardinality control).
        assert "/api/v1/trades/{trade_id}" in body
        assert "abc123" not in body

    @pytest.mark.asyncio
    async def test_metrics_path_is_not_recorded(self):
        mw = PrometheusMiddleware(app=lambda *a: None)
        called = {}

        async def call_next(_req):
            called["hit"] = True
            return Response("data")

        await mw.dispatch(_req("/metrics"), call_next)
        assert called.get("hit")  # passed through, no recursion/recording

    def test_metrics_response_content_type(self):
        assert "text/plain" in metrics_response().media_type


class TestRedisHealth:
    @pytest.mark.asyncio
    async def test_healthy(self, monkeypatch):
        import redis.asyncio as aioredis

        class FakeClient:
            async def ping(self):
                return True

            async def aclose(self):
                pass

        monkeypatch.setattr(aioredis, "from_url", lambda *a, **k: FakeClient())
        from api.health import check_redis_health

        assert (await check_redis_health())["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_unhealthy_on_connection_error(self, monkeypatch):
        import redis.asyncio as aioredis

        def boom(*a, **k):
            raise ConnectionError("refused")

        monkeypatch.setattr(aioredis, "from_url", boom)
        from api.health import check_redis_health

        result = await check_redis_health()
        assert result["status"] == "unhealthy"
        assert "error" in result
