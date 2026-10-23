"""
Failure alerting for the congressional disclosure sync pipeline.

Alerting is best-effort and must never break an ingestion run: every path
here swallows its own exceptions and degrades to a log line. When
``settings.INGESTION_ALERT_EMAIL`` is configured (one address, or several
separated by commas/semicolons) an email is also sent, but a missing/broken
mail path is not treated as an error.

Per-source health is tracked as a streak across runs (``evaluate_source_health``)
so a source that stays down produces one alert when it crosses the failure
threshold, a reminder every few days while it stays down, and a recovery
notice when it comes back, instead of an email on every run.
"""

from __future__ import annotations

import html as _html
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# A source must fail this many consecutive runs before we alert (rides out
# one-off network blips; with twice-daily runs this is ~12h).
FAILURE_ALERT_THRESHOLD = 2
# While a source stays down, repeat the alert at most this often.
REMINDER_INTERVAL = timedelta(hours=72)


def parse_recipients(raw: Optional[str]) -> List[str]:
    """Split a comma/semicolon/whitespace separated address list, dropping blanks and dupes."""
    if not raw:
        return []
    seen: List[str] = []
    for part in re.split(r"[,;\s]+", raw):
        addr = part.strip()
        if addr and "@" in addr and addr not in seen:
            seen.append(addr)
    return seen


def _parse_ts(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        ts = datetime.fromisoformat(value)
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def evaluate_source_health(
    prior_streaks: Optional[Dict[str, Dict[str, Any]]],
    source_health: Dict[str, bool],
    source_errors: Dict[str, List[str]],
    now: Optional[datetime] = None,
    threshold: int = FAILURE_ALERT_THRESHOLD,
    reminder_interval: timedelta = REMINDER_INTERVAL,
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """Advance each source's failure streak and decide which alerts to send.

    Pure function (no I/O) so the alert policy is unit-testable. Returns
    ``(new_streaks, alerts)`` where each alert is
    ``{"source", "kind": "down"|"reminder"|"recovered", "consecutive_failures",
    "first_failed_at", "errors"}``.
    """
    now = now or datetime.now(timezone.utc)
    now_iso = now.isoformat()
    prior_streaks = prior_streaks or {}
    new_streaks: Dict[str, Dict[str, Any]] = {}
    alerts: List[Dict[str, Any]] = []

    for source, ok in source_health.items():
        prev = dict(prior_streaks.get(source) or {})
        failures = int(prev.get("consecutive_failures") or 0)

        if ok:
            if prev.get("last_alerted_at"):
                alerts.append(
                    {
                        "source": source,
                        "kind": "recovered",
                        "consecutive_failures": failures,
                        "first_failed_at": prev.get("first_failed_at"),
                        "errors": [],
                    }
                )
            new_streaks[source] = {
                "consecutive_failures": 0,
                "first_failed_at": None,
                "last_alerted_at": None,
                "last_success_at": now_iso,
                "last_error": None,
            }
            continue

        failures += 1
        errors = source_errors.get(source) or []
        streak = {
            "consecutive_failures": failures,
            "first_failed_at": prev.get("first_failed_at") or now_iso,
            "last_alerted_at": prev.get("last_alerted_at"),
            "last_success_at": prev.get("last_success_at"),
            "last_error": errors[0] if errors else prev.get("last_error"),
        }

        last_alerted = _parse_ts(streak["last_alerted_at"])
        kind: Optional[str] = None
        if failures >= threshold and last_alerted is None:
            kind = "down"
        elif last_alerted is not None and now - last_alerted >= reminder_interval:
            kind = "reminder"

        if kind:
            streak["last_alerted_at"] = now_iso
            alerts.append(
                {
                    "source": source,
                    "kind": kind,
                    "consecutive_failures": failures,
                    "first_failed_at": streak["first_failed_at"],
                    "errors": errors,
                }
            )
        new_streaks[source] = streak

    return new_streaks, alerts


def _render_text(summary: str, errors: List[str], context: Dict[str, Any]) -> str:
    lines = [summary, ""]
    if errors:
        lines.append("Errors:")
        lines.extend(f"  - {e}" for e in errors)
        lines.append("")
    if context:
        lines.append("Context:")
        lines.extend(f"  {k}: {v}" for k, v in context.items())
    return "\n".join(lines)


def _render_html(summary: str, errors: List[str], context: Dict[str, Any]) -> str:
    try:
        from core.email_templates import email_heading, email_panel, p, render_email
    except Exception:  # template module unavailable: plain preformatted fallback
        return "<pre>" + _html.escape(_render_text(summary, errors, context)) + "</pre>"

    body = email_heading(_html.escape(summary))
    if errors:
        items = "".join(f"<li>{_html.escape(e)}</li>" for e in errors)
        body += email_panel(f'<ul style="margin:0;padding-left:18px;">{items}</ul>', accent=True)
    if context:
        rows = "".join(
            f"<div><code>{_html.escape(str(k))}</code>: {_html.escape(str(v))}</div>"
            for k, v in context.items()
        )
        body += p(rows)
    return render_email(title="CapitolScope ingestion alert", body_html=body, preheader=summary)


def emit_ingestion_alert(
    summary: str,
    errors: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Log an ingestion failure/degradation and optionally email operators.

    Never raises: alerting problems are logged and suppressed so they cannot
    abort the ingestion run that triggered them.
    """
    errors = errors or []
    context = context or {}

    # The log line is the guaranteed channel; the email is opportunistic.
    logger.error("INGESTION ALERT: %s | errors=%s | context=%s", summary, errors, context)

    try:
        from core.config import get_settings

        settings = get_settings()
        recipients = parse_recipients(getattr(settings, "INGESTION_ALERT_EMAIL", None))
    except Exception as exc:  # settings import/paths are environment-dependent
        logger.debug("Ingestion alert: settings unavailable, email skipped: %s", exc)
        return

    if not recipients:
        logger.debug("Ingestion alert: no INGESTION_ALERT_EMAIL configured, email skipped")
        return

    text = _render_text(summary, errors, context)
    html = _render_html(summary, errors, context)
    subject = f"[CapitolScope] {summary[:120]}"

    try:
        from core.email import EmailService

        service = EmailService()
    except Exception as exc:
        logger.warning("Ingestion alert email unavailable (%s); alert was logged", exc)
        return

    for to_email in recipients:
        try:
            # Prefer the sync SMTP path (orchestrator runs synchronously inside
            # the Celery task); fall back to the async multi-provider path.
            sent = False
            if getattr(settings, "EMAIL_HOST", None):
                sent = service._send_smtp_email(to_email, "Operator", subject, html, text)
            if not sent:
                import asyncio

                sent = asyncio.run(
                    service._send_email(to_email, "Operator", subject, html, text)
                )
            if sent:
                logger.info("Ingestion alert email sent to %s", to_email)
            else:
                logger.warning("Ingestion alert email could not be delivered to %s", to_email)
        except Exception as exc:
            logger.warning("Ingestion alert email to %s failed (%s); alert was logged", to_email, exc)


def emit_source_alerts(alerts: List[Dict[str, Any]], context: Optional[Dict[str, Any]] = None) -> None:
    """Send one email per source state change produced by ``evaluate_source_health``."""
    for alert in alerts:
        source = alert["source"]
        n = alert["consecutive_failures"]
        since = alert.get("first_failed_at") or "unknown"
        if alert["kind"] == "recovered":
            summary = f"{source} ingestion recovered after {n} failed run(s)"
        elif alert["kind"] == "reminder":
            summary = f"{source} ingestion still failing ({n} consecutive runs)"
        else:
            summary = f"{source} ingestion failing ({n} consecutive runs)"
        emit_ingestion_alert(
            summary=summary,
            errors=alert.get("errors") or [],
            context={"source": source, "failing_since": since, **(context or {})},
        )
