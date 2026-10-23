#!/usr/bin/env python3
"""
Fill party / chamber / state / district / bioguide_id (and term dates) for
congress members that are missing them, using the unitedstates
congress-legislators dataset. See ``domains.congressional.member_enrichment``
for the matching rules.

Dry-run is the default: it opens a READ ONLY transaction, prints the proposed
updates and the ambiguous / review / duplicate / unmatched lists, and writes
nothing. Pass --apply to write matched rows (NULL columns only).

Usage (from app/src, or inside the capitolscope-worker container):
    python scripts/enrich_congress_members.py                     # dry run, fetch dataset
    python scripts/enrich_congress_members.py --data-dir /tmp/legislators-data
    python scripts/enrich_congress_members.py --json out.json     # machine-readable report
    python scripts/enrich_congress_members.py --apply             # write matches
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from domains.congressional.member_enrichment import (  # noqa: E402
    STATUS_AMBIGUOUS,
    STATUS_DUPLICATE,
    STATUS_MATCHED,
    STATUS_REVIEW,
    STATUS_UNMATCHED,
    load_legislator_records,
    run_enrichment,
)

_ORDER = (STATUS_MATCHED, STATUS_REVIEW, STATUS_DUPLICATE, STATUS_AMBIGUOUS, STATUS_UNMATCHED)


def _db_url(cli_url: str | None) -> str:
    if cli_url:
        return cli_url
    if os.environ.get("ENRICH_DATABASE_URL"):
        return os.environ["ENRICH_DATABASE_URL"]
    from core.config import settings
    return settings.database_url_sync


def _fmt_term(r) -> str:
    t = r.term
    if not t:
        return "-"
    loc = t.state + (f"-{t.district}" if t.district else "")
    return f"{t.chamber} {loc} {t.party or '?'}({t.raw_party}) {t.start}..{t.end}"


def _print_report(results, apply: bool, updated: int) -> None:
    by_status = {s: [r for r in results if r.status == s] for s in _ORDER}
    trades = Counter()
    for r in results:
        trades[r.status] += r.member.trade_count

    print(f"\n=== Member identity enrichment ({'APPLY' if apply else 'DRY RUN'}) ===")
    print(f"members needing enrichment: {len(results)} "
          f"covering {sum(r.member.trade_count for r in results)} trades")
    for s in _ORDER:
        print(f"  {s:<10} {len(by_status[s]):>4} members  {trades[s]:>6} trades")

    print("\n--- Proposed updates (matched) ---")
    for r in by_status[STATUS_MATCHED]:
        m, leg = r.member, r.legislator
        print(f"  {m.full_name!r:<28} [{m.trade_count:>5} trades {m.first_trade}..{m.last_trade}] -> "
              f"{leg.bioguide} {leg.display_name!r} | {_fmt_term(r)} | {r.reason}")

    print("\n--- Needs review (not applied; suggested legislator) ---")
    for r in by_status[STATUS_REVIEW]:
        m, leg = r.member, r.legislator
        print(f"  {m.full_name!r:<28} [{m.trade_count:>5} trades {m.first_trade}..{m.last_trade}] ~> "
              f"{leg.bioguide} {leg.display_name!r} | {_fmt_term(r)} | {r.reason}")

    print("\n--- Duplicates of an existing member row (merge needed, not applied) ---")
    for r in by_status[STATUS_DUPLICATE]:
        m, leg = r.member, r.legislator
        print(f"  {m.full_name!r:<28} [{m.trade_count:>5} trades] = {leg.bioguide} "
              f"{leg.display_name!r} | {r.reason}")

    print("\n--- Ambiguous (skipped) ---")
    for r in by_status[STATUS_AMBIGUOUS]:
        cands = "; ".join(f"{c.bioguide} {c.display_name}" for c in r.candidates)
        print(f"  {r.member.full_name!r:<28} [{r.member.trade_count:>5} trades] {r.reason} :: {cands}")

    print("\n--- Unmatched (skipped) ---")
    for r in by_status[STATUS_UNMATCHED]:
        print(f"  {r.member.full_name!r:<28} [{r.member.trade_count:>5} trades "
              f"{r.member.first_trade}..{r.member.last_trade}] {r.reason}")

    if apply:
        print(f"\nRows updated: {updated}")
    else:
        print("\nDry run: nothing written. Re-run with --apply to write the matched rows.")


def _to_json(results):
    out = []
    for r in results:
        out.append({
            "member_id": r.member.id,
            "full_name": r.member.full_name,
            "trade_count": r.member.trade_count,
            "first_trade": str(r.member.first_trade) if r.member.first_trade else None,
            "last_trade": str(r.member.last_trade) if r.member.last_trade else None,
            "status": r.status,
            "reason": r.reason,
            "bioguide": r.legislator.bioguide if r.legislator else None,
            "legislator": r.legislator.display_name if r.legislator else None,
            "proposed": {k: str(v) for k, v in r.proposed_fields().items()},
            "candidates": [c.bioguide for c in r.candidates],
        })
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=True, help="(default) print only, read-only transaction")
    mode.add_argument("--apply", action="store_true", help="write matched rows (NULL columns only)")
    ap.add_argument("--data-dir", help="directory with legislators-current.json and legislators-historical.json "
                                       "(default: download from unitedstates.github.io)")
    ap.add_argument("--database-url", help="sync SQLAlchemy URL (default: ENRICH_DATABASE_URL or settings)")
    ap.add_argument("--grace-days", type=int, default=90, help="slack around the trade window (default 90)")
    ap.add_argument("--json", dest="json_out", help="also write the full report as JSON to this path")
    args = ap.parse_args(argv)

    current, historical = load_legislator_records(args.data_dir)
    engine = create_engine(_db_url(args.database_url), pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        if not args.apply:
            session.execute(text("SET TRANSACTION READ ONLY"))
        summary = run_enrichment(session, current, historical, apply=args.apply, grace_days=args.grace_days)
        if not args.apply:
            session.rollback()

    results = summary["results"]
    _print_report(results, args.apply, summary["updated_rows"])
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(_to_json(results), fh, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
