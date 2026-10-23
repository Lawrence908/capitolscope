"""Rate limiting must key on the visitor, not the reverse proxy."""

import pytest
from starlette.requests import Request

from api.middleware import real_client_ip

pytestmark = pytest.mark.unit


def _req(peer: str, headers: dict) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "client": (peer, 1234), "headers": raw, "method": "GET", "path": "/"})


def test_cloudflare_header_wins_behind_private_proxy():
    r = _req("172.21.0.5", {"CF-Connecting-IP": "203.0.113.9", "X-Real-IP": "172.21.0.9"})
    assert real_client_ip(r) == "203.0.113.9"


def test_x_real_ip_then_forwarded_for():
    assert real_client_ip(_req("172.21.0.5", {"X-Real-IP": "198.51.100.7"})) == "198.51.100.7"
    assert real_client_ip(_req("10.0.0.2", {"X-Forwarded-For": "198.51.100.8, 10.0.0.1"})) == "198.51.100.8"


def test_public_peer_cannot_spoof_headers():
    r = _req("8.8.8.8", {"CF-Connecting-IP": "1.2.3.4", "X-Forwarded-For": "5.6.7.8"})
    assert real_client_ip(r) == "8.8.8.8"


def test_no_headers_falls_back_to_peer():
    assert real_client_ip(_req("172.21.0.5", {})) == "172.21.0.5"
