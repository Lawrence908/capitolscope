"""
Failure alerting for the congressional disclosure sync pipeline.

Alerting is best-effort and must never break an ingestion run: every path
here swallows its own exceptions and degrades to a log line. When
``settings.INGESTION_ALERT_EMAIL`` is configured an email is also sent, but a
missing/broken mail path is not treated as an error.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


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


def emit_ingestion_alert(
    summary: str,
    errors: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Log an ingestion failure/degradation and optionally email an operator.

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
        to_email = getattr(settings, "INGESTION_ALERT_EMAIL", None)
    except Exception as exc:  # settings import/paths are environment-dependent
        logger.debug("Ingestion alert: settings unavailable, email skipped: %s", exc)
        return

    if not to_email:
        logger.debug("Ingestion alert: no INGESTION_ALERT_EMAIL configured, email skipped")
        return

    text = _render_text(summary, errors, context)
    html = "<pre>" + text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") + "</pre>"
    subject = f"[CapitolScope] Ingestion alert: {summary[:120]}"

    try:
        from core.email import EmailService

        service = EmailService()
        # Prefer the sync SMTP path (orchestrator runs synchronously inside the
        # Celery task); fall back to the async multi-provider path if needed.
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
        logger.warning("Ingestion alert email failed (%s); alert was logged", exc)
