"""
Shareable card images (Open Graph / X) in the Bulletin design, rendered with
Pillow. Pure functions: they take the plain dataclasses from formatting.py and
return PNG bytes, so they unit-test without a database.

Design (light theme): ink on white, heavy black slabs, giant condensed tickers
in Big Shoulders Display, body in Libre Franklin, square corners, brand red
#c5302a as the only accent. Disclosure timing is the fuel-style gauge from
frontend/src/components/ui/bulletin.tsx (DisclosureGauge): a 180 degree dial,
0 to 45 days over the first 150 degrees, the last 30 degrees a red "late"
zone, late needles pegging at 45 + 180 days. Parties are never color-coded:
an ink-outlined letter chip plus "R-AL" text.

Fonts are bundled under app/src/assets/fonts (SIL OFL 1.1, from
github.com/google/fonts).
"""

from __future__ import annotations

import io
import math
import threading
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from .formatting import (
    DISCLOSURE_LIMIT_DAYS,
    MemberCardData,
    TradeCardData,
    affiliation,
    amount_range,
    chamber_label,
    days_to_disclose,
    fmt_date,
    is_amendment,
    is_late,
    member_line,
    party_letter,
    plural,
    public_domain,
    short_asset_label,
    clean_asset_name,
    timing_sentence,
    trade_verb,
)

# Bump when the layout changes so cached PNGs are re-rendered.
RENDER_VERSION = "bulletin-1"

TRADE_SIZE = (1200, 675)
MEMBER_SIZE = (1200, 630)
DEFAULT_SIZE = (1200, 630)

FONT_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"
_FONT_FILES = {
    "display": FONT_DIR / "BigShouldersDisplay-wght.ttf",
    "body": FONT_DIR / "LibreFranklin-wght.ttf",
}

# Light-theme tokens (frontend/src/index.css, design tokens.md).
BG = (255, 255, 255)
INK = (18, 20, 23)  # #121417
MUTED = (74, 79, 87)  # #4a4f57
FAINT = (107, 112, 121)  # #6b7079
LINE = (213, 215, 219)  # #d5d7db
TRACK = (236, 237, 239)  # #ecedef, surface-inset
ACCENT = (197, 48, 42)  # #c5302a brand red
ACCENT_ON_SLAB = (232, 84, 76)  # #e8544c, brand red lifted for contrast on ink
LATE_TRACK = (239, 197, 195)  # accent at 28% over white
ON_SLAB = (255, 255, 255)
SLAB_MUTED = (169, 174, 182)  # #a9aeb6

M = 64  # outer margin

# Gauge geometry, mirrored from bulletin.tsx.
ON_TIME_SWEEP = 150.0
LATE_PEG_DAYS = 180.0

# FreeType faces are shared across renders; serialize rendering.
_RENDER_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Fonts and text helpers
# ---------------------------------------------------------------------------
@lru_cache(maxsize=512)
def _font(kind: str, size: int, weight: int) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(_FONT_FILES[kind]), max(1, int(size)))
    try:
        f.set_variation_by_axes([weight])
    except (OSError, AttributeError):  # FreeType built without variation support
        pass
    return f


def display(size: int, weight: int = 900) -> ImageFont.FreeTypeFont:
    return _font("display", size, weight)


def body(size: int, weight: int = 400) -> ImageFont.FreeTypeFont:
    return _font("body", size, weight)


def text_w(f: ImageFont.FreeTypeFont, s: str) -> int:
    if not s:
        return 0
    x0, _, x1, _ = f.getbbox(s, anchor="ls")
    return x1 - x0


def ink_h(f: ImageFont.FreeTypeFont, s: str) -> int:
    """Height of the inked glyphs above the baseline (cap height for caps)."""
    if not s:
        return 0
    _, y0, _, _ = f.getbbox(s, anchor="ls")
    return -y0


def truncate(f: ImageFont.FreeTypeFont, s: str, max_w: int) -> str:
    if text_w(f, s) <= max_w:
        return s
    ell = "..."
    while s and text_w(f, s.rstrip() + ell) > max_w:
        s = s[:-1]
    return (s.rstrip() + ell) if s else ell


def fit(
    s: str,
    kind: str,
    weight: int,
    max_w: int,
    max_size: int,
    min_size: int,
    max_h: Optional[int] = None,
) -> Tuple[ImageFont.FreeTypeFont, str]:
    """Largest font (max_size down to min_size) whose rendering fits; truncate at min."""
    size = max_size
    while size > min_size:
        f = _font(kind, size, weight)
        if text_w(f, s) <= max_w and (max_h is None or ink_h(f, s) <= max_h):
            return f, s
        size = max(min_size, int(size * 0.94))
    f = _font(kind, min_size, weight)
    return f, truncate(f, s, max_w)


def _new(size: Tuple[int, int]) -> Tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGBA", size, BG + (255,))
    return img, ImageDraw.Draw(img)


def _png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Shared marks
# ---------------------------------------------------------------------------
def draw_chip(d: ImageDraw.ImageDraw, x: int, y: int, size: int, letter: str, color=INK) -> int:
    """Square ink-outlined party letter (R/D/I). Returns the chip width."""
    border = max(2, round(size / 11))
    d.rectangle([x, y, x + size - 1, y + size - 1], outline=color, width=border)
    f = display(round(size * 0.74), 800)
    d.text((x + size / 2, y + size / 2 + 1), letter, font=f, fill=color, anchor="mm")
    return size


def draw_wordmark(d: ImageDraw.ImageDraw, right: int, baseline: int, size: int, color=ON_SLAB) -> int:
    """'CAPITOLSCOPE' with a red square mark, right-aligned. Returns left x."""
    f = display(size, 900)
    word = "CAPITOLSCOPE"
    w = text_w(f, word)
    x = right - w
    d.text((x, baseline), word, font=f, fill=color, anchor="ls")
    cap = ink_h(f, word)
    mark = max(8, round(cap * 0.62))
    gap = round(size * 0.3)
    mx = x - gap - mark
    d.rectangle([mx, baseline - mark, mx + mark - 1, baseline - 1], fill=ACCENT)
    return mx


def draw_stamp(d: ImageDraw.ImageDraw, x: int, y: int, h: int, verb: str) -> int:
    """BOUGHT is a filled ink box; SOLD (and others) an outlined box. Returns width."""
    f = display(round(h * 0.78), 800)
    pad = round(h * 0.32)
    w = text_w(f, verb) + pad * 2
    if verb == "BOUGHT":
        d.rectangle([x, y, x + w - 1, y + h - 1], fill=INK)
        color = ON_SLAB
    else:
        border = max(3, round(h / 14))
        d.rectangle([x, y, x + w - 1, y + h - 1], outline=INK, width=border)
        color = INK
    d.text((x + w / 2, y + h / 2 + 1), verb, font=f, fill=color, anchor="mm")
    return w


def angle_for_days(days: float) -> float:
    """Dial angle in math degrees (180 = left end, 0 = right end); see bulletin.tsx."""
    if days <= DISCLOSURE_LIMIT_DAYS:
        return 180.0 - (max(0.0, days) / DISCLOSURE_LIMIT_DAYS) * ON_TIME_SWEEP
    over = min(1.0, (days - DISCLOSURE_LIMIT_DAYS) / LATE_PEG_DAYS)
    return 180.0 - ON_TIME_SWEEP - over * (180.0 - ON_TIME_SWEEP)


def _point(cx: float, cy: float, r: float, deg: float) -> Tuple[float, float]:
    rad = math.radians(deg)
    return cx + r * math.cos(rad), cy - r * math.sin(rad)


def draw_gauge(
    img: Image.Image,
    cx: int,
    cy: int,
    r: int,
    stroke: int,
    days: Optional[float],
    late: bool,
    labels: bool = True,
    label_size: int = 18,
) -> None:
    """The disclosure gauge, supersampled for smooth arcs.

    ``late`` decides the red needle and red fill; callers pass False for
    amended filings, which are never called late (their needle is drawn ink
    and stops at the limit).
    """
    ss = 4
    tick_out = stroke * 0.9 + 3
    pad = stroke / 2 + tick_out + 6
    x0, y0 = int(cx - r - pad), int(cy - r - pad)
    x1, y1 = int(cx + r + pad), int(cy + stroke + 6)
    layer = Image.new("RGBA", ((x1 - x0) * ss, (y1 - y0) * ss), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    lcx, lcy = (cx - x0) * ss, (cy - y0) * ss
    R, S = r * ss, stroke * ss

    def arc(from_deg: float, to_deg: float, color) -> None:
        if from_deg - to_deg <= 0.01:
            return
        ro = R + S / 2
        box = [lcx - ro, lcy - ro, lcx + ro, lcy + ro]
        # Pillow measures clockwise from 3 o'clock; math degrees run counter-clockwise.
        ld.arc(box, 360 - from_deg, 360 - to_deg, fill=color, width=int(S))

    limit_deg = 180.0 - ON_TIME_SWEEP
    known = days is not None
    needle_deg = angle_for_days(days) if known else 180.0
    if known and not late:
        needle_deg = max(needle_deg, limit_deg)  # amendments: never into the late zone

    arc(180.0, limit_deg, TRACK)
    arc(limit_deg, 0.0, LATE_TRACK)
    if known and days > 0:
        arc(180.0, max(needle_deg, limit_deg), INK)
    if late:
        arc(limit_deg, needle_deg, ACCENT)

    for tick in (0, 15, 30, 45):
        deg = angle_for_days(tick)
        last = tick == DISCLOSURE_LIMIT_DAYS
        a = _point(lcx, lcy, R + S / 2 + 2 * ss, deg)
        b = _point(lcx, lcy, R + S / 2 + (tick_out if last else tick_out * 0.55) * ss, deg)
        ld.line([a, b], fill=ACCENT if last else FAINT, width=(3 if last else 2) * ss)

    if known:
        color = ACCENT if late else INK
        tip = _point(lcx, lcy, R - S * 0.2, needle_deg)
        ld.line([(lcx, lcy), tip], fill=color, width=int(max(2.0, stroke * 0.32) * ss))
        hub = max(3.0, stroke * 0.5) * ss
        ld.ellipse([lcx - hub, lcy - hub, lcx + hub, lcy + hub], fill=color)

    layer = layer.resize((x1 - x0, y1 - y0), Image.LANCZOS)
    img.alpha_composite(layer, (x0, y0))

    if labels:
        d = ImageDraw.Draw(img)
        fl = body(label_size, 500)
        fb = body(label_size, 700)
        ly = cy + stroke / 2 + label_size + 4
        d.text((cx - r, ly), "0", font=fl, fill=FAINT, anchor="ms")
        lx, lyy = _point(cx, cy, r + stroke / 2 + tick_out + label_size * 0.9, limit_deg)
        d.text((lx, lyy), str(DISCLOSURE_LIMIT_DAYS), font=fb, fill=ACCENT, anchor="mm")
        d.text((cx + r, ly), "LATE", font=fb, fill=ACCENT, anchor="ms")


def _slab(d: ImageDraw.ImageDraw, size: Tuple[int, int], top: int) -> None:
    d.rectangle([0, top, size[0], size[1]], fill=INK)


def _slab_brand(d: ImageDraw.ImageDraw, size: Tuple[int, int], top: int, domain: str) -> int:
    """Wordmark + domain at the right of the slab. Returns the left edge used."""
    h = size[1] - top
    word_base = top + round(h * 0.52)
    left = draw_wordmark(d, size[0] - M, word_base, round(h * 0.40))
    fd = body(max(14, round(h * 0.18)), 400)
    dw = text_w(fd, domain)
    d.text((size[0] - M, word_base + round(h * 0.28)), domain, font=fd, fill=SLAB_MUTED, anchor="rs")
    return min(left, size[0] - M - dw)


# ---------------------------------------------------------------------------
# Trade card (1200 x 675)
# ---------------------------------------------------------------------------
def render_trade_card(t: TradeCardData, domain: Optional[str] = None) -> bytes:
    with _RENDER_LOCK:
        return _png(_trade_image(t, domain or public_domain()))


def _trade_image(t: TradeCardData, domain: str) -> Image.Image:
    W, H = TRADE_SIZE
    img, d = _new(TRADE_SIZE)
    amended = is_amendment(t.filing_status)
    days = days_to_disclose(t.transaction_date, t.notification_date)
    late = is_late(days, t.filing_status)

    # -- top row: member (left), dates (right) --------------------------------
    disclosed = fmt_date(t.notification_date)
    traded = fmt_date(t.transaction_date)
    fd1, fd2 = body(24, 700), body(22, 400)
    line1 = f"Disclosed {disclosed}" if disclosed else "Disclosure date unknown"
    line2 = f"Traded {traded}" if traded else "Trade date unknown"
    d.text((W - M, 74), line1, font=fd1, fill=INK, anchor="rs")
    d.text((W - M, 106), line2, font=fd2, fill=FAINT, anchor="rs")
    dates_w = max(text_w(fd1, line1), text_w(fd2, line2))

    x = M
    letter = party_letter(t.party)
    chip = 42
    if letter:
        draw_chip(d, x, 58, chip, letter)
        x += chip + 16
    who = member_line(t.member_name, t.chamber, t.party, t.state, t.district)
    fm, who = fit(who, "body", 600, (W - M - dates_w - 40) - x, 34, 22)
    d.text((x, 92), who, font=fm, fill=INK, anchor="ls")

    d.rectangle([M, 128, W - M, 130], fill=INK)  # 3px section rule

    # -- right column: the gauge ----------------------------------------------
    gcx, gcy, gr, gs = 990, 318, 116, 20
    draw_gauge(img, gcx, gcy, gr, gs, days if not amended else None, late, label_size=18)
    if amended:
        value, vcolor = "AMENDED", INK
    elif days is None:
        value, vcolor = "UNKNOWN", FAINT
    else:
        value, vcolor = f"{days:,} DAY{'' if days == 1 else 'S'}", ACCENT if late else INK
    fv, value = fit(value, "display", 900, 300, 76, 40)
    d.text((gcx, gcy + 112), value, font=fv, fill=vcolor, anchor="ms")
    cap = "from trade to disclosure" if not amended else "timing not assessed"
    d.text((gcx, gcy + 146), cap, font=body(20, 500), fill=FAINT, anchor="ms")

    # -- left column: stamp + company, ticker, amount -------------------------
    col_w = 800 - M
    verb = trade_verb(t.transaction_type)
    sw = draw_stamp(d, M, 156, 54, verb)
    company = clean_asset_name(t.asset_name)
    head = (t.ticker or "").strip().upper()
    if not head:
        head = short_asset_label(t.asset_name)
        company = company if company and company.upper() != head else None
    if company:
        fc, company = fit(company, "body", 500, col_w - sw - 22, 30, 20)
        d.text((M + sw + 22, 156 + 27), company, font=fc, fill=MUTED, anchor="lm")

    ft, head = fit(head, "display", 900, col_w, 340, 72, max_h=230)
    # Centre the ticker + amount block in the band between the stamp row and
    # the slab, so short-but-wide headlines (no-ticker assets) do not float.
    head_h = ink_h(ft, head)
    block_top = 214 + max(0, (552 - 214 - (head_h + 78)) // 2)
    head_base = block_top + head_h
    d.text((M - 4, head_base), head, font=ft, fill=INK, anchor="ls")

    amount = amount_range(t.amount_min, t.amount_max, t.amount_exact)
    if amount:
        fa, amount = fit(amount, "display", 800, col_w, 70, 40)
        d.text((M, head_base + 78), amount, font=fa, fill=INK, anchor="ls")
    else:
        d.text((M, head_base + 72), "Amount not disclosed", font=body(30, 600), fill=FAINT, anchor="ls")

    # -- bottom slab ------------------------------------------------------------
    top = 575
    _slab(d, TRADE_SIZE, top)
    brand_left = _slab_brand(d, TRADE_SIZE, top, domain)
    sentence = timing_sentence(t)
    max_w = brand_left - 40 - M
    base = top + 62
    if late and days is not None:
        lead = plural(days, "day")
        rest = sentence[len(lead):]
        fs, _ = fit(sentence, "body", 700, max_w, 34, 20)
        d.text((M, base), lead, font=fs, fill=ACCENT_ON_SLAB, anchor="ls")
        d.text((M + text_w(fs, lead) + _space(fs), base), rest.strip(), font=fs, fill=ON_SLAB, anchor="ls")
    else:
        fs, sentence = fit(sentence, "body", 700, max_w, 34, 20)
        d.text((M, base), sentence, font=fs, fill=ON_SLAB, anchor="ls")
    return img


def _space(f: ImageFont.FreeTypeFont) -> int:
    return text_w(f, "a a") - text_w(f, "aa")


# ---------------------------------------------------------------------------
# Member card (1200 x 630)
# ---------------------------------------------------------------------------
def render_member_card(m: MemberCardData, domain: Optional[str] = None) -> bytes:
    with _RENDER_LOCK:
        return _png(_member_image(m, domain or public_domain()))


def _member_image(m: MemberCardData, domain: str) -> Image.Image:
    W, H = MEMBER_SIZE
    img, d = _new(MEMBER_SIZE)

    d.text((M, 72), "Congressional stock trade disclosures", font=body(22, 600), fill=FAINT, anchor="ls")
    name = " ".join((m.name or "Unknown member").split()).upper()
    fn, name = fit(name, "display", 900, W - 2 * M, 150, 56, max_h=112)
    d.text((M - 3, 206), name, font=fn, fill=INK, anchor="ls")

    x = M
    letter = party_letter(m.party)
    if letter:
        draw_chip(d, x, 232, 38, letter)
        x += 38 + 14
    tag = affiliation(m.party, m.state, m.district if (m.chamber or "").lower().startswith("house") else None)
    chamber = chamber_label(m.chamber)
    fa = body(30, 600)
    if tag:
        d.text((x, 264), tag, font=fa, fill=INK, anchor="ls")
        x += text_w(fa, tag) + 18
    if chamber:
        if tag:
            d.rectangle([x, 238, x + 1, 266], fill=LINE)
            x += 18
        d.text((x, 264), chamber, font=body(30, 400), fill=MUTED, anchor="ls")

    d.rectangle([M, 292, W - M, 294], fill=INK)

    col = (W - 2 * M) // 3
    for i in (1, 2):
        cx = M + col * i
        d.rectangle([cx, 316, cx, 522], fill=LINE)

    # trades
    c1 = M
    fv = display(110, 900)
    d.text((c1, 432), f"{m.trade_count:,}", font=fv, fill=INK, anchor="ls")
    d.text((c1, 474), "Trades disclosed", font=body(24, 600), fill=MUTED, anchor="ls")
    if m.last_disclosed:
        d.text((c1, 506), f"Latest {fmt_date(m.last_disclosed)}", font=body(20, 400), fill=FAINT, anchor="ls")

    # average days, with the gauge
    c2 = M + col + col // 2
    avg_late = is_late(m.avg_days)
    draw_gauge(img, c2, 390, 70, 14, m.avg_days, avg_late, label_size=15)
    if m.avg_days is None:
        avg_txt, color = "NO DATA", FAINT
    else:
        n = round(m.avg_days)
        avg_txt, color = f"{n:,} DAY{'' if n == 1 else 'S'}", ACCENT if avg_late else INK
    d.text((c2, 478), avg_txt, font=display(50, 900), fill=color, anchor="ms")
    d.text((c2, 506), "Average time to disclose", font=body(20, 600), fill=MUTED, anchor="ms")

    # late filings
    c3 = M + col * 2 + 32
    d.text((c3, 432), f"{m.late_count:,}", font=fv, fill=ACCENT if m.late_count else INK, anchor="ls")
    d.text((c3, 474), f"Filed past the {DISCLOSURE_LIMIT_DAYS}-day limit", font=body(24, 600), fill=MUTED, anchor="ls")
    d.text((c3, 506), "Amended filings excluded", font=body(20, 400), fill=FAINT, anchor="ls")

    top = 548
    _slab(d, MEMBER_SIZE, top)
    left = _slab_brand(d, MEMBER_SIZE, top, domain)
    fs, line = fit(member_line(m.name, m.chamber, m.party, m.state, m.district), "body", 700, left - 40 - M, 28, 18)
    d.text((M, top + 52), line, font=fs, fill=ON_SLAB, anchor="ls")
    return img


# ---------------------------------------------------------------------------
# Default site card (1200 x 630)
# ---------------------------------------------------------------------------
def render_default_card(domain: Optional[str] = None) -> bytes:
    with _RENDER_LOCK:
        return _png(_default_image(domain or public_domain()))


def _default_image(domain: str) -> Image.Image:
    W, H = DEFAULT_SIZE
    img, d = _new(DEFAULT_SIZE)

    fw = display(132, 900)
    word = "CAPITOLSCOPE"
    cap = ink_h(fw, word)
    mark = round(cap * 0.62)
    d.rectangle([M, 190 - mark, M + mark - 1, 189], fill=ACCENT)
    d.text((M + mark + 22, 190), word, font=fw, fill=INK, anchor="ls")

    fh = display(58, 800)
    d.text((M, 330), "Congressional stock trades,", font=fh, fill=INK, anchor="ls")
    d.text((M, 392), "and how long they took to disclose.", font=fh, fill=INK, anchor="ls")
    d.text(
        (M, 448),
        "Every House and Senate periodic transaction report.",
        font=body(26, 400),
        fill=MUTED,
        anchor="ls",
    )

    gcx, gcy = 1000, 318
    draw_gauge(img, gcx, gcy, 112, 20, DISCLOSURE_LIMIT_DAYS, False, label_size=17)
    d.text((gcx, gcy + 104), f"{DISCLOSURE_LIMIT_DAYS} DAYS", font=display(64, 900), fill=INK, anchor="ms")
    d.text((gcx, gcy + 138), "the STOCK Act limit", font=body(20, 500), fill=FAINT, anchor="ms")

    top = 540
    _slab(d, DEFAULT_SIZE, top)
    left = _slab_brand(d, DEFAULT_SIZE, top, domain)
    fs, line = fit("Public disclosures, plainly shown.", "body", 700, left - 40 - M, 28, 18)
    d.text((M, top + 56), line, font=fs, fill=ON_SLAB, anchor="ls")
    return img
