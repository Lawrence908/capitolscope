"""
Social card rendering (domains.social.cards), the text helpers behind it
(domains.social.formatting) and the PNG disk cache (domains.social.card_cache).
"""

import io
from datetime import date

import pytest
from PIL import Image

from domains.social import card_cache
from domains.social.cards import (
    ACCENT,
    DEFAULT_SIZE,
    INK,
    LATE_TRACK,
    MEMBER_SIZE,
    TRADE_SIZE,
    angle_for_days,
    render_default_card,
    render_member_card,
    render_trade_card,
)
from domains.social.formatting import (
    MemberCardData,
    TradeCardData,
    affiliation,
    amount_range,
    clean_asset_name,
    is_late,
    member_description,
    member_line,
    short_asset_label,
    timing_sentence,
    trade_description,
    trade_headline,
    trade_verb,
)

pytestmark = pytest.mark.unit


def _trade(**kw) -> TradeCardData:
    base = dict(
        member_name="Tommy Tuberville",
        chamber="Senate",
        party="R",
        state="AL",
        ticker="INTC",
        asset_name="Intel Corporation",
        transaction_type="P",
        amount_min=10_000_100,
        amount_max=25_000_000,
        transaction_date=date(2024, 5, 7),
        notification_date=date(2026, 8, 5),
        filing_status="N",
    )
    base.update(kw)
    return TradeCardData(**base)


def _img(png: bytes) -> Image.Image:
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    return Image.open(io.BytesIO(png)).convert("RGB")


# ---------------------------------------------------------------------------
# formatting
# ---------------------------------------------------------------------------
class TestFormatting:
    def test_amount_range_is_cents(self):
        assert amount_range(10_000_100, 25_000_000) == "$100,001 to $250,000"
        assert amount_range(100_100, 1_500_000) == "$1,001 to $15,000"
        assert amount_range(5_000_000_100, None) == "$50,000,001+"
        assert amount_range(None, None, 1_234_500) == "$12,345"
        assert amount_range(None, None) is None

    def test_member_line_and_affiliation(self):
        assert member_line("Tommy Tuberville", "Senate", "R", "AL") == "Sen. Tommy Tuberville, R-AL"
        assert member_line("Rudy Yakym", "House", "Republican", "IN", "2") == "Rep. Rudy Yakym, R-IN-2"
        assert member_line("Angus King", "Senate", "I", "ME", "5") == "Sen. Angus King, I-ME"
        assert member_line("Someone", None, None, None) == "Someone"
        assert affiliation("Democratic", "nj", "05") == "D-NJ-5"

    def test_trade_verb(self):
        assert trade_verb("P") == "BOUGHT"
        assert trade_verb("S") == "SOLD"
        assert trade_verb("S (partial)") == "SOLD"
        assert trade_verb("E") == "EXCHANGED"
        assert trade_verb(None) == "TRADED"

    def test_timing_sentences(self):
        assert timing_sentence(_trade()) == "820 days to disclose. Limit: 45."
        on_time = _trade(transaction_date=date(2026, 1, 1), notification_date=date(2026, 1, 13))
        assert timing_sentence(on_time) == "Disclosed in 12 days. Limit: 45."
        same = _trade(transaction_date=date(2026, 1, 1), notification_date=date(2026, 1, 1))
        assert timing_sentence(same).startswith("Disclosed the same day")
        assert timing_sentence(_trade(filing_status="A")) == "Amended filing."
        assert timing_sentence(_trade(transaction_date=None)) == "Disclosure date not on record."

    def test_amendments_are_never_late(self):
        assert is_late(820, "N")
        assert not is_late(820, "A")
        assert not is_late(45)
        assert is_late(46)
        assert not is_late(None)

    def test_asset_name_cleanup(self):
        assert clean_asset_name("Salesforce Inc (CRM)") == "Salesforce Inc"
        assert clean_asset_name("WesBanco, Inc. - Common Stock") == "WesBanco, Inc."
        assert clean_asset_name("   ") is None
        assert short_asset_label("Treasury Bill (6-Week, Matures 12/01/2026)") == "TREASURY BILL"
        assert short_asset_label(None) == "UNDISCLOSED ASSET"

    def test_text_has_no_emdash(self):
        t = _trade()
        m = MemberCardData(name="A B", chamber="House", party="D", state="CA", trade_count=3, avg_days=50.2, late_count=1)
        for s in (trade_headline(t), trade_description(t), member_description(m), timing_sentence(t)):
            assert "\u2014" not in s and "\u2013" not in s

    def test_descriptions(self):
        assert trade_headline(_trade()) == "Sen. Tommy Tuberville (R-AL) bought INTC"
        d = trade_description(_trade())
        assert "$100,001 to $250,000" in d and "Intel Corporation (INTC)" in d and "820 days" in d
        m = MemberCardData(name="X", trade_count=1, avg_days=None, late_count=0)
        assert member_description(m) == "1 disclosed trade. No filings past the 45-day limit."
        assert member_description(MemberCardData(name="X")) == "No stock trade disclosures on record."


# ---------------------------------------------------------------------------
# gauge geometry (mirrors frontend bulletin.tsx)
# ---------------------------------------------------------------------------
class TestGaugeGeometry:
    @pytest.mark.parametrize(
        "days,deg",
        [(0, 180.0), (15, 130.0), (45, 30.0), (45 + 90, 15.0), (45 + 180, 0.0), (5000, 0.0), (-3, 180.0)],
    )
    def test_angle_for_days(self, days, deg):
        assert angle_for_days(days) == pytest.approx(deg)


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------
def _close(px, color, tol=40):
    return all(abs(a - b) <= tol for a, b in zip(px, color))


class TestRendering:
    def test_trade_card_size_and_late_zone(self):
        img = _img(render_trade_card(_trade(), domain="example.test"))
        assert img.size == TRADE_SIZE
        # A point inside the late band (math angle 15 deg on the gauge arc) is solid red when late.
        import math

        cx, cy, r = 990, 318, 116
        x, y = cx + r * math.cos(math.radians(15)), cy - r * math.sin(math.radians(15))
        assert _close(img.getpixel((round(x), round(y))), ACCENT)
        # Same point on an on-time filing shows the pale late track instead.
        ok = _img(render_trade_card(_trade(transaction_date=date(2026, 8, 1)), domain="example.test"))
        assert _close(ok.getpixel((round(x), round(y))), LATE_TRACK)
        # The footer slab is ink.
        assert _close(img.getpixel((5, TRADE_SIZE[1] - 5)), INK, tol=5)

    def test_amended_filing_never_red(self):
        img = _img(render_trade_card(_trade(filing_status="A"), domain="example.test"))
        import math

        cx, cy, r = 990, 318, 116
        x, y = cx + r * math.cos(math.radians(15)), cy - r * math.sin(math.radians(15))
        assert _close(img.getpixel((round(x), round(y))), LATE_TRACK)

    @pytest.mark.parametrize(
        "kw",
        [
            dict(ticker=None, asset_name="Treasury Bill (6-Week, Matures 12/01/2026)"),
            dict(ticker="BRK.B", asset_name="Berkshire Hathaway Inc. Class B " * 6),
            dict(ticker="WWWWWWWWWWWWWWWWWWWW"),
            dict(member_name="Maximilian Bartholomew Featherstonehaugh-Cholmondeley the Third of Somewhere"),
            dict(transaction_date=None, notification_date=None),
            dict(party=None, chamber=None, state=None),
            dict(amount_min=None, amount_max=None),
            dict(transaction_type="E"),
        ],
    )
    def test_trade_card_edge_cases_render(self, kw):
        img = _img(render_trade_card(_trade(**kw), domain="example.test"))
        assert img.size == TRADE_SIZE

    def test_member_card(self):
        m = MemberCardData(
            name="Tommy Tuberville", chamber="Senate", party="R", state="AL",
            trade_count=168, avg_days=664.0, late_count=157, last_disclosed=date(2026, 8, 5),
        )
        assert _img(render_member_card(m, domain="example.test")).size == MEMBER_SIZE
        empty = MemberCardData(name="New Member")
        assert _img(render_member_card(empty, domain="example.test")).size == MEMBER_SIZE

    def test_default_card(self):
        assert _img(render_default_card(domain="example.test")).size == DEFAULT_SIZE


# ---------------------------------------------------------------------------
# disk cache
# ---------------------------------------------------------------------------
class TestCardCache:
    def test_hash_tracks_content_and_domain(self):
        a = card_cache.content_hash(_trade(), "a.test")
        assert a == card_cache.content_hash(_trade(), "a.test")
        assert a != card_cache.content_hash(_trade(amount_max=50_000_000), "a.test")
        assert a != card_cache.content_hash(_trade(), "b.test")

    def test_cache_dir_defaults_next_to_data_dir(self, monkeypatch):
        monkeypatch.delenv("OG_CACHE_DIR", raising=False)
        monkeypatch.setenv("CAPITOLSCOPE_DATA_DIR", "/app/data/congress")
        assert str(card_cache.cache_dir()) == "/app/data/og"

    def test_get_or_render_caches_and_prunes(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OG_CACHE_DIR", str(tmp_path))
        calls = []

        def render():
            calls.append(1)
            return b"png-bytes"

        png, hit = card_cache.get_or_render("trade", "abc", "h1", render)
        assert (png, hit) == (b"png-bytes", False)
        png, hit = card_cache.get_or_render("trade", "abc", "h1", render)
        assert (png, hit) == (b"png-bytes", True) and len(calls) == 1
        card_cache.get_or_render("trade", "abc", "h2", render)
        assert sorted(p.name for p in (tmp_path / "trade").glob("*.png")) == ["abc-h2.png"]

    def test_unwritable_cache_still_renders(self, monkeypatch, tmp_path):
        blocker = tmp_path / "file"
        blocker.write_text("x")
        monkeypatch.setenv("OG_CACHE_DIR", str(blocker / "sub"))
        png, hit = card_cache.get_or_render("trade", "abc", "h1", lambda: b"png")
        assert (png, hit) == (b"png", False)
