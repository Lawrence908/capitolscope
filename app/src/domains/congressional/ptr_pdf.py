"""
Parse House periodic transaction report (PTR) PDFs into full trade rows.

Electronic House PTRs render each transaction as one line ending in
"<type> <trade date> <notification date> <amount>", with the asset cell
wrapping onto following lines that carry the "(TICKER) [TYPE]" codes and
sometimes the tail of the amount ("$15,001 -" / "[ST] $50,000"). The record
ends at the "Filing Status" line. The old parser kept only the first line,
which is why stored asset text is cut at ~30 characters and the ticker was
lost. This parser stitches the continuation lines back on.

Pure text processing (``parse_ptr_text``) is separate from PDF extraction
(``parse_ptr_pdf``) so it can be unit-tested without fixtures.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional

_TXN = re.compile(
    r"^(?:(?P<owner>SP|JT|DC)\s+)?(?P<asset>.+?)\s+"
    r"(?P<type>P|S|E)(?:\s+\((?:partial|full)\))?\s+"
    r"(?P<tdate>\d{2}/\d{2}/\d{4})\s+(?P<ndate>\d{2}/\d{2}/\d{4})\s+"
    r"(?P<amount>\$[\d,]+(?:\s*-\s*(?:\$[\d,]+)?)?|Spouse/DC Over \$1,000,000|Over \$[\d,]+)\s*$"
)
# "F<nul..> S<nul..>: New" in extracted text (the label glyphs drop out).
_STATUS = re.compile(r"^F[\s\x00]+S[\s\x00]*:")
_SUBHOLDING = re.compile(r"^S[\s\x00]+O[\s\x00]*:")
_DESCRIPTION = re.compile(r"^D[\s\x00]+:")
_TYPE_CODE = re.compile(r"\[([A-Z]{2})\]")
_PAREN_TICKER = re.compile(r"\(([A-Z][A-Z0-9.\-]{0,9})\)")
_AMOUNT_TAIL = re.compile(r"\$[\d,]+\s*$")


@dataclass(frozen=True)
class PtrRow:
    owner: Optional[str]
    asset: str               # full asset text, without the [TYPE] code
    ticker: Optional[str]    # from "(TICKER)" when present
    type_code: Optional[str]  # House asset type code, e.g. ST, GS, OP, EF
    transaction_type: str    # P / S / E
    transaction_date: date
    notification_date: date
    amount_min_cents: Optional[int]
    amount_max_cents: Optional[int]
    description: Optional[str] = None


def _d(s: str) -> date:
    return datetime.strptime(s, "%m/%d/%Y").date()


def parse_amount(text: str) -> tuple[Optional[int], Optional[int]]:
    """'$15,001 - $50,000' -> (1500100, 5000000) cents; 'Over $50,000,000' -> (5000000100, None)."""
    nums = [int(n.replace(",", "")) for n in re.findall(r"\$([\d,]+)", text or "")]
    if not nums:
        return None, None
    if text.strip().lower().startswith(("over", "spouse/dc over")):
        return (nums[0] + 1) * 100, None
    if len(nums) == 1:
        return nums[0] * 100, (nums[0] * 100 if "-" not in text else None)
    return nums[0] * 100, nums[1] * 100


def parse_ptr_text(text: str) -> List[PtrRow]:
    lines = [ln.replace("\x00", " ").rstrip() for ln in (text or "").splitlines()]
    rows: List[PtrRow] = []
    cur = None  # dict being assembled

    def flush():
        nonlocal cur
        if cur is None:
            return
        asset = re.sub(r"\s+", " ", " ".join(cur["asset"])).strip()
        codes = _TYPE_CODE.findall(asset)
        tickers = _PAREN_TICKER.findall(asset)
        asset_clean = _TYPE_CODE.sub("", asset).strip()
        amin, amax = parse_amount(cur["amount"])
        rows.append(PtrRow(
            owner=cur["owner"],
            asset=asset_clean,
            ticker=tickers[-1] if tickers else None,
            type_code=codes[-1] if codes else None,
            transaction_type=cur["type"],
            transaction_date=cur["tdate"],
            notification_date=cur["ndate"],
            amount_min_cents=amin,
            amount_max_cents=amax,
            description=cur.get("description"),
        ))
        cur = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        m = _TXN.match(line)
        if m:
            flush()
            cur = {
                "owner": m.group("owner"),
                "asset": [m.group("asset")],
                "type": m.group("type"),
                "tdate": _d(m.group("tdate")),
                "ndate": _d(m.group("ndate")),
                "amount": m.group("amount"),
                "closed": False,
            }
            continue
        if cur is None:
            continue
        if _STATUS.match(line) or _SUBHOLDING.match(line):
            cur["closed"] = True
            continue
        if _DESCRIPTION.match(line):
            cur["description"] = line.split(":", 1)[1].strip()
            cur["closed"] = True
            continue
        if cur["closed"]:
            continue
        # Continuation of the asset cell; may also carry the amount's tail.
        if cur["amount"].rstrip().endswith("-"):
            tail = _AMOUNT_TAIL.search(line)
            if tail:
                cur["amount"] = f"{cur['amount']} {tail.group(0).strip()}"
                line = line[: tail.start()].strip()
        if line:
            cur["asset"].append(line)
    flush()
    return rows


def parse_ptr_pdf(path: str) -> List[PtrRow]:
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        text = "\n".join((page.extract_text() or "") for page in pdf.pages)
    return parse_ptr_text(text)
