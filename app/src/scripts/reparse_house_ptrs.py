#!/usr/bin/env python3
"""
Re-fetch and re-parse House PTR PDFs to restore full asset text and tickers.

For each House filing that still has trades without a matched security (or
every House filing with --all-filings), this downloads the PTR PDF (cached
under data/congress/pdf/), parses it with domains.congressional.ptr_pdf
(multi-line asset cells), and matches each parsed row to the stored trade:
same filing, trade date, transaction type and lower amount bound, and the
stored (truncated) text must be a prefix of the full text. Unique matches
get the full asset text and, when SecurityMatcher validates the ticker with
the full text, the security link.

  python scripts/reparse_house_ptrs.py --download-only     # fetch PDFs only
  python scripts/reparse_house_ptrs.py                      # dry run report
  python scripts/reparse_house_ptrs.py --apply              # write (backs up first)
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

DATA_DIR = Path(os.environ.get("CAPITOLSCOPE_DATA_DIR", "/app/data/congress"))
PDF_DIR = DATA_DIR / "pdf"
BACKUP_DIR = Path(os.environ.get("CAPITOLSCOPE_BACKUP_DIR", "/app/data/backups"))
PTR_URL = "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/{doc_id}.pdf"
USER_AGENT = "CapitolScope disclosure research (capitolscope@gmail.com)"

# House PTR asset type codes -> congressional_trades.asset_type categories.
TYPE_CODE_CATEGORY = {
    "ST": "STOCK", "EF": "ETF", "MF": "MUTUAL_FUND", "OP": "OPTION",
    "GS": "BOND", "CS": "BOND", "AB": "BOND", "BA": "CASH",
    "PS": "PRIVATE", "OI": "PRIVATE", "PE": "PRIVATE", "HN": "PRIVATE",
    "CT": "CRYPTOCURRENCY", "RE": "REAL_ESTATE", "RS": "REIT",
    "OT": "OTHER", "IH": "OTHER", "OL": "OTHER", "VA": "OTHER", "WU": "OTHER",
}


_GENERIC = {"the", "inc", "corp", "corporation", "co", "company", "common", "stock", "class", "group",
            "holdings", "holding", "ltd", "plc", "sa", "nv", "ag", "trust", "fund", "shares", "of", "and",
            "unsponsored", "sponsored", "adr", "ads"}


def _sig(name: Optional[str]) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9]+", (name or "").lower()) if t not in _GENERIC and len(t) > 1]


def names_consistent(asset_text: str, company: str) -> bool:
    """The listed company name must start like the filed asset text.

    Guards against reused tickers (Spectra Energy's SE is now Sea Ltd).
    """
    a = _sig(re.sub(r"\([^)]*\)", " ", asset_text))
    b = _sig(company)
    if not a or not b:
        return False
    return a[0] == b[0] or (len(a[0]) >= 4 and (b[0].startswith(a[0]) or a[0].startswith(b[0])))


def norm(s: Optional[str]) -> str:
    """Comparable form: no leading numeric line id, alphanumerics only, lower case."""
    s = re.sub(r"^\s*\d{6,}\s+", "", s or "")
    return re.sub(r"[^a-z0-9]", "", s.lower())


def filing_years() -> Dict[str, str]:
    years: Dict[str, str] = {}
    for f in glob.glob(str(DATA_DIR / "csv" / "*FD_docIDlist.csv")):
        with open(f, newline="", encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh):
                if (r.get("Year") or "").strip():
                    years[(r.get("DocID") or "").strip()] = r["Year"].strip()
    return years


def target_docs(session, all_filings: bool) -> List[str]:
    where = "" if all_filings else "AND security_id IS NULL"
    return [r[0] for r in session.execute(text(
        f"SELECT DISTINCT doc_id FROM congressional_trades WHERE doc_id ~ '^[0-9]+$' {where} ORDER BY 1"
    ))]


def download(docs: List[str], years: Dict[str, str], delay: float = 0.6) -> Counter:
    import httpx

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    stats: Counter = Counter()
    with httpx.Client(timeout=60, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        for i, doc in enumerate(docs, 1):
            path = PDF_DIR / f"{doc}.pdf"
            if path.exists() and path.stat().st_size > 1000:
                stats["cached"] += 1
                continue
            year = years.get(doc)
            if not year:
                stats["no filing year"] += 1
                continue
            try:
                r = client.get(PTR_URL.format(year=year, doc_id=doc))
            except httpx.HTTPError:
                stats["network error"] += 1
                continue
            if r.status_code == 200 and r.content[:4] == b"%PDF":
                tmp = path.with_suffix(".tmp")
                tmp.write_bytes(r.content)
                tmp.replace(path)
                stats["downloaded"] += 1
            else:
                stats[f"http {r.status_code}"] += 1
            if i % 100 == 0:
                print(f"  {i}/{len(docs)} {dict(stats)}", flush=True)
            time.sleep(delay)
    return stats


def build_plan(session, docs: List[str], matcher) -> Dict[str, object]:
    from domains.congressional.ptr_pdf import parse_ptr_pdf

    stats: Counter = Counter()
    updates: List[Dict[str, object]] = []
    for i, doc in enumerate(docs, 1):
        if i % 200 == 0:
            print(f"  ... {i}/{len(docs)} filings parsed {dict(stats)}", flush=True)
        path = PDF_DIR / f"{doc}.pdf"
        if not path.exists():
            stats["pdf missing"] += 1
            continue
        try:
            rows = parse_ptr_pdf(str(path))
        except Exception:
            stats["pdf unreadable"] += 1
            continue
        if not rows:
            stats["no text rows (scanned paper filing?)"] += 1
            continue
        trades = session.execute(text("""
            SELECT id::text, transaction_date, transaction_type, amount_min, raw_asset_description,
                   ticker, security_id::text
            FROM congressional_trades WHERE doc_id = :doc
        """), {"doc": doc}).all()
        by_key = defaultdict(list)
        for r in rows:
            by_key[(r.transaction_date, r.transaction_type, r.amount_min_cents)].append(r)
        for tid, tdate, ttype, amin, raw, ticker, sid in trades:
            cands = [r for r in by_key.get((tdate, ttype, amin), []) if norm(r.asset).startswith(norm(raw))]
            if len(cands) != 1:
                stats["no unique pdf row" if not cands else "several pdf rows"] += 1
                continue
            row = cands[0]
            symbol, method = (None, "fixed_income")
            if row.type_code in (None, "ST", "EF", "OP", "MF", "OL", "OT", "PS", "RS"):
                symbol, method = matcher.resolve(row.ticker, row.asset)
            upd = {"trade_id": tid, "full_asset": row.asset[:1000], "old_asset": raw, "type_code": row.type_code,
                   "category": TYPE_CODE_CATEGORY.get(row.type_code or "")}
            company = (matcher.universe_meta.get(symbol) or {}).get("name") or "" if symbol else ""
            if symbol and not names_consistent(row.asset, company):
                stats["ticker name mismatch (not linked)"] += 1
                symbol = None
            if symbol:
                text_l = row.asset.lower()
                meta_type = str((matcher.universe_meta.get(symbol) or {}).get("asset_type") or "").upper()
                # A mutual fund must not link to the same manager's ETF (Angel Oak fund -> CARY).
                if "fund" in text_l and "etf" not in text_l and meta_type in ("ETF", "EF") and row.type_code != "EF":
                    stats["fund vs ETF mismatch (not linked)"] += 1
                    symbol = None
            if symbol and not sid:
                upd["symbol"] = symbol
                upd["method"] = method
                stats["security recovered"] += 1
            elif not sid:
                stats[f"still unmatched ({row.type_code or 'no code'})"] += 1
            if row.asset != raw or "symbol" in upd or upd["category"]:
                updates.append(upd)
                stats["text restored"] += int(row.asset != raw)
    return {"docs": len(docs), "stats": dict(stats), "updates": updates}


def _load_all_models() -> None:
    """Import every domain model so SQLAlchemy can configure relationships
    (Security -> MemberPortfolio etc.) outside the app process."""
    import domains.congressional.models  # noqa: F401
    import domains.notifications.models  # noqa: F401
    import domains.portfolio.models  # noqa: F401
    import domains.securities.models  # noqa: F401
    import domains.users.models  # noqa: F401


def apply(session, matcher, updates: List[Dict[str, object]], commit: bool = True) -> Dict[str, int]:
    _load_all_models()
    from domains.securities.models import Security

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bak = BACKUP_DIR / f"ptr_reparse_{stamp}.json"
    ids = [u["trade_id"] for u in updates]
    prior = session.execute(text(
        "SELECT id::text, raw_asset_description, ticker, security_id::text, asset_type FROM congressional_trades WHERE id = ANY(CAST(:ids AS uuid[]))"
    ), {"ids": ids}).all()
    bak.write_text(json.dumps([list(r) for r in prior]), encoding="utf-8")
    print(f"backup: {bak}")

    sec_map = {t.strip().upper(): str(i) for i, t in session.execute(text("SELECT id, ticker FROM securities WHERE ticker IS NOT NULL"))}
    created = linked = 0
    for u in updates:
        params = {"tid": u["trade_id"], "asset": u["full_asset"]}
        sql = "UPDATE congressional_trades SET raw_asset_description = :asset, updated_at = now()"
        if u.get("category"):
            sql += ", asset_type = :category"
            params["category"] = u["category"]
        sym = u.get("symbol")
        if sym:
            if sym not in sec_map:
                sec = Security(currency="USD", **matcher.security_seed(sym, u.get("method") or "ticker", None))
                session.add(sec)
                session.flush()
                sec_map[sym] = str(sec.id)
                created += 1
            sql += ", security_id = :sid, ticker = :sym"
            params.update({"sid": sec_map[sym], "sym": sym})
            linked += 1
        session.execute(text(sql + " WHERE id = :tid"), params)
    if commit:
        session.commit()
    else:
        session.rollback()
    return {"updated": len(updates), "linked": linked, "securities_created": created, "committed": commit}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--download-only", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--all-filings", action="store_true", help="every House filing, not only ones with unmatched trades")
    ap.add_argument("--test-apply", action="store_true", help="run the writes, then roll back")
    ap.add_argument("--max-docs", type=int, default=0, help="limit filings (quick tests)")
    ap.add_argument("--from-plan", action="store_true", help="apply the saved plan instead of re-parsing")
    args = ap.parse_args()

    import asyncio
    import random

    from core.database import db_manager, get_sync_db_session

    asyncio.run(db_manager.initialize())
    with get_sync_db_session() as session:
        if not (args.apply or args.test_apply):
            session.execute(text("SET TRANSACTION READ ONLY"))
        docs = target_docs(session, args.all_filings)
        if args.max_docs:
            docs = docs[: args.max_docs]
        print(f"target filings: {len(docs)}")
        if args.download_only:
            print("download:", dict(download(docs, filing_years())))
            return 0
        from domains.securities.matching import SecurityMatcher

        matcher = SecurityMatcher()
        plan_path = DATA_DIR / "state" / "ptr_reparse_plan.json"
        if args.from_plan:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            print(f"loaded saved plan: {len(plan['updates'])} updates")
        else:
            plan = build_plan(session, docs, matcher)
            if not args.max_docs:
                plan_path.write_text(json.dumps(plan), encoding="utf-8")
        for k, v in sorted(plan["stats"].items(), key=lambda kv: -kv[1]):
            print(f"  {k}: {v}")
        sample = [u for u in plan["updates"] if u.get("symbol")]
        print("\nsample recovered securities:")
        for u in random.sample(sample, min(20, len(sample))):
            print(f"  {u['old_asset'][:34]!r:38} -> {u['symbol']:6} {u['full_asset'][:50]}")
        if args.apply:
            print("\napplied:", apply(session, matcher, plan["updates"]))
        elif args.test_apply:
            print("\ntest apply (rolled back):", apply(session, matcher, plan["updates"], commit=False))
        else:
            print("\nDRY RUN: nothing written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
