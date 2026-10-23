"""Alert policy for the congressional disclosure sync (fetch/alerts.py)."""

from datetime import datetime, timedelta, timezone

import pytest

from domains.congressional.fetch import alerts
from domains.congressional.fetch.alerts import (
    emit_source_alerts,
    evaluate_source_health,
    parse_recipients,
)

pytestmark = pytest.mark.unit

T0 = datetime(2026, 10, 22, 14, 0, tzinfo=timezone.utc)


def _run(prior, senate_ok, now, house_ok=True, errors=None):
    return evaluate_source_health(
        prior,
        source_health={"house": house_ok, "senate": senate_ok},
        source_errors={"house": [], "senate": errors or (["senate: 403"] if not senate_ok else [])},
        now=now,
    )


class TestParseRecipients:
    def test_comma_and_semicolon_separated(self):
        assert parse_recipients("a@x.com, b@y.com;c@z.com") == ["a@x.com", "b@y.com", "c@z.com"]

    def test_blank_dupes_and_junk_dropped(self):
        assert parse_recipients(" a@x.com,,a@x.com, nonsense ") == ["a@x.com"]

    @pytest.mark.parametrize("raw", [None, "", "   "])
    def test_empty(self, raw):
        assert parse_recipients(raw) == []


class TestEvaluateSourceHealth:
    def test_single_failure_does_not_alert(self):
        streaks, sent = _run(None, senate_ok=False, now=T0)
        assert sent == []
        assert streaks["senate"]["consecutive_failures"] == 1
        assert streaks["senate"]["first_failed_at"] == T0.isoformat()

    def test_second_consecutive_failure_alerts_down_once(self):
        streaks, _ = _run(None, senate_ok=False, now=T0)
        streaks, sent = _run(streaks, senate_ok=False, now=T0 + timedelta(hours=12))
        assert [(a["source"], a["kind"]) for a in sent] == [("senate", "down")]
        assert sent[0]["consecutive_failures"] == 2
        assert sent[0]["first_failed_at"] == T0.isoformat()
        # Third failure inside the reminder window stays quiet.
        streaks, sent = _run(streaks, senate_ok=False, now=T0 + timedelta(hours=24))
        assert sent == []
        assert streaks["senate"]["consecutive_failures"] == 3

    def test_reminder_after_interval(self):
        streaks, _ = _run(None, senate_ok=False, now=T0)
        streaks, _ = _run(streaks, senate_ok=False, now=T0 + timedelta(hours=12))
        streaks, sent = _run(streaks, senate_ok=False, now=T0 + timedelta(hours=12 + 72))
        assert [a["kind"] for a in sent] == ["reminder"]

    def test_recovery_after_alerted_outage(self):
        streaks, _ = _run(None, senate_ok=False, now=T0)
        streaks, _ = _run(streaks, senate_ok=False, now=T0 + timedelta(hours=12))
        streaks, sent = _run(streaks, senate_ok=True, now=T0 + timedelta(hours=24))
        assert [(a["source"], a["kind"]) for a in sent] == [("senate", "recovered")]
        assert streaks["senate"]["consecutive_failures"] == 0
        assert streaks["senate"]["last_alerted_at"] is None

    def test_recovery_from_unalerted_blip_is_silent(self):
        streaks, _ = _run(None, senate_ok=False, now=T0)
        _, sent = _run(streaks, senate_ok=True, now=T0 + timedelta(hours=12))
        assert sent == []

    def test_healthy_sources_track_last_success(self):
        streaks, sent = _run(None, senate_ok=True, now=T0)
        assert sent == []
        assert streaks["house"]["last_success_at"] == T0.isoformat()

    def test_sources_are_independent(self):
        streaks, _ = _run(None, senate_ok=False, house_ok=False, now=T0)
        streaks, sent = _run(streaks, senate_ok=False, house_ok=True, now=T0 + timedelta(hours=12))
        assert [(a["source"], a["kind"]) for a in sent] == [("senate", "down")]
        assert streaks["house"]["consecutive_failures"] == 0


class TestEmitSourceAlerts:
    def test_one_email_per_alert_with_readable_summary(self, monkeypatch):
        calls = []
        monkeypatch.setattr(alerts, "emit_ingestion_alert", lambda **kw: calls.append(kw))
        emit_source_alerts(
            [
                {"source": "senate", "kind": "down", "consecutive_failures": 2,
                 "first_failed_at": T0.isoformat(), "errors": ["senate: 403"]},
                {"source": "house", "kind": "recovered", "consecutive_failures": 3,
                 "first_failed_at": T0.isoformat(), "errors": []},
            ],
            context={"run_manifest": "m.json"},
        )
        assert [c["summary"] for c in calls] == [
            "senate ingestion failing (2 consecutive runs)",
            "house ingestion recovered after 3 failed run(s)",
        ]
        assert calls[0]["context"]["failing_since"] == T0.isoformat()
        assert calls[0]["context"]["run_manifest"] == "m.json"


class TestEmitIngestionAlertRecipients:
    def test_sends_to_every_recipient(self, monkeypatch, make_settings):
        settings = make_settings(
            INGESTION_ALERT_EMAIL="a@x.com, b@y.com",
            EMAIL_HOST="smtp.example.com",
        )
        monkeypatch.setattr("core.config.get_settings", lambda: settings)

        sent_to = []

        class FakeEmailService:
            def _send_smtp_email(self, to_email, to_name, subject, html, text):
                sent_to.append((to_email, subject))
                return True

        monkeypatch.setattr("core.email.EmailService", FakeEmailService)
        alerts.emit_ingestion_alert("senate ingestion failing (2 consecutive runs)", errors=["403"])
        assert [t for t, _ in sent_to] == ["a@x.com", "b@y.com"]
        assert sent_to[0][1] == "[CapitolScope] senate ingestion failing (2 consecutive runs)"
