"""X client behavior with a mocked transport (no network)."""

import json

import httpx
import pytest

from domains.social import x_client
from domains.social.x_client import XClient, XPostError, XRateLimited

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("X_TOKEN_STATE_FILE", str(tmp_path / "x_token.json"))
    monkeypatch.setenv("X_OAUTH2_ACCESS_TOKEN", "old-access")
    monkeypatch.setenv("X_OAUTH2_REFRESH_TOKEN", "refresh-1")
    monkeypatch.setenv("X_OAUTH2_CLIENT_ID", "client")
    monkeypatch.setenv("SOCIAL_X_ENABLED", "1")


def _client(handler):
    return XClient(client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_refreshes_once_on_401_and_persists_rotation(tmp_path):
    calls = []

    def handler(req: httpx.Request):
        calls.append((req.url.path, req.headers.get("authorization")))
        if req.url.path == "/2/oauth2/token":
            return httpx.Response(200, json={"access_token": "new-access", "refresh_token": "refresh-2"})
        if req.headers.get("authorization") == "Bearer old-access":
            return httpx.Response(401, json={})
        return httpx.Response(201, json={"data": {"id": "999"}})

    c = _client(handler)
    assert c.post("hello") == "999"
    assert [p for p, _ in calls] == ["/2/tweets", "/2/oauth2/token", "/2/tweets"]
    saved = json.loads((tmp_path / "x_token.json").read_text())
    assert saved["access_token"] == "new-access" and saved["refresh_token"] == "refresh-2"


def test_rate_limit_surfaces_reset_time():
    def handler(req):
        return httpx.Response(429, headers={"x-rate-limit-reset": "1800000000"}, json={})

    with pytest.raises(XRateLimited) as exc:
        _client(handler).post("hello")
    assert exc.value.reset_at is not None and exc.value.reset_at.year == 2027


def test_thread_with_image_attaches_media_and_chains_replies():
    posted = []

    def handler(req: httpx.Request):
        if req.url.path == "/2/media/upload":
            assert b"tweet_image" in req.content
            return httpx.Response(200, json={"data": {"id": "m1"}})
        body = json.loads(req.content)
        posted.append(body)
        return httpx.Response(201, json={"data": {"id": f"p{len(posted)}"}})

    ids = _client(handler).post_thread("lead", ["reply"], image=b"\x89PNG fake")
    assert ids == ["p1", "p2"]
    assert posted[0]["media"] == {"media_ids": ["m1"]}
    assert posted[1]["reply"] == {"in_reply_to_tweet_id": "p1"}


def test_disabled_gate(monkeypatch):
    monkeypatch.setenv("SOCIAL_X_ENABLED", "0")
    with pytest.raises(XPostError, match="disabled"):
        _client(lambda req: httpx.Response(500)).post_thread("lead")
    assert x_client.x_enabled() is False
