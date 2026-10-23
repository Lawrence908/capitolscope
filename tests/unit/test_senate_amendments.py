"""Senate eFD amendment handling (fetch/senate_fetcher.py).

An amended PTR is re-filed long after the original; its submitted date must
not be used as the disclosure date or on-time trades look years late.
"""

import pytest

from domains.congressional.fetch.senate_fetcher import SenateDisclosureFetcher

pytestmark = pytest.mark.unit

LINK = '<a href="/search/view/ptr/0a25588d-a3f8-4ed6-971a-706097f78e3a/" target="_blank">{}</a>'

PTR_HTML = """
<table><tbody>
<tr><td>1</td><td>05/07/2024</td><td>Self</td><td>INTC</td><td>Intel Corporation</td>
<td>Stock</td><td>Purchase</td><td>$100,001 - $250,000</td><td>--</td></tr>
</tbody></table>
"""


def _row(title, submitted="08/05/2026"):
    return ["Thomas H", "Tuberville", "Tuberville, Tommy (Senator)", LINK.format(title), submitted]


class TestParseSearchRow:
    def test_amendment_number_and_original_date(self):
        parsed = SenateDisclosureFetcher._parse_search_row(
            _row("Periodic Transaction Report for 06/14/2024 (Amendment 1)")
        )
        assert parsed["amendment"] == 1
        assert parsed["original_filed_date"] == "06/14/2024"
        assert parsed["submitted_date"] == "08/05/2026"

    def test_original_report(self):
        parsed = SenateDisclosureFetcher._parse_search_row(
            _row("Periodic Transaction Report for 07/16/2026", submitted="07/16/2026")
        )
        assert parsed["amendment"] == 0
        assert parsed["original_filed_date"] == "07/16/2026"


class _FakeResp:
    def __init__(self, text):
        self.text = text
        self.status_code = 200

    def raise_for_status(self):
        pass


class _FakeSession:
    def get(self, url, timeout=None):
        return _FakeResp(PTR_HTML)


def _fetcher():
    fetcher = SenateDisclosureFetcher.__new__(SenateDisclosureFetcher)
    fetcher.session = _FakeSession()
    fetcher.timeout = 5
    return fetcher


class TestParseElectronicPtr:
    def test_amendment_uses_original_filing_date(self):
        report = SenateDisclosureFetcher._parse_search_row(
            _row("Periodic Transaction Report for 06/14/2024 (Amendment 1)")
        )
        (row,) = _fetcher()._parse_electronic_ptr(report)
        assert row["Notification Date"] == "06/14/2024"
        assert row["filing_status"] == "Amendment"
        assert row["Transaction Date"] == "05/07/2024"

    def test_original_uses_submitted_date(self):
        report = SenateDisclosureFetcher._parse_search_row(
            _row("Periodic Transaction Report for 07/16/2026", submitted="07/16/2026")
        )
        (row,) = _fetcher()._parse_electronic_ptr(report)
        assert row["Notification Date"] == "07/16/2026"
        assert row["filing_status"] == "New"
