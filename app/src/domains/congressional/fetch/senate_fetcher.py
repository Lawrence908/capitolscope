"""
Senate disclosure source fetcher (phase 2).

Implements the Senate Electronic Financial Disclosure (eFD) workflow:

  1. Establish a session and accept the eFD access agreement (CSRF-guarded).
  2. Query the server-side DataTables endpoint for Periodic Transaction
     Reports (PTRs) submitted within a lookback window.
  3. For each *electronic* PTR, parse its transaction table into rows and
     append them to a per-year CSV (``<year>SFD.csv``) using the same column
     schema the congressional importer already understands. *Paper* PTRs are
     scanned images and are recorded as skipped (no reliable text to parse).

The raw search results are also persisted under ``raw/senate`` for auditing.

Everything here is defensive: network/parse failures for an individual report
are collected and reported rather than aborting the whole source, so the
orchestrator can classify the run as ``partial`` and alert.
"""

from __future__ import annotations

import csv as pycsv
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from .base import atomic_write_json, ensure_dir

logger = logging.getLogger(__name__)

# efdsearch.senate.gov sits behind Akamai, which blocks non-browser TLS
# fingerprints (plain `requests`/`curl` get a 403 "Access Denied" even with
# browser headers). curl_cffi impersonates a real Chrome TLS/JA3 fingerprint
# and is let through. Fall back to `requests` only so the module still imports
# in environments without curl_cffi (the fetch will then 403 and be reported as
# a failed source by the orchestrator rather than crashing).
try:
    from curl_cffi import requests as _http

    _IMPERSONATE = os.environ.get("CAPITOLSCOPE_SENATE_IMPERSONATE", "chrome120")
    _HAS_CURL_CFFI = True
except ImportError:  # pragma: no cover
    import requests as _http  # type: ignore

    _IMPERSONATE = None
    _HAS_CURL_CFFI = False

BASE = "https://efdsearch.senate.gov"
HOME_URL = f"{BASE}/search/home/"
SEARCH_PAGE_URL = f"{BASE}/search/"
REPORT_DATA_URL = f"{BASE}/search/report/data/"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# CSV columns understood by CongressionalDataIngestion._parse_csv_row.
CSV_FIELDS = [
    "DocID",
    "Prefix",
    "FirstName",
    "LastName",
    "Asset",
    "Transaction Type",
    "Owner",
    "Amount",
    "Transaction Date",
    "Notification Date",
    "Description",
    "filing_status",
    "cap_gains_over_200",
]

# Report type 11 == Periodic Transaction Report in the eFD taxonomy.
PTR_REPORT_TYPE = "11"

# The importer's validator only accepts single-letter transaction codes
# (P/S/E); Senate PTRs spell them out ("Purchase", "Sale (Full)", ...).
def _map_txn_type(raw: str) -> str:
    t = (raw or "").strip().lower()
    if t.startswith("purchase"):
        return "P"
    if t.startswith("sale"):
        return "S"
    if t.startswith("exchange"):
        return "E"
    return (raw or "").strip()


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


class SenateDisclosureFetcher:
    def __init__(self, raw_dir: Path, csv_dir: Path):
        self.raw_dir = ensure_dir(raw_dir / "senate")
        self.csv_dir = ensure_dir(csv_dir)
        self.delay = _env_float("CAPITOLSCOPE_SENATE_FETCH_DELAY", 1.5)
        self.lookback_days = _env_int("CAPITOLSCOPE_SENATE_LOOKBACK_DAYS", 45)
        self.max_reports = _env_int("CAPITOLSCOPE_SENATE_MAX_REPORTS", 150)
        self.timeout = _env_int("CAPITOLSCOPE_SENATE_TIMEOUT_SECONDS", 45)
        if _HAS_CURL_CFFI:
            self.session = _http.Session(impersonate=_IMPERSONATE)
        else:
            self.session = _http.Session()
            self.session.headers.update({"User-Agent": USER_AGENT})

    # -- auth ---------------------------------------------------------------

    def _csrf(self) -> str:
        resp = self.session.get(HOME_URL, timeout=self.timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        token_el = soup.find("input", {"name": "csrfmiddlewaretoken"})
        if not token_el or not token_el.get("value"):
            raise RuntimeError("Senate eFD: could not locate csrfmiddlewaretoken")
        return token_el["value"]

    def _accept_agreement(self) -> str:
        token = self._csrf()
        resp = self.session.post(
            HOME_URL,
            data={
                "csrfmiddlewaretoken": token,
                "prohibition_agreement": "1",
            },
            headers={"Referer": HOME_URL},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        # After accepting, the csrftoken cookie is what the data endpoint wants.
        return self.session.cookies.get("csrftoken", token)

    # -- search -------------------------------------------------------------

    def _search_ptrs(self, csrf_token: str) -> List[Dict[str, Any]]:
        start = (datetime.utcnow() - timedelta(days=self.lookback_days)).strftime("%m/%d/%Y")
        end = datetime.utcnow().strftime("%m/%d/%Y")
        collected: List[Dict[str, Any]] = []
        offset = 0
        page_size = 100

        while len(collected) < self.max_reports:
            payload = {
                "draw": str(offset // page_size + 1),
                "start": str(offset),
                "length": str(page_size),
                "report_types": f"[{PTR_REPORT_TYPE}]",
                "filer_types": "[]",
                "submitted_start_date": f"{start} 00:00:00",
                "submitted_end_date": f"{end} 23:59:59",
                "candidate_state": "",
                "senator_state": "",
                "office_id": "",
                "first_name": "",
                "last_name": "",
            }
            resp = self.session.post(
                REPORT_DATA_URL,
                data=payload,
                headers={
                    "Referer": SEARCH_PAGE_URL,
                    "X-CSRFToken": csrf_token,
                    "X-Requested-With": "XMLHttpRequest",
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            body = resp.json()
            rows = body.get("data", [])
            if not rows:
                break
            for row in rows:
                parsed = self._parse_search_row(row)
                if parsed:
                    collected.append(parsed)
            total = body.get("recordsFiltered", 0)
            offset += page_size
            if offset >= total:
                break
            time.sleep(self.delay)

        return collected[: self.max_reports]

    @staticmethod
    def _parse_search_row(row: List[str]) -> Optional[Dict[str, Any]]:
        # DataTables row: [first, last, office, report_link_html, date_str]
        if len(row) < 5:
            return None
        first, last, office, link_html, date_str = row[0], row[1], row[2], row[3], row[4]
        href_match = re.search(r'href="([^"]+)"', link_html)
        text_match = re.search(r">([^<]+)</a>", link_html)
        if not href_match:
            return None
        href = href_match.group(1)
        report_kind = (text_match.group(1).strip() if text_match else "").lower()
        is_electronic = "/ptr/" in href  # paper filings route to /paper/
        uuid_match = re.search(r"/ptr/([0-9a-fA-F-]+)/?", href)
        return {
            "first_name": first.strip(),
            "last_name": last.strip(),
            "office": office.strip(),
            "url": href if href.startswith("http") else f"{BASE}{href}",
            "doc_id": uuid_match.group(1) if uuid_match else href.rstrip("/").rsplit("/", 1)[-1],
            "submitted_date": date_str.strip(),
            "is_electronic": is_electronic,
            "report_kind": report_kind,
        }

    # -- report parsing -----------------------------------------------------

    def _parse_electronic_ptr(self, report: Dict[str, Any]) -> List[Dict[str, str]]:
        resp = self.session.get(report["url"], timeout=self.timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table")
        if not table or not table.find("tbody"):
            return []

        rows: List[Dict[str, str]] = []
        for tr in table.find("tbody").find_all("tr"):
            # Collapse the whitespace/newlines the eFD HTML embeds in cells.
            cells = [re.sub(r"\s+", " ", td.get_text(" ", strip=True)).strip() for td in tr.find_all("td")]
            if len(cells) < 8:
                continue
            # eFD electronic PTR columns:
            # #, Transaction Date, Owner, Ticker, Asset Name, Asset Type, Type, Amount, Comment
            txn_date, owner, ticker, asset_name = cells[1], cells[2], cells[3], cells[4]
            txn_type, amount = cells[6], cells[7]
            comment = cells[8] if len(cells) > 8 else ""
            asset = asset_name
            if ticker and ticker not in ("--", "N/A"):
                asset = f"{asset_name} ({ticker})".strip()
            rows.append(
                {
                    "DocID": report["doc_id"],
                    "Prefix": "",
                    "FirstName": report["first_name"],
                    "LastName": report["last_name"],
                    "Asset": asset,
                    "Transaction Type": _map_txn_type(txn_type),
                    "Owner": owner,
                    "Amount": amount,
                    "Transaction Date": txn_date,
                    "Notification Date": report.get("submitted_date", ""),
                    "Description": comment,
                    "filing_status": "New",
                    "cap_gains_over_200": "false",
                }
            )
        return rows

    # -- csv output ---------------------------------------------------------

    def _write_year_csvs(self, rows_by_year: Dict[int, List[Dict[str, str]]]) -> List[str]:
        written: List[str] = []
        for year, rows in rows_by_year.items():
            if not rows:
                continue
            path = self.csv_dir / f"{year}SFD.csv"
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = pycsv.DictWriter(fh, fieldnames=CSV_FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            written.append(str(path))
        return written

    @staticmethod
    def _year_of(report: Dict[str, Any]) -> int:
        for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(report.get("submitted_date", "").split()[0], fmt).year
            except (ValueError, IndexError):
                continue
        return datetime.utcnow().year

    # -- entrypoint ---------------------------------------------------------

    def sync(self) -> Dict[str, Any]:
        failed: List[str] = []
        skipped_paper: List[str] = []
        rows_by_year: Dict[int, List[Dict[str, str]]] = {}
        parsed_reports = 0
        total_transactions = 0

        try:
            csrf_token = self._accept_agreement()
        except Exception as exc:
            logger.exception("Senate eFD: authentication failed")
            return {
                "source": "senate",
                "status": "failed",
                "error": f"authentication failed: {exc}",
                "downloaded_files": [],
                "existing_files": [],
                "failed_years": [],
            }

        try:
            reports = self._search_ptrs(csrf_token)
        except Exception as exc:
            logger.exception("Senate eFD: PTR search failed")
            return {
                "source": "senate",
                "status": "failed",
                "error": f"search failed: {exc}",
                "downloaded_files": [],
                "existing_files": [],
                "failed_years": [],
            }

        # Persist raw search results for audit/checkpointing.
        stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        atomic_write_json(self.raw_dir / f"search_{stamp}.json", {"reports": reports})

        for report in reports:
            if not report.get("is_electronic"):
                skipped_paper.append(report["doc_id"])
                continue
            try:
                txns = self._parse_electronic_ptr(report)
                if txns:
                    rows_by_year.setdefault(self._year_of(report), []).extend(txns)
                    total_transactions += len(txns)
                parsed_reports += 1
            except Exception as exc:
                logger.warning("Senate eFD: failed to parse PTR %s: %s", report.get("doc_id"), exc)
                failed.append(report.get("doc_id", "unknown"))
            time.sleep(self.delay)

        written = self._write_year_csvs(rows_by_year)

        status = "success"
        if failed and not written:
            status = "failed"
        elif failed:
            status = "partial"

        return {
            "source": "senate",
            "status": status,
            "reports_found": len(reports),
            "electronic_parsed": parsed_reports,
            "transactions_written": total_transactions,
            "csv_files": written,
            "downloaded_files": written,
            "existing_files": [],
            "skipped_paper_reports": skipped_paper,
            "failed_reports": failed,
            "failed_years": [],
            "lookback_days": self.lookback_days,
        }
