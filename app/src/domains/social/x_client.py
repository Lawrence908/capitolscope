"""
Minimal X (Twitter) API v2 client for the CapitolScope account.

Ported from the proven Zeus/Pheme poster (OAuth 2.0 user-context bearer,
refresh on 401 with token rotation persisted to a JSON file) and extended
with image upload (POST /2/media/upload, multipart, tweet_image) and
rate-limit awareness (HTTP 429 -> XRateLimited with the reset time).

Env:
  SOCIAL_X_ENABLED              master gate for any write to X (default 0)
  X_OAUTH2_CLIENT_ID            OAuth2 app client id (needed for refresh)
  X_OAUTH2_CLIENT_SECRET        confidential-client secret (optional)
  X_OAUTH2_ACCESS_TOKEN         initial user access token (seed)
  X_OAUTH2_REFRESH_TOKEN        initial refresh token (offline.access scope)
  X_TOKEN_STATE_FILE            rotated tokens (default /app/data/social/x_token.json)
Scopes needed: tweet.read tweet.write users.read media.write offline.access
"""

from __future__ import annotations

import json
import logging
import os
from base64 import b64encode
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)

API_BASE = os.getenv("X_API_BASE_URL", "https://api.x.com").rstrip("/")


class XPostError(RuntimeError):
    pass


class XRateLimited(XPostError):
    def __init__(self, reset_at: Optional[datetime], message: str):
        super().__init__(message)
        self.reset_at = reset_at


def x_enabled() -> bool:
    return os.getenv("SOCIAL_X_ENABLED", "0").strip().lower() in ("1", "true", "yes", "on")


def _state_path() -> Path:
    return Path(os.getenv("X_TOKEN_STATE_FILE", "/app/data/social/x_token.json"))


def load_tokens() -> dict:
    """Rotated tokens from the state file win over the env-seeded ones."""
    state: dict = {}
    p = _state_path()
    if p.is_file():
        try:
            state = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            logger.warning("corrupt X token state at %s, falling back to env", p)
    return {
        "access_token": state.get("access_token") or os.getenv("X_OAUTH2_ACCESS_TOKEN", ""),
        "refresh_token": state.get("refresh_token") or os.getenv("X_OAUTH2_REFRESH_TOKEN", ""),
    }


def save_tokens(access_token: str, refresh_token: str) -> None:
    p = _state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "rotated_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    os.chmod(tmp, 0o600)
    tmp.replace(p)


def _reset_at(resp: httpx.Response) -> Optional[datetime]:
    raw = resp.headers.get("x-rate-limit-reset")
    try:
        return datetime.fromtimestamp(int(raw), tz=timezone.utc) if raw else None
    except ValueError:
        return None


class XClient:
    def __init__(self, client: Optional[httpx.Client] = None):
        self._client = client or httpx.Client(timeout=30.0)
        self.tokens = load_tokens()

    # -- auth ---------------------------------------------------------------

    def _refresh(self) -> None:
        client_id = os.getenv("X_OAUTH2_CLIENT_ID", "").strip()
        client_secret = os.getenv("X_OAUTH2_CLIENT_SECRET", "").strip()
        refresh_token = self.tokens.get("refresh_token", "")
        if not refresh_token or not client_id:
            raise XPostError("X access token expired and no refresh credentials (X_OAUTH2_REFRESH_TOKEN + X_OAUTH2_CLIENT_ID)")
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {"grant_type": "refresh_token", "refresh_token": refresh_token}
        if client_secret:
            headers["Authorization"] = "Basic " + b64encode(f"{client_id}:{client_secret}".encode()).decode()
        else:
            data["client_id"] = client_id
        r = self._client.post(f"{API_BASE}/2/oauth2/token", headers=headers, data=data)
        if r.status_code != 200:
            raise XPostError(f"X token refresh failed: {r.status_code} {r.text[:200]}")
        body = r.json() or {}
        access = str(body.get("access_token", ""))
        if not access:
            raise XPostError("X token refresh returned no access_token")
        self.tokens = {"access_token": access, "refresh_token": str(body.get("refresh_token") or refresh_token)}
        save_tokens(self.tokens["access_token"], self.tokens["refresh_token"])
        logger.info("X access token refreshed")

    def _send(self, method: str, path: str, **kwargs) -> httpx.Response:
        """One request with refresh-once-on-401 and 429 surfaced as XRateLimited."""
        if not self.tokens.get("access_token"):
            self._refresh()
        for attempt in range(2):
            headers = dict(kwargs.pop("headers", {}) or {})
            headers["Authorization"] = f"Bearer {self.tokens['access_token']}"
            r = self._client.request(method, f"{API_BASE}{path}", headers=headers, **kwargs)
            if r.status_code == 401 and attempt == 0:
                self._refresh()
                continue
            if r.status_code == 429:
                reset = _reset_at(r)
                raise XRateLimited(reset, f"X rate limited until {reset.isoformat() if reset else 'unknown'}")
            if r.status_code >= 400:
                raise XPostError(f"X {method} {path} failed: {r.status_code} {r.text[:300]}")
            return r
        raise XPostError(f"X {method} {path} failed after token refresh")

    # -- api ----------------------------------------------------------------

    def upload_image(self, png: bytes, filename: str = "card.png") -> str:
        r = self._send(
            "POST",
            "/2/media/upload",
            files={"media": (filename, png, "image/png")},
            data={"media_category": "tweet_image"},
        )
        media_id = str(((r.json() or {}).get("data") or {}).get("id", ""))
        if not media_id:
            raise XPostError("X media upload returned no id")
        return media_id

    def post(self, text: str, reply_to: Optional[str] = None, media_ids: Optional[List[str]] = None) -> str:
        payload: dict = {"text": text}
        if reply_to:
            payload["reply"] = {"in_reply_to_tweet_id": reply_to}
        if media_ids:
            payload["media"] = {"media_ids": media_ids}
        r = self._send("POST", "/2/tweets", json=payload)
        tweet_id = str(((r.json() or {}).get("data") or {}).get("id", ""))
        if not tweet_id:
            raise XPostError("X returned no post id")
        return tweet_id

    def post_thread(self, lead: str, replies: Optional[List[str]] = None, image: Optional[bytes] = None) -> List[str]:
        """Post the lead (with an optional image) and replies chained under it."""
        if not x_enabled():
            raise XPostError("X posting disabled (SOCIAL_X_ENABLED=0)")
        media_ids = [self.upload_image(image)] if image else None
        ids = [self.post(lead, media_ids=media_ids)]
        for text in replies or []:
            ids.append(self.post(text, reply_to=ids[-1]))
        return ids
