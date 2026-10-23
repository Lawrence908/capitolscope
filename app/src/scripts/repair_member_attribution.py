#!/usr/bin/env python3
"""
Re-attribute every disclosure filing to the member who actually filed it.

Ground truth per filing:
  House  : the Clerk's filing index (data/congress/csv/*FD_docIDlist.csv):
           DocID -> Last, First, StateDst
  Senate : stored eFD search results (data/congress/raw/senate/search_*.json):
           doc_id -> first_name, last_name
Each filer is resolved to a legislator (bioguide) with
domains.congressional.member_resolution, then to a congress_members row:
  1. the row that already carries that bioguide, else
  2. "adopt" the row currently holding the filing when it has no bioguide and
     the same surname (keeps its UUID, so shared links and alert rules stay
     valid), else
  3. create a new member from the legislator record.
Then filings are moved, identity fields (party/chamber/state/district) are
set from the legislator's latest term, and member rows left with no trades
and no references are deleted.

Dry run by default: prints the plan and writes it to --plan-out. --apply
backs up congress_members and the trade->member map first, then applies the
whole plan in one transaction.

Usage (from app/src, inside the capitolscope or worker container):
  python scripts/repair_member_attribution.py [--apply] [--legislators-dir DIR]
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import sys
import uuid
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from domains.congressional.member_enrichment import (  # noqa: E402
    build_index,
    load_legislator_records,
    normalize_token,
    surname_keys,
)
from domains.congressional.member_resolution import (  # noqa: E402
    Filer,
    chamber_from_doc_id,
    parse_state_dst,
    identity_fields,
    resolve_filer,
)

DATA_DIR = Path(os.environ.get("CAPITOLSCOPE_DATA_DIR", "/app/data/congress"))
BACKUP_DIR = Path(os.environ.get("CAPITOLSCOPE_BACKUP_DIR", "/app/data/backups"))

# Tables that reference congress_members.id (a member row with any of these
# is never deleted, even if it ends up with no trades).
MEMBER_REFS = [
    ("trade_alert_rules", "target_member_id"),
    ("mirror_portfolio_members", "member_id"),
    ("social_posts", "member_id"),
]


def load_house_index() -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    for f in glob.glob(str(DATA_DIR / "csv" / "*FD_docIDlist.csv")):
        with open(f, newline="", encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh):
                out[(r.get("DocID") or "").strip()] = r
    return out


def load_senate_index() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for f in sorted(glob.glob(str(DATA_DIR / "raw" / "senate" / "search_*.json"))):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for r in d if isinstance(d, list) else d.get("reports", []):
            if isinstance(r, dict) and r.get("doc_id"):
                out[r["doc_id"]] = r
    return out


def filer_for(doc_id: str, on: date, house: dict, senate: dict) -> Optional[Filer]:
    chamber = chamber_from_doc_id(doc_id)
    if chamber == "House":
        r = house.get(doc_id)
        if not r:
            return None
        state, district = parse_state_dst(r.get("StateDst"))
        return Filer(first=r.get("First") or "", last=r.get("Last") or "", state=state,
                     district=district, chamber="House", on=on)
    if chamber == "Senate":
        r = senate.get(doc_id)
        if not r:
            return None
        return Filer(first=r.get("first_name") or "", last=r.get("last_name") or "", chamber="Senate", on=on)
    return None


def build_plan(session, index) -> Dict[str, Any]:
    house, senate = load_house_index(), load_senate_index()
    docs = session.execute(text("""
        SELECT t.doc_id, t.member_id::text, MIN(t.notification_date), COUNT(*)
        FROM congressional_trades t GROUP BY t.doc_id, t.member_id
    """)).all()
    members = {
        r[0]: {"id": r[0], "full_name": r[1], "last_name": r[2], "bioguide_id": r[3]}
        for r in session.execute(text(
            "SELECT id::text, full_name, last_name, bioguide_id FROM congress_members"
        )).all()
    }
    by_bioguide = {m["bioguide_id"]: mid for mid, m in members.items() if m["bioguide_id"]}

    resolved: List[Tuple[str, str, Any, date, int]] = []   # doc, current member, legislator, on, trades
    review: List[Dict[str, Any]] = []
    for doc_id, member_id, on, n in docs:
        filer = filer_for(doc_id, on, house, senate)
        if filer is None:
            review.append({"doc_id": doc_id, "member_id": member_id, "trades": n, "reason": "no source identity"})
            continue
        res = resolve_filer(filer, index)
        if res.status != "matched":
            review.append({"doc_id": doc_id, "member_id": member_id, "trades": n, "filer": f"{filer.first} {filer.last}",
                           "reason": f"{res.status}: {res.reason}", "candidates": list(res.candidates)})
            continue
        resolved.append((doc_id, member_id, res.legislator, on, n))

    # Choose a target row per legislator: existing bioguide row, else adopt the
    # surname-matching, bioguide-less row holding most of its trades, else new.
    holders: Dict[str, Counter] = defaultdict(Counter)
    legs: Dict[str, Any] = {}
    latest: Dict[str, date] = {}
    for doc_id, member_id, leg, on, n in resolved:
        holders[leg.bioguide][member_id] += n
        legs[leg.bioguide] = leg
        latest[leg.bioguide] = max(latest.get(leg.bioguide, on), on)

    target: Dict[str, str] = {}
    adopts: List[Dict[str, Any]] = []
    creates: List[Dict[str, Any]] = []
    adopted_rows: set = set()
    for bio, counter in holders.items():
        if bio in by_bioguide:
            target[bio] = by_bioguide[bio]
            continue
        leg = legs[bio]
        leg_keys = set(surname_keys(leg.last))
        pick = None
        for mid, _ in counter.most_common():
            m = members.get(mid)
            if not m or m["bioguide_id"] or mid in adopted_rows:
                continue
            full_last = (m["full_name"] or "").split()[-1] if m["full_name"] else ""
            row_keys = set(surname_keys(m["last_name"])) | set(surname_keys(full_last))
            if leg_keys & row_keys or normalize_token(leg.last) in normalize_token(m["full_name"]):
                pick = mid
                break
        if pick:
            adopted_rows.add(pick)
            target[bio] = pick
            adopts.append({"member_id": pick, "was": members[pick]["full_name"], **identity_fields(leg, latest[bio])})
        else:
            new_id = str(uuid.uuid4())
            target[bio] = new_id
            creates.append({"member_id": new_id, **identity_fields(leg, latest[bio])})

    moves = []
    for doc_id, member_id, leg, on, n in resolved:
        dest = target[leg.bioguide]
        if dest != member_id:
            moves.append({"doc_id": doc_id, "from": member_id, "from_name": members.get(member_id, {}).get("full_name"),
                          "to": dest, "to_name": legs[leg.bioguide].display_name, "trades": n})

    # Identity refresh for every targeted row that already had a bioguide.
    refresh = [
        {"member_id": target[bio], **identity_fields(legs[bio], latest[bio])}
        for bio in holders if bio in by_bioguide
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filings": len(docs),
        "resolved": len(resolved),
        "review": review,
        "adopts": adopts,
        "creates": creates,
        "moves": moves,
        "refresh": refresh,
    }


def summarize(plan: Dict[str, Any]) -> None:
    moved_trades = sum(m["trades"] for m in plan["moves"])
    print(f"filings: {plan['filings']}  resolved: {plan['resolved']}  review: {len(plan['review'])}")
    print(f"moves: {len(plan['moves'])} filings / {moved_trades} trades")
    print(f"adopt existing rows: {len(plan['adopts'])}  create members: {len(plan['creates'])}  refresh identities: {len(plan['refresh'])}")
    agg = Counter()
    for m in plan["moves"]:
        agg[(m["from_name"], m["to_name"])] += m["trades"]
    print("\nlargest moves (from -> to : trades)")
    for (a, b), n in agg.most_common(25):
        print(f"  {a!r:34} -> {b!r:34} {n}")
    if plan["creates"]:
        print("\nnew members:", ", ".join(c["full_name"] for c in plan["creates"][:30]))
    if plan["review"]:
        print("\nreview (not changed):")
        for r in plan["review"][:20]:
            print("  ", r)


_COLS = ("bioguide_id", "first_name", "last_name", "full_name", "party", "chamber", "state", "district", "term_start", "term_end")


def apply_plan(session, plan: Dict[str, Any]) -> Dict[str, int]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    members_bak = BACKUP_DIR / f"congress_members_{stamp}.json"
    trades_bak = BACKUP_DIR / f"trade_member_map_{stamp}.csv"
    rows = session.execute(text("SELECT row_to_json(m) FROM congress_members m")).scalars().all()
    members_bak.write_text(json.dumps(rows, default=str), encoding="utf-8")
    with open(trades_bak, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["trade_id", "member_id"])
        for tid, mid in session.execute(text("SELECT id::text, member_id::text FROM congressional_trades")):
            w.writerow([tid, mid])
    print(f"backups: {members_bak} {trades_bak}")

    set_sql = ", ".join(f"{c} = :{c}" for c in _COLS)
    for c in plan["creates"]:
        session.execute(text(
            "INSERT INTO congress_members (id, created_at, updated_at, " + ", ".join(_COLS) + ") "
            "VALUES (:member_id, now(), now(), " + ", ".join(f":{c}" for c in _COLS) + ")"
        ), c)
    for a in plan["adopts"]:
        session.execute(text(f"UPDATE congress_members SET {set_sql}, updated_at = now() WHERE id = :member_id"), a)
    # Rows that already had the right bioguide keep their names; only the
    # identity fields are corrected (e.g. at-large House members stored as Senate).
    ident = ("party", "chamber", "state", "district", "term_start", "term_end")
    ident_sql = ", ".join(f"{c} = :{c}" for c in ident)
    for r in plan["refresh"]:
        session.execute(text(f"UPDATE congress_members SET {ident_sql}, updated_at = now() WHERE id = :member_id"), r)
    for m in plan["moves"]:
        session.execute(text(
            "UPDATE congressional_trades SET member_id = :to, updated_at = now() "
            "WHERE doc_id = :doc_id AND member_id = :from"
        ), m)

    # Delete member rows left with no trades and no references.
    refs = " AND ".join(
        f"NOT EXISTS (SELECT 1 FROM {tbl} r WHERE r.{col} = m.id)"
        for tbl, col in MEMBER_REFS
        if session.execute(text("SELECT to_regclass(:t)"), {"t": tbl}).scalar()
    )
    deleted = session.execute(text(
        "DELETE FROM congress_members m WHERE NOT EXISTS (SELECT 1 FROM congressional_trades t WHERE t.member_id = m.id)"
        " AND m.bioguide_id IS NULL" + (f" AND {refs}" if refs else "")
    )).rowcount
    session.commit()
    return {"created": len(plan["creates"]), "adopted": len(plan["adopts"]), "refreshed": len(plan["refresh"]),
            "moved_filings": len(plan["moves"]), "deleted_empty_members": deleted}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    ap.add_argument("--legislators-dir", help="dir with legislators-current.json / -historical.json (default: download)")
    ap.add_argument("--plan-out", default=str(DATA_DIR / "state" / "member_repair_plan.json"))
    args = ap.parse_args()

    import asyncio

    from core.database import db_manager, get_sync_db_session

    asyncio.run(db_manager.initialize())
    current, historical = load_legislator_records(args.legislators_dir)
    index, _ = build_index(current, historical)

    with get_sync_db_session() as session:
        if not args.apply:
            session.execute(text("SET TRANSACTION READ ONLY"))
        plan = build_plan(session, index)
        Path(args.plan_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.plan_out).write_text(json.dumps(plan, indent=1, default=str), encoding="utf-8")
        summarize(plan)
        print(f"\nplan written to {args.plan_out}")
        if args.apply:
            print("\napplied:", apply_plan(session, plan))
        else:
            print("\nDRY RUN: nothing written. Re-run with --apply to apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
