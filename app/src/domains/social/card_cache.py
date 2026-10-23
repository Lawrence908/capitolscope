"""
Disk cache for rendered card PNGs.

Files live under <data dir>/og/<kind>/<id>-<hash>.png where the data dir is
the parent of CAPITOLSCOPE_DATA_DIR (default /app/data/congress, so the cache
is /app/data/og). OG_CACHE_DIR overrides the location. The hash covers the
card's input data, the render version and the printed domain, so any change
to the trade, member, security name or layout produces a new file; stale
versions for the same id are removed when a new one is written.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Callable, Tuple

from .cards import RENDER_VERSION

logger = logging.getLogger(__name__)


def cache_dir() -> Path:
    explicit = os.getenv("OG_CACHE_DIR")
    if explicit:
        return Path(explicit)
    data_dir = Path(os.getenv("CAPITOLSCOPE_DATA_DIR", "/app/data/congress"))
    return data_dir.parent / "og"


def content_hash(data: Any, domain: str) -> str:
    payload = asdict(data) if is_dataclass(data) else data
    blob = json.dumps({"v": RENDER_VERSION, "domain": domain, "data": payload}, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def get_or_render(kind: str, ident: str, digest: str, render: Callable[[], bytes]) -> Tuple[bytes, bool]:
    """Return (png, from_cache). Cache failures never fail the request."""
    base = cache_dir() / kind
    path = base / f"{ident}-{digest}.png"
    try:
        if path.is_file():
            return path.read_bytes(), True
    except OSError as exc:
        logger.warning("og cache read failed for %s: %s", path, exc)

    png = render()
    try:
        base.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=base, prefix=".tmp-", suffix=".png")
        with os.fdopen(fd, "wb") as fh:
            fh.write(png)
        os.replace(tmp, path)
        for old in base.glob(f"{ident}-*.png"):
            if old != path:
                try:
                    old.unlink()
                except OSError:
                    pass
    except OSError as exc:
        logger.warning("og cache write failed for %s: %s", path, exc)
    return png, False

