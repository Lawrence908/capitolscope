"""
Prometheus metrics (Phase 7c observability).

Exposes HTTP request counts and latency at ``/metrics`` (plus prometheus_client's
default process/GC collectors). Labels use the matched ROUTE TEMPLATE
(``/api/v1/trades/{trade_id}``), not the raw path, so per-id URLs don't blow up
cardinality.
"""

import time

from prometheus_client import Counter, Histogram, CONTENT_TYPE_LATEST, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "path", "status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency (s)", ["method", "path"]
)


def _route_template(request: Request) -> str:
    """The matched route template, or a coarse fallback (keeps label cardinality bounded)."""
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if path:
        return path
    # No route matched (404s, etc.) — bucket them rather than emit the raw URL.
    return "unmatched"


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Don't recurse on the scrape endpoint itself.
        if request.url.path == "/metrics":
            return await call_next(request)

        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            path = _route_template(request)
            REQUEST_LATENCY.labels(request.method, path).observe(time.perf_counter() - start)
            REQUEST_COUNT.labels(request.method, path, status).inc()


def metrics_response() -> Response:
    """Render the Prometheus exposition format for the /metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
