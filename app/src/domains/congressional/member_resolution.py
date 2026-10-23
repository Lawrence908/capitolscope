"""
Resolve a disclosure filer to the right member of Congress.

The old importer split a single "Prefix First Last" string by position and
then fell back to substring and 70% fuzzy matching on the whole name, which
credited filings to whoever shared a first name (John Boehner's filings
landed on Sen. John Thune) and minted garbled members ("Armstrong
Armstrong" when a Senate row had no prefix).

This resolver works from the filer's separate first/last name plus whatever
the source knows (House filings carry the state and district; Senate
filings are always the Senate) and identifies the legislator against the
congress-legislators dataset by surname, service dates and given name.
Only an unambiguous answer is returned; anything else is reported for
review rather than guessed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .member_enrichment import (
    Legislator,
    LegislatorIndex,
    Term,
    first_name_strength,
    legislator_given_names,
    normalize_token,
)

# Tokens that appear in filer names but are not names.
_NOISE = {
    "hon", "honorable", "mr", "mrs", "ms", "miss", "dr", "rep", "sen", "senator",
    "representative", "md", "facs", "phd", "jd", "dds", "dmd", "cpa", "esq",
    "mba", "rn", "dvm", "od", "ret", "usn", "usa", "usmc", "usaf", "facc", "faap",
    "jr", "sr", "ii", "iii", "iv", "v",
}

# Filings can land after a member leaves office (final PTRs) or, for the
# first filing, shortly before the term formally starts.
DEFAULT_GRACE_DAYS = 200


@dataclass(frozen=True)
class Filer:
    first: str
    last: str
    state: Optional[str] = None      # 2-letter, when the source says
    district: Optional[str] = None
    chamber: Optional[str] = None    # 'House' | 'Senate', when the source says
    on: Optional[date] = None        # filing date (or a trade date)


@dataclass(frozen=True)
class Resolution:
    legislator: Optional[Legislator]
    status: str                      # matched | ambiguous | unmatched
    reason: str
    candidates: Tuple[str, ...] = ()


def name_tokens(value: Optional[str]) -> List[str]:
    return [t for t in normalize_token(value).split() if t not in _NOISE]


def parse_state_dst(value: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """House StateDst "LA05" -> ("LA", "5"); "AK00" / "VT" -> (state, None)."""
    m = re.match(r"^\s*([A-Za-z]{2})\s*(\d{1,2})?\s*$", value or "")
    if not m:
        return None, None
    district = m.group(2)
    if district is not None:
        district = str(int(district)) if int(district) > 0 else None
    return m.group(1).upper(), district


def chamber_from_doc_id(doc_id: Optional[str]) -> Optional[str]:
    """House Clerk ids are numeric; Senate eFD ids are UUIDs."""
    if not doc_id:
        return None
    if re.fullmatch(r"\d+", doc_id.strip()):
        return "House"
    if re.fullmatch(r"[0-9a-fA-F-]{32,36}", doc_id.strip()):
        return "Senate"
    return None


def _served(terms: Sequence[Term], on: Optional[date], grace: timedelta) -> List[Term]:
    if on is None:
        return list(terms)
    return [t for t in terms if t.start - grace <= on <= t.end + grace]


def _surname_candidates(index: LegislatorIndex, last: str) -> List[Legislator]:
    toks = name_tokens(last)
    if not toks:
        return []
    out: List[Legislator] = []
    # Full surname first ("Van Taylor", "Hinson Arenholz"), then each word:
    # compound and married surnames are often listed under one part.
    for key in [" ".join(toks)] + toks[::-1]:
        for leg in index.surname_candidates(key):
            if leg not in out:
                out.append(leg)
    return out


def resolve_filer(
    filer: Filer,
    index: LegislatorIndex,
    grace_days: int = DEFAULT_GRACE_DAYS,
) -> Resolution:
    grace = timedelta(days=grace_days)
    given = name_tokens(filer.first)
    pool = _surname_candidates(index, filer.last)
    if not pool:
        return Resolution(None, "unmatched", f"no legislator with surname {filer.last!r}")

    viable: List[Tuple[Legislator, int]] = []
    for leg in pool:
        terms = _served(leg.terms, filer.on, grace)
        if filer.chamber:
            terms = [t for t in terms if t.chamber == filer.chamber]
        if filer.state:
            terms = [t for t in terms if t.state == filer.state]
        if not terms:
            continue
        strength = first_name_strength(given, legislator_given_names(leg)) if given else 0
        viable.append((leg, strength))

    if not viable and filer.on is not None and filer.state and given:
        # Filing dated outside every term (paper-era dates, pre-swearing-in
        # filings): accept only a unique same-state, same-chamber legislator
        # whose given name matches exactly or by nickname.
        relaxed = resolve_filer(Filer(filer.first, filer.last, filer.state, filer.district, filer.chamber, None), index, grace_days)
        if relaxed.status == "matched" and relaxed.reason.endswith("(strength 2)"):
            return Resolution(relaxed.legislator, "matched", "outside term dates; " + relaxed.reason, relaxed.candidates)

    names = tuple(f"{leg.display_name} ({leg.bioguide})" for leg, _ in viable)
    if not viable:
        return Resolution(None, "unmatched", "surname found but nobody served then/there", tuple(
            f"{leg.display_name} ({leg.bioguide})" for leg in pool[:5]
        ))

    best = max(s for _, s in viable)
    top = [leg for leg, s in viable if s == best]
    if len(top) == 1:
        leg = top[0]
        # A lone candidate with no given-name support is only trusted when the
        # source pinned the state (House filings always do).
        if best == 0 and not filer.state:
            return Resolution(None, "ambiguous", "surname-only match without state", names)
        return Resolution(leg, "matched", f"surname+{'given name' if best else 'state'} (strength {best})", names)
    return Resolution(None, "ambiguous", f"{len(top)} legislators tie", names)


def term_on(leg: Legislator, on: Optional[date], chamber: Optional[str] = None) -> Optional[Term]:
    """The term in force on a date (latest overlapping), for chamber/state/party."""
    terms = [t for t in leg.terms if chamber is None or t.chamber == chamber]
    if on is not None:
        live = [t for t in terms if t.start <= on <= t.end]
        if live:
            return max(live, key=lambda t: t.start)
        earlier = [t for t in terms if t.start <= on]
        if earlier:
            return max(earlier, key=lambda t: t.start)
    return max(terms, key=lambda t: t.start) if terms else None


def identity_fields(leg: Legislator, on: Optional[date]) -> Dict[str, Any]:
    """congress_members column values for a legislator as of a date."""
    t = term_on(leg, on) or term_on(leg, None)
    starts = [x.start for x in leg.terms]
    ends = [x.end for x in leg.terms]
    first = leg.nickname or leg.first
    return {
        "bioguide_id": leg.bioguide,
        "first_name": first,
        "last_name": leg.last,
        "full_name": f"{first} {leg.last}".strip(),
        "party": t.party if t else None,
        "chamber": t.chamber if t else None,
        "state": t.state if t else None,
        "district": t.district if t else None,
        "term_start": min(starts) if starts else None,
        "term_end": None if leg.is_current else (max(ends) if ends else None),
    }
