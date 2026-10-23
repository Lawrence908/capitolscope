"""
Prometheus metrics (Phase 7c observability).

Exposes HTTP request counts and latency at ``/metrics`` (plus prometheus_client's
default process/GC collectors). Labels use the matched ROUTE TEMPLATE
(``/api/v1/trades/{trade_id}``), not the raw path, so per-id URLs don't blow up
cardinality.
"""

import time

from prometheus_client import Counter, Gauge, Histogram, CONTENT_TYPE_LATEST, generate_latest
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


INGESTION_LAST_SUCCESS = Gauge(
    "capitolscope_ingestion_last_success_timestamp_seconds",
    "Unix time of the last successful disclosure sync per source (0 if none on record)",
    ["source"],
)
INGESTION_CONSECUTIVE_FAILURES = Gauge(
    "capitolscope_ingestion_consecutive_failures",
    "Consecutive failed sync runs per disclosure source",
    ["source"],
)


def refresh_ingestion_gauges() -> None:
    """Update ingestion gauges from the sync checkpoint (cheap file read; never raises)."""
    try:
        from datetime import datetime

        from domains.congressional.fetch.freshness import read_checkpoint, summarize_ingestion

        summary = summarize_ingestion(read_checkpoint())
        for source, info in summary["sources"].items():
            ts = info.get("last_success_at")
            INGESTION_LAST_SUCCESS.labels(source).set(
                datetime.fromisoformat(ts).timestamp() if ts else 0
            )
            INGESTION_CONSECUTIVE_FAILURES.labels(source).set(info.get("consecutive_failures") or 0)
    except Exception:  # metrics must never break the scrape
        pass


def metrics_response() -> Response:
    """Render the Prometheus exposition format for the /metrics endpoint."""
    refresh_ingestion_gauges()
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
