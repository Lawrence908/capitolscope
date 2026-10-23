"""
Ingestion freshness: how recently each disclosure source last synced.

Reads the sync checkpoint the orchestrator writes after every run (no DB, no
network), so it is cheap enough for health checks and the /metrics scrape.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# A source with no successful sync for this long is reported stale. The sync
# runs twice a day, so this tolerates two missed runs plus slack.
STALE_AFTER = timedelta(hours=48)
SOURCES = ("house", "senate")


def checkpoint_path() -> Path:
    base = Path(os.environ.get("CAPITOLSCOPE_DATA_DIR", "/app/data/congress"))
    return base / "state" / "checkpoint.json"


def read_checkpoint(path: Optional[Path] = None) -> Dict[str, Any]:
    path = path or checkpoint_path()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _parse_ts(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        ts = datetime.fromisoformat(value)
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def summarize_ingestion(
    checkpoint: Dict[str, Any],
    now: Optional[datetime] = None,
    stale_after: timedelta = STALE_AFTER,
) -> Dict[str, Any]:
    """Per-source freshness plus an overall status: healthy, stale or unknown."""
    now = now or datetime.now(timezone.utc)
    streaks = checkpoint.get("source_streaks") or {}
    sources: Dict[str, Dict[str, Any]] = {}
    statuses = []
    for name in SOURCES:
        streak = streaks.get(name) or {}
        last_success = _parse_ts(streak.get("last_success_at"))
        failures = int(streak.get("consecutive_failures") or 0)
        if last_success is None:
            # Failing with no success on record (e.g. down since before
            # streaks were tracked) is stale, not merely unknown.
            status = "stale" if failures else "unknown"
        elif now - last_success > stale_after:
            status = "stale"
        else:
            status = "healthy"
        statuses.append(status)
        sources[name] = {
            "status": status,
            "last_success_at": last_success.isoformat() if last_success else None,
            "hours_since_success": round((now - last_success).total_seconds() / 3600, 1)
            if last_success
            else None,
            "consecutive_failures": failures,
            "failing_since": streak.get("first_failed_at"),
            "last_error": streak.get("last_error"),
        }

    if "stale" in statuses:
        overall = "stale"
    elif all(s == "healthy" for s in statuses):
        overall = "healthy"
    else:
        overall = "unknown"
    return {
        "status": overall,
        "last_run": checkpoint.get("last_run"),
        "last_run_status": checkpoint.get("last_status"),
        "sources": sources,
    }
