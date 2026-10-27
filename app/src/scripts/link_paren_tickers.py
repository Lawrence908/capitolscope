#!/usr/bin/env python3
"""
Link unmatched trades whose filed text carries an explicit "(TICKER)".

Two gaps left by the shared SecurityMatcher on restored PTR text:
  * older PDFs garble ticker case ("Boeing Co (Ba)", "Goldman Sachs (Gs)");
    the matcher only trusts 1-2 letter tickers from an upper-case paren;
  * bond ETFs ("iShares iBoxx ... Corporate Bond ETF (HYG)") trip the
    fixed-income guard meant for individual bonds and notes.

A ticker is linked only when it is a listed symbol in the matcher universe,
the listed company name is consistent with the filed text (reused tickers
such as Monsanto's MON stay unlinked), and, for bond-like text, the symbol
is an ETF/fund rather than an equity.

Dry run by default; --apply backs up the affected ids, then links.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

BACKUP_DIR = Path(os.environ.get("CAPITOLSCOPE_BACKUP_DIR", "/app/data/backups"))
_PAREN = re.compile(r"\(([A-Za-z][A-Za-z.\-]{0,5})\)")
_FUND_TYPES = {"ETF", "EF", "ETN", "FUND", "MF", "ETV", "ETS"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    import asyncio
    import random

    from core.database import db_manager, get_sync_db_session
    from domains.securities.matching import SecurityMatcher
    from domains.securities.name_matching import looks_like_fixed_income
    from scripts.reparse_house_ptrs import _load_all_models, names_consistent

    asyncio.run(db_manager.initialize())
    matcher = SecurityMatcher()
    with get_sync_db_session() as session:
        if not args.apply:
            session.execute(text("SET TRANSACTION READ ONLY"))
        rows = session.execute(text(
            r"SELECT id::text, raw_asset_description FROM congressional_trades "
            r"WHERE security_id IS NULL AND raw_asset_description ~ '\([A-Za-z][A-Za-z.\-]{0,5}\)'"
        )).all()
        stats: Counter = Counter()
        links = []
        for tid, raw in rows:
            found = [t.upper() for t in _PAREN.findall(raw) if t.lower() not in ("partial", "full")]
            if not found:
                continue
            sym = found[-1]
            meta = matcher.universe_meta.get(sym)
            if not meta:
                stats["not a listed symbol (delisted/unknown)"] += 1
                continue
            name = meta.get("name") or ""
            if not names_consistent(raw, name):
                stats["name mismatch (reused ticker?)"] += 1
                continue
            if looks_like_fixed_income(raw) and str(meta.get("asset_type") or "").upper() not in _FUND_TYPES:
                stats["bond text but symbol is not a fund"] += 1
                continue
            links.append({"trade_id": tid, "symbol": sym, "raw": raw, "company": name})
            stats["linkable"] += 1

        print(f"unmatched trades with a (TICKER): {len(rows)}")
        for k, v in sorted(stats.items(), key=lambda kv: -kv[1]):
            print(f"  {k}: {v}")
        print("\nsample:")
        for l in random.sample(links, min(25, len(links))):
            print(f"  {l['raw'][:46]!r:50} -> {l['symbol']:6} {l['company'][:40]}")

        if not args.apply:
            print("\nDRY RUN: nothing written.")
            return 0

        _load_all_models()
        from domains.securities.models import Security

        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        bak = BACKUP_DIR / f"paren_ticker_links_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
        bak.write_text(json.dumps([l["trade_id"] for l in links]), encoding="utf-8")
        sec_map = {t.strip().upper(): str(i) for i, t in session.execute(text("SELECT id, ticker FROM securities WHERE ticker IS NOT NULL"))}
        created = 0
        for l in links:
            sym = l["symbol"]
            if sym not in sec_map:
                sec = Security(currency="USD", **matcher.security_seed(sym, "ticker", l["company"] or None))
                session.add(sec)
                session.flush()
                sec_map[sym] = str(sec.id)
                created += 1
            session.execute(text(
                "UPDATE congressional_trades SET security_id = :sid, ticker = :sym, updated_at = now() "
                "WHERE id = :tid AND security_id IS NULL"
            ), {"sid": sec_map[sym], "sym": sym, "tid": l["trade_id"]})
        session.commit()
        print(f"\napplied: linked {len(links)}, securities created {created}; backup {bak}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
