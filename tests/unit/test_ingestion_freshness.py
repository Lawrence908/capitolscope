"""Ingestion freshness summary used by /health/detailed and /metrics."""

from datetime import datetime, timedelta, timezone

import pytest

from domains.congressional.fetch.freshness import read_checkpoint, summarize_ingestion

pytestmark = pytest.mark.unit

NOW = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)


def _streak(hours_ago=None, failures=0):
    return {
        "last_success_at": (NOW - timedelta(hours=hours_ago)).isoformat() if hours_ago is not None else None,
        "consecutive_failures": failures,
        "first_failed_at": None,
        "last_error": "senate: 403" if failures else None,
    }


def test_both_recent_is_healthy():
    s = summarize_ingestion({"source_streaks": {"house": _streak(3), "senate": _streak(3)}}, now=NOW)
    assert s["status"] == "healthy"
    assert s["sources"]["house"]["hours_since_success"] == 3.0


def test_old_success_is_stale():
    s = summarize_ingestion({"source_streaks": {"house": _streak(3), "senate": _streak(60, failures=5)}}, now=NOW)
    assert s["status"] == "stale"
    assert s["sources"]["senate"]["status"] == "stale"
    assert s["sources"]["senate"]["consecutive_failures"] == 5


def test_failing_without_any_recorded_success_is_stale():
    s = summarize_ingestion({"source_streaks": {"house": _streak(3), "senate": _streak(None, failures=1)}}, now=NOW)
    assert s["sources"]["senate"]["status"] == "stale"
    assert s["status"] == "stale"


def test_no_checkpoint_is_unknown():
    s = summarize_ingestion({}, now=NOW)
    assert s["status"] == "unknown"
    assert {v["status"] for v in s["sources"].values()} == {"unknown"}


def test_read_checkpoint_missing_or_corrupt(tmp_path):
    assert read_checkpoint(tmp_path / "nope.json") == {}
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert read_checkpoint(bad) == {}
