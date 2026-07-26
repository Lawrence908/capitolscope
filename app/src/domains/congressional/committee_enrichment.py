"""
Committee enrichment for congress members.

Congress.gov does not expose clean, current committee-membership rosters, so we
use the community-maintained ``unitedstates/congress-legislators`` dataset,
which publishes:

  - committees-current.json         (committee code -> canonical name)
  - committee-membership-current.json (committee code -> [{bioguide, ...}])

both keyed by the same ``bioguide`` id we already store on ``CongressMember``.

This module fetches those files, builds a ``bioguide_id -> [committee names]``
map (parent committees only, deduped), and writes it to
``CongressMember.committees``. It is the prerequisite for every
conflict-of-interest signal (committee x sector overlap, legislation
proximity), which currently cannot run because ``committees`` is empty.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from domains.congressional.models import CongressMember

logger = logging.getLogger(__name__)

COMMITTEES_URL = "https://unitedstates.github.io/congress-legislators/committees-current.json"
MEMBERSHIP_URL = "https://unitedstates.github.io/congress-legislators/committee-membership-current.json"

_HEADERS = {"User-Agent": "capitolscope-committee-enrichment/1.0"}


def _fetch_json(url: str, timeout: int = 45) -> Any:
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def build_bioguide_committee_map() -> Dict[str, List[str]]:
    """Return {bioguide_id: [committee_name, ...]} for parent committees.

    Subcommittee codes (whose thomas_id is not a top-level committee) are
    skipped so the stored list stays at the jurisdiction level that matters for
    conflict mapping. Names are deduped and order-stable.
    """
    committees = _fetch_json(COMMITTEES_URL)
    membership = _fetch_json(MEMBERSHIP_URL)

    # code -> canonical name, parent committees only (they carry thomas_id).
    code_to_name: Dict[str, str] = {
        c["thomas_id"]: c["name"] for c in committees if c.get("thomas_id") and c.get("name")
    }

    bioguide_to_committees: Dict[str, List[str]] = {}
    for code, members in membership.items():
        name = code_to_name.get(code)
        if not name:
            continue  # subcommittee or unknown code; skip
        for m in members:
            bioguide = m.get("bioguide")
            if not bioguide:
                continue
            lst = bioguide_to_committees.setdefault(bioguide, [])
            if name not in lst:
                lst.append(name)

    logger.info(
        "Built committee map: %d committees, %d members with assignments",
        len(code_to_name),
        len(bioguide_to_committees),
    )
    return bioguide_to_committees


def enrich_committees_sync(session: Session) -> Dict[str, Any]:
    """Backfill ``CongressMember.committees`` from the congress-legislators data.

    Only members with a ``bioguide_id`` present in the dataset are updated.
    Returns a summary dict.
    """
    bio_map = build_bioguide_committee_map()

    members = session.execute(select(CongressMember)).scalars().all()
    updated = 0
    matched = 0
    total_assignments = 0
    unmatched: List[str] = []

    for member in members:
        if not member.bioguide_id:
            continue
        committees = bio_map.get(member.bioguide_id)
        if not committees:
            unmatched.append(member.bioguide_id)
            continue
        matched += 1
        if member.committees != committees:
            member.committees = committees
            updated += 1
            total_assignments += len(committees)

    session.commit()

    summary = {
        "members_total": len(members),
        "members_matched": matched,
        "members_updated": updated,
        "members_unmatched": len(unmatched),
        "avg_committees_per_matched": round(total_assignments / matched, 2) if matched else 0,
        "source_members_in_dataset": len(bio_map),
    }
    logger.info("Committee enrichment complete: %s", summary)
    return summary
