"""House PTR text parsing: multi-line asset cells and wrapped amounts."""

from datetime import date

import pytest

from domains.congressional.ptr_pdf import parse_amount, parse_ptr_text

pytestmark = pytest.mark.unit

# Shape of pdfplumber output for a real filing (20033762), incl. the NUL-glyph labels.
SAMPLE = """Filing ID #20033762
Name: Hon. Gilbert Cisneros
ID Owner Asset Transaction Date Notification Amount Cap.
Abbott Laboratories Common Stock S (partial) 12/19/2025 01/09/2026 $1,001 - $15,000
(ABT) [ST]
F\x00\x00\x00\x00\x00 S\x00\x00\x00\x00\x00: New
S\x00\x00\x00\x00\x00\x00\x00\x00\x00 O\x00: 150 Main Street Trust > Bank of America
Advanced Micro Devices, Inc. (AMD) S (partial) 12/19/2025 01/09/2026 $15,001 -
[ST] $50,000
F      S     : New
Agios Pharmaceuticals, Inc. - P 12/11/2025 01/09/2026 $1,001 - $15,000
Common Stock (AGIO) [ST]
F      S     : New
AJINOMOTO CO INC (AJINF) [ST] S 12/26/2025 01/09/2026 $1,001 - $15,000
F      S     : New
D          : Ticker 2802 JP
SP US Treasury Note 2.25% due P 03/01/2024 03/15/2024 $50,001 - $100,000
11/15/2027 [GS]
F      S     : New
"""


@pytest.fixture(scope="module")
def rows():
    return parse_ptr_text(SAMPLE)


def test_all_rows_found(rows):
    assert len(rows) == 5


def test_ticker_on_wrapped_line(rows):
    abt = rows[0]
    assert (abt.ticker, abt.type_code, abt.transaction_type) == ("ABT", "ST", "S")
    assert abt.asset == "Abbott Laboratories Common Stock (ABT)"
    assert (abt.transaction_date, abt.notification_date) == (date(2025, 12, 19), date(2026, 1, 9))


def test_wrapped_amount_is_stitched(rows):
    amd = rows[1]
    assert (amd.amount_min_cents, amd.amount_max_cents) == (1500100, 5000000)
    assert amd.ticker == "AMD" and amd.type_code == "ST"


def test_asset_name_continues_across_lines(rows):
    assert rows[2].asset == "Agios Pharmaceuticals, Inc. - Common Stock (AGIO)"


def test_description_line(rows):
    assert rows[3].ticker == "AJINF" and rows[3].description == "Ticker 2802 JP"


def test_owner_and_government_security_code(rows):
    t = rows[4]
    assert t.owner == "SP" and t.type_code == "GS" and t.ticker is None
    assert t.asset == "US Treasury Note 2.25% due 11/15/2027"


@pytest.mark.parametrize("raw,expected", [
    ("$1,001 - $15,000", (100100, 1500000)),
    ("$15,001 -", (1500100, None)),
    ("Over $50,000,000", (5000000100, None)),
    ("Spouse/DC Over $1,000,000", (100000100, None)),
    ("", (None, None)),
])
def test_parse_amount(raw, expected):
    assert parse_amount(raw) == expected


# Older layout (2014-era): single-digit dates, garbled glyph case in labels and
# tickers, ticker wrapped onto its own line, numeric line ids.
OLD = """Name: Mr. Lamar Smith
apple Inc. (aaPL) S 12/10/2013 01/2/2014 $1,001 - $15,000
FILINg STaTUS: New
SUbHoLdINg oF: MERRILL LYNCH INVESTMENT aCCoUNTS
Cameron International Corporation S 12/11/2013 01/2/2014 $1,001 - $15,000
(CaM)
FILINg STaTUS: New
2000080752 FedEx Corporation (FDX) P 3/4/2015 3/20/2015 $15,001 - $50,000
FILINg STaTUS: New
"""


def test_old_layout():
    rows = parse_ptr_text(OLD)
    assert [r.ticker for r in rows] == ["AAPL", "CAM", "FDX"]
    assert rows[0].notification_date == date(2014, 1, 2)
    assert rows[1].asset == "Cameron International Corporation (CaM)"
    assert rows[2].asset == "FedEx Corporation (FDX)"
    assert all("STATUS" not in r.asset.upper() for r in rows)
