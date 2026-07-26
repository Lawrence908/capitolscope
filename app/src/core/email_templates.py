"""
Unified email layout for CapitolScope.

Every transactional email (password reset, welcome, subscription, trade alerts,
digests) renders through :func:`render_email` so they share one look: the
"Scrutiny" oversight-dossier language, translated for email clients.

Email constraints drove the choices here — inline styles only (Gmail strips
``<style>`` blocks), table-based layout (Outlook), web-safe fonts (Georgia
serif for display, a system sans for body, monospace for data), and a light
"paper" palette (dark email bodies render unreliably across clients).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

# --- palette (light "paper" translation of the app tokens) ---
PAPER = "#f6f5f1"      # outer background
SURFACE = "#ffffff"    # card
INSET = "#efece4"      # subtle panels / table stripes
LINE = "#e3e0d7"       # borders / dividers
INK = "#1a201e"        # headings / primary text
BODY = "#48514b"       # body text
FAINT = "#77807a"      # muted / captions
ACCENT = "#1f9e88"     # verdigris fill (buttons)
ACCENT_DK = "#217a6b"  # verdigris for text/links (AA on white)
ACCENT_INK = "#06130f" # text on accent fills
BRASS = "#9a7b32"

# --- font stacks (no web fonts; clients fall back gracefully) ---
SERIF = "Georgia, 'Times New Roman', serif"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'SF Mono', 'IBM Plex Mono', Menlo, Consolas, monospace"

EYEBROW = "CapitolScope · Congressional Oversight"
SUPPORT_EMAIL = "capitolscope@gmail.com"


def email_button(url: str, label: str) -> str:
    """A robust, table-wrapped call-to-action button (accent fill, dark ink)."""
    return f"""
    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:24px 0;">
      <tr>
        <td style="border-radius:6px;background:{ACCENT};">
          <a href="{url}" target="_blank"
             style="display:inline-block;padding:13px 26px;font-family:{SANS};font-size:15px;
                    font-weight:600;color:{ACCENT_INK};text-decoration:none;border-radius:6px;">
            {label}
          </a>
        </td>
      </tr>
    </table>
    """.strip()


def email_eyebrow(text: str) -> str:
    """A mono, letter-spaced caption label (accent)."""
    return (
        f'<div style="font-family:{MONO};font-size:11px;letter-spacing:0.16em;'
        f'text-transform:uppercase;color:{ACCENT_DK};margin-bottom:6px;">{text}</div>'
    )


def email_heading(text: str) -> str:
    """A serif section heading."""
    return (
        f'<h2 style="margin:0 0 12px 0;font-family:{SERIF};font-weight:500;'
        f'font-size:24px;line-height:1.15;color:{INK};">{text}</h2>'
    )


def email_panel(inner_html: str, accent: bool = False) -> str:
    """A bordered content panel; ``accent`` adds a verdigris left rule."""
    border_left = f"border-left:3px solid {ACCENT};" if accent else ""
    return (
        f'<div style="background:{INSET};border:1px solid {LINE};{border_left}'
        f'border-radius:8px;padding:18px 20px;margin:20px 0;">{inner_html}</div>'
    )


def render_email(
    *,
    title: str,
    body_html: str,
    preheader: str = "",
    footer_note: str = "",
    footer_links: Optional[List[Tuple[str, str]]] = None,
) -> str:
    """Wrap ``body_html`` in the shared dossier email shell.

    ``title`` sets the document title; ``preheader`` is the hidden inbox preview
    line; ``footer_note`` is a small line above the copyright; ``footer_links``
    is an optional list of ``(label, url)`` shown as a separated row.
    """
    preheader_html = (
        f'<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{preheader}</div>'
        if preheader
        else ""
    )

    links_html = ""
    if footer_links:
        parts = [
            f'<a href="{url}" style="color:{FAINT};text-decoration:underline;">{label}</a>'
            for label, url in footer_links
        ]
        links_html = (
            f'<p style="margin:6px 0;font-family:{SANS};font-size:12px;color:{FAINT};">'
            + ' &nbsp;·&nbsp; '.join(parts)
            + "</p>"
        )

    note_html = (
        f'<p style="margin:6px 0;font-family:{SANS};font-size:12px;color:{FAINT};">{footer_note}</p>'
        if footer_note
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="light">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background:{PAPER};">
  {preheader_html}
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{PAPER};padding:24px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0"
               style="max-width:600px;width:100%;background:{SURFACE};border:1px solid {LINE};border-radius:12px;overflow:hidden;">
          <!-- accent rule -->
          <tr><td style="height:3px;background:{ACCENT};font-size:0;line-height:0;">&nbsp;</td></tr>
          <!-- masthead -->
          <tr>
            <td style="padding:26px 32px 18px 32px;border-bottom:1px solid {LINE};">
              {email_eyebrow(EYEBROW)}
              <div style="font-family:{SERIF};font-size:22px;font-weight:500;letter-spacing:-0.01em;color:{INK};">
                Capitol<span style="color:{ACCENT_DK};">Scope</span>
              </div>
            </td>
          </tr>
          <!-- body -->
          <tr>
            <td style="padding:28px 32px;font-family:{SANS};font-size:15px;line-height:1.6;color:{BODY};">
              {body_html}
            </td>
          </tr>
          <!-- footer -->
          <tr>
            <td style="padding:22px 32px;border-top:1px solid {LINE};background:{INSET};text-align:center;">
              {note_html}
              {links_html}
              <p style="margin:6px 0;font-family:{MONO};font-size:11px;letter-spacing:0.04em;color:{FAINT};">
                © 2025 CapitolScope · Built on public STOCK Act disclosures
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def p(text: str) -> str:
    """A body paragraph in the shared style."""
    return f'<p style="margin:0 0 14px 0;font-family:{SANS};font-size:15px;line-height:1.6;color:{BODY};">{text}</p>'
