"""
Identity enrichment for congress members (party, chamber, state, bioguide).

Members created by the disclosure ingestion pipeline only carry a parsed name,
so former members (who are not in the Congress.gov "current members" sync) end
up with NULL party/chamber/state/bioguide_id. This module fills them from the
community-maintained ``unitedstates/congress-legislators`` dataset (the same
source ``committee_enrichment`` uses), which covers every member of Congress,
current and historical, with dated terms.

Matching is precision-first:

  1. Surname must match (normalized: accents, punctuation, case and
     generational suffixes removed; compound surnames such as
     "McMorris Rodgers" also match on their final word).
  2. The legislator must have served during the member's trade window
     (first..last transaction date, with a small grace period).
  3. The first name must be compatible. "Strong" compatibility is an exact or
     nickname-equivalent match against the legislator's first, middle,
     nickname or official-name tokens ("Tom" = "Thomas", "Mick" = Michael).
     "Weak" compatibility is an initial ("K." = K. Michael Conaway) or a
     shared prefix of at least three letters ("Matthew" = "Matt").
  4. Exactly one candidate must survive. Any tie, or a strong match that is
     shadowed by another weak one, is reported as ambiguous and skipped.

A unique surname-only hit (first name lost by the parser, e.g.
"Armstrong Armstrong") is surfaced as ``review`` with the suggested
legislator, never applied automatically. A match whose bioguide already
belongs to another row is reported as ``duplicate`` (those rows need a
merge, not an update, and ``bioguide_id`` is unique).

The matching functions are pure; the DB helpers at the bottom are thin.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
import urllib.request
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

LEGISLATORS_CURRENT_URL = "https://unitedstates.github.io/congress-legislators/legislators-current.json"
LEGISLATORS_HISTORICAL_URL = "https://unitedstates.github.io/congress-legislators/legislators-historical.json"
_HEADERS = {"User-Agent": "capitolscope-member-enrichment/1.0"}

# Trades are only reported while in office, but transaction dates are
# occasionally mis-parsed and terms start/end mid-week, so allow some slack.
DEFAULT_GRACE_DAYS = 90
# Members with no trades: only consider people who served in the STOCK Act era.
NO_TRADES_WINDOW = (date(2012, 1, 1), None)

STATUS_MATCHED = "matched"
STATUS_AMBIGUOUS = "ambiguous"
STATUS_REVIEW = "review"
STATUS_DUPLICATE = "duplicate"
STATUS_UNMATCHED = "unmatched"

_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}
_HONORIFICS = {
    "hon", "honorable", "rep", "representative", "sen", "senator", "mr", "mrs",
    "ms", "miss", "dr", "the", "del", "delegate", "commissioner",
}

# Nickname groups. Two given names are "strongly" compatible when they are
# equal or appear together in at least one group. Names in several groups
# ("ted", "pat") do not make the groups' other members equivalent.
_NICKNAME_GROUPS: Tuple[Tuple[str, ...], ...] = (
    ("thomas", "tom", "tommy"),
    ("james", "jim", "jimmy", "jamie"),
    ("robert", "bob", "bobby", "rob", "robbie", "bert", "beto"),
    ("william", "bill", "billy", "will", "willie", "liam"),
    ("edward", "ed", "eddie", "ted", "ned"),
    ("theodore", "ted", "teddy"),
    ("edwin", "ed"),
    ("kenneth", "ken", "kenny"),
    ("charles", "charlie", "chuck", "chas"),
    ("david", "dave", "davey"),
    ("michael", "mike", "mick", "mickey"),
    ("richard", "rick", "ricky", "dick", "rich"),
    ("john", "jack", "johnny", "jon"),
    ("jonathan", "jon"),
    ("gregory", "greg"),
    ("rodney", "rod"),
    ("nicholas", "nick", "nicky"),
    ("bradley", "brad"),
    ("bradford", "brad"),
    ("catherine", "cathy", "kathy", "kate", "katie", "cat"),
    ("katherine", "kathy", "kate", "katie", "kathryn"),
    ("kathleen", "kathy", "kate", "katie"),
    ("christopher", "chris"),
    ("christine", "chris", "christy"),
    ("daniel", "dan", "danny"),
    ("donald", "don", "donnie"),
    ("joseph", "joe", "joey"),
    ("samuel", "sam", "sammy"),
    ("stephen", "steve", "steven"),
    ("steven", "steve", "stephen"),
    ("timothy", "tim", "timmy"),
    ("anthony", "tony"),
    ("patrick", "pat"),
    ("patricia", "pat", "patty", "trish"),
    ("peter", "pete"),
    ("matthew", "matt"),
    ("andrew", "andy", "drew"),
    ("benjamin", "ben", "benny"),
    ("frederick", "fred", "freddie"),
    ("gerald", "jerry"),
    ("jerome", "jerry"),
    ("harold", "hal"),
    ("henry", "hank", "harry"),
    ("lawrence", "larry"),
    ("leonard", "len", "lenny"),
    ("louis", "lou"),
    ("nathaniel", "nate", "nathan"),
    ("raymond", "ray"),
    ("ronald", "ron", "ronnie"),
    ("russell", "russ"),
    ("terrence", "terry"),
    ("walter", "walt"),
    ("zachary", "zach"),
    ("jeffrey", "jeff"),
    ("joshua", "josh"),
    ("douglas", "doug"),
    ("elizabeth", "liz", "beth", "betsy", "betty", "eliza"),
    ("margaret", "maggie", "peggy", "meg"),
    ("susan", "sue", "susie", "suzanne"),
    ("deborah", "debbie", "deb", "debra"),
    ("barbara", "barb"),
    ("cynthia", "cindy"),
    ("jacqueline", "jackie"),
    ("victoria", "vicky", "tori"),
    ("abigail", "abby"),
    ("virginia", "ginny"),
    ("francis", "frank"),
    ("franklin", "frank"),
    ("morris", "mo"),
    ("augustus", "gus"),
    ("alexander", "alex", "sandy"),
    ("alexandra", "alex", "sandy"),
    ("albert", "al", "bert"),
    ("alan", "al"),
    ("allen", "al"),
    ("vernon", "vern"),
    ("gilbert", "gil"),
    ("mitchell", "mitch"),
    ("randall", "randy"),
    ("randolph", "randy"),
    ("jeffery", "jeff"),
    ("thaddeus", "thad"),
    ("eleanor", "ellie"),
    ("dorothy", "dot"),
    ("jennifer", "jen", "jenny"),
    ("rebecca", "becca", "becky"),
    ("theresa", "terri", "tess"),
    ("valerie", "val"),
    ("frances", "fran"),
    ("carolyn", "carol"),
    ("judith", "judy"),
    ("kimberly", "kim"),
    ("pamela", "pam"),
    ("melvin", "mel"),
    ("bennie", "ben"),
)


def _build_nickname_index() -> Dict[str, frozenset]:
    idx: Dict[str, set] = {}
    for gid, group in enumerate(_NICKNAME_GROUPS):
        for name in group:
            idx.setdefault(name, set()).add(gid)
    return {k: frozenset(v) for k, v in idx.items()}


_NICK_IDX = _build_nickname_index()


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Term:
    chamber: str                 # 'House' or 'Senate'
    start: date
    end: date
    state: str
    district: Optional[str]      # None for senators and at-large seats
    party: Optional[str]         # 'D' / 'R' / 'I' or None if unmappable
    raw_party: Optional[str]


@dataclass(frozen=True)
class Legislator:
    bioguide: str
    first: str
    last: str
    middle: Optional[str]
    nickname: Optional[str]
    suffix: Optional[str]
    official_full: Optional[str]
    terms: Tuple[Term, ...]
    is_current: bool

    @property
    def display_name(self) -> str:
        if self.official_full:
            return self.official_full
        return " ".join(p for p in (self.first, self.middle, self.last, self.suffix) if p)


@dataclass(frozen=True)
class MemberRecord:
    """A ``congress_members`` row plus its trade window (no ORM dependency)."""

    id: str
    first_name: str
    last_name: str
    full_name: str
    prefix: Optional[str] = None
    first_trade: Optional[date] = None
    last_trade: Optional[date] = None
    trade_count: int = 0


@dataclass
class MatchResult:
    member: MemberRecord
    status: str
    legislator: Optional[Legislator] = None
    term: Optional[Term] = None
    candidates: List[Legislator] = field(default_factory=list)
    reason: str = ""

    def proposed_fields(self) -> Dict[str, Any]:
        """Column values this match would set (before NULL-only filtering)."""
        if not self.legislator or not self.term:
            return {}
        leg, term = self.legislator, self.term
        fields: Dict[str, Any] = {
            "bioguide_id": leg.bioguide,
            "party": term.party,
            "chamber": term.chamber,
            "state": term.state,
            "district": term.district,
            "term_start": min(t.start for t in leg.terms),
            # Current members keep term_end NULL, matching the Congress.gov sync.
            "term_end": None if leg.is_current else max(t.end for t in leg.terms),
        }
        return {k: v for k, v in fields.items() if v is not None}


# ---------------------------------------------------------------------------
# Parsing the congress-legislators JSON
# ---------------------------------------------------------------------------

def map_party(raw: Optional[str]) -> Optional[str]:
    """Map dataset party names to the DB's single-letter codes.

    Parties outside D/R/I (e.g. "Libertarian") return None so the column is
    left untouched rather than violating ``check_party``.
    """
    if not raw:
        return None
    r = raw.strip().lower()
    if r.startswith("democrat"):
        return "D"
    if r.startswith("republican"):
        return "R"
    if r.startswith("independent"):
        return "I"
    return None


def _parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _party_on(term_raw: Dict[str, Any], on: date) -> Optional[str]:
    """Party in effect on ``on``, honoring mid-term ``party_affiliations``."""
    affs = []
    for aff in term_raw.get("party_affiliations") or []:
        s, e = _parse_date(aff.get("start")), _parse_date(aff.get("end"))
        if s:
            affs.append((s, e, aff.get("party")))
    for s, e, party in affs:
        if s <= on and (e is None or on <= e):
            return party
    started = [a for a in affs if a[0] <= on]
    if started:
        return max(started, key=lambda a: a[0])[2]
    if affs:
        return min(affs, key=lambda a: a[0])[2]
    return term_raw.get("party")


def _parse_term(term_raw: Dict[str, Any], party_date: Optional[date] = None) -> Optional[Term]:
    kind = term_raw.get("type")
    chamber = {"rep": "House", "sen": "Senate"}.get(kind or "")
    start, end = _parse_date(term_raw.get("start")), _parse_date(term_raw.get("end"))
    state = term_raw.get("state")
    if not chamber or not start or not end or not state or len(state) != 2:
        return None
    district: Optional[str] = None
    if chamber == "House":
        d = term_raw.get("district")
        # 0 is at-large; existing rows store NULL there, so keep it NULL.
        if isinstance(d, int) and d > 0:
            district = str(d)
    raw_party = _party_on(term_raw, party_date) if party_date else term_raw.get("party")
    return Term(chamber, start, end, state.upper(), district, map_party(raw_party), raw_party)


def parse_legislators(records: Iterable[Dict[str, Any]], is_current: bool) -> List[Legislator]:
    out: List[Legislator] = []
    for rec in records:
        ids, name = rec.get("id") or {}, rec.get("name") or {}
        bioguide, first, last = ids.get("bioguide"), name.get("first"), name.get("last")
        if not bioguide or not first or not last:
            continue
        terms = tuple(t for t in (_parse_term(tr) for tr in rec.get("terms") or []) if t)
        if not terms:
            continue
        out.append(
            Legislator(
                bioguide=bioguide,
                first=first,
                last=last,
                middle=name.get("middle"),
                nickname=name.get("nickname"),
                suffix=name.get("suffix"),
                official_full=name.get("official_full"),
                terms=terms,
                is_current=is_current,
            )
        )
    return out


def _raw_terms_by_bioguide(records: Iterable[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    return {
        (r.get("id") or {}).get("bioguide"): list(r.get("terms") or [])
        for r in records
        if (r.get("id") or {}).get("bioguide")
    }


# ---------------------------------------------------------------------------
# Name normalization
# ---------------------------------------------------------------------------

def normalize_token(value: Optional[str]) -> str:
    """Lowercase, strip accents and punctuation; keep inner spaces."""
    if not value:
        return ""
    s = unicodedata.normalize("NFKD", value)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[’'`\.]", "", s)       # O'Rourke / O’Rourke -> orourke
    s = re.sub(r"[^a-z0-9 ]+", " ", s)        # hyphens, commas -> space
    return re.sub(r"\s+", " ", s).strip()


def surname_keys(last: Optional[str]) -> List[str]:
    """Lookup keys for a surname: full form, space-collapsed, final word.

    Generational suffixes are dropped, so "Pascrell, Jr." -> "pascrell".
    """
    words = [w for w in normalize_token(last).split() if w not in _SUFFIXES]
    if not words:
        return []
    keys = [" ".join(words)]
    if len(words) > 1:
        keys.append("".join(words))
        keys.append(words[-1])
    seen: List[str] = []
    for k in keys:
        if k not in seen:
            seen.append(k)
    return seen


def _given_tokens(*values: Optional[str]) -> List[str]:
    toks: List[str] = []
    for v in values:
        for t in normalize_token(v).split():
            if t in _SUFFIXES or t in _HONORIFICS:
                continue
            if t not in toks:
                toks.append(t)
    return toks


def legislator_given_names(leg: Legislator) -> List[str]:
    """First, middle, nickname and official-name given tokens (no surname)."""
    surname_words = set(normalize_token(leg.last).split())
    official = [
        t for t in _given_tokens(leg.official_full) if t not in surname_words
    ]
    return _given_tokens(leg.first, leg.middle, leg.nickname) + [
        t for t in official if t not in _given_tokens(leg.first, leg.middle, leg.nickname)
    ]


def member_given_names(member: MemberRecord) -> List[str]:
    """Given-name tokens for a DB row.

    Includes ``prefix`` when it is not an honorific: the parser sometimes puts
    the real first name there (prefix "David", first_name "A." for Dave Trott).
    """
    names = _given_tokens(member.first_name)
    surname_words = set(normalize_token(member.last_name).split())
    for t in _given_tokens(member.prefix):
        if t not in names and t not in surname_words:
            names.append(t)
    return names


def nickname_equivalent(a: str, b: str) -> bool:
    if a == b:
        return True
    ga, gb = _NICK_IDX.get(a), _NICK_IDX.get(b)
    return bool(ga and gb and ga & gb)


def first_name_strength(member_names: Sequence[str], leg_names: Sequence[str]) -> int:
    """2 = exact/nickname match, 1 = initial or 3+ letter prefix, 0 = none."""
    best = 0
    for m in member_names:
        for g in leg_names:
            if len(m) > 1 and len(g) > 1 and nickname_equivalent(m, g):
                return 2
            if len(m) == 1 or len(g) == 1:
                if m[0] == g[0]:
                    best = max(best, 1)
            elif len(m) >= 3 and len(g) >= 3 and (m.startswith(g) or g.startswith(m)):
                best = max(best, 1)
    return best


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

class LegislatorIndex:
    """Surname -> legislators lookup over current + historical records."""

    def __init__(self, legislators: Iterable[Legislator]):
        self.by_surname: Dict[str, List[Legislator]] = {}
        self.by_bioguide: Dict[str, Legislator] = {}
        for leg in legislators:
            # Current file wins if a bioguide appears in both.
            if leg.bioguide in self.by_bioguide and not leg.is_current:
                continue
            self.by_bioguide[leg.bioguide] = leg
        for leg in self.by_bioguide.values():
            for key in surname_keys(leg.last):
                bucket = self.by_surname.setdefault(key, [])
                if leg not in bucket:
                    bucket.append(leg)

    def surname_candidates(self, last_name: str) -> List[Legislator]:
        out: List[Legislator] = []
        for key in surname_keys(last_name):
            for leg in self.by_surname.get(key, []):
                if leg not in out:
                    out.append(leg)
        return out


def trade_window(member: MemberRecord, grace_days: int = DEFAULT_GRACE_DAYS) -> Tuple[date, Optional[date]]:
    if member.first_trade is None:
        return NO_TRADES_WINDOW
    lo = member.first_trade - timedelta(days=grace_days)
    hi = (member.last_trade or member.first_trade) + timedelta(days=grace_days)
    return lo, hi


def overlapping_terms(leg: Legislator, window: Tuple[date, Optional[date]]) -> List[Term]:
    lo, hi = window
    return [t for t in leg.terms if t.end >= lo and (hi is None or t.start <= hi)]


def _resolve_term(
    leg: Legislator,
    window: Tuple[date, Optional[date]],
    member: MemberRecord,
    raw_terms: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Optional[Term]:
    """Last term overlapping the window, with party as of the last trade."""
    terms = overlapping_terms(leg, window)
    if not terms:
        return None
    last = max(terms, key=lambda t: t.start)
    if raw_terms and leg.bioguide in raw_terms:
        # Party as of the last trade, clamped into the term.
        anchor = min(max(member.last_trade or last.end, last.start), last.end)
        for tr in raw_terms[leg.bioguide]:
            if _parse_date(tr.get("start")) == last.start and tr.get("party_affiliations"):
                reparsed = _parse_term(tr, party_date=anchor)
                if reparsed:
                    return reparsed
    return last


def match_member(
    member: MemberRecord,
    index: LegislatorIndex,
    grace_days: int = DEFAULT_GRACE_DAYS,
    raw_terms: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> MatchResult:
    """Resolve one DB member to at most one legislator. Pure function."""
    window = trade_window(member, grace_days)
    surname_hits = index.surname_candidates(member.last_name)
    if not surname_hits:
        return MatchResult(member, STATUS_UNMATCHED, reason="no legislator with this surname")

    in_window = [leg for leg in surname_hits if overlapping_terms(leg, window)]
    if not in_window:
        return MatchResult(
            member, STATUS_UNMATCHED, candidates=surname_hits[:5],
            reason="surname found but nobody with it served during the trade window",
        )

    given = member_given_names(member)
    strong, weak = [], []
    for leg in in_window:
        s = first_name_strength(given, legislator_given_names(leg))
        if s == 2:
            strong.append(leg)
        elif s == 1:
            weak.append(leg)

    # A unique strong match is only shadowed by weak candidates whose own
    # first name or nickname is compatible; a bare middle initial elsewhere
    # ("Sanford D. Bishop" vs "Dan Bishop") does not compete with it.
    if len(strong) == 1 and weak:
        weak = [
            leg for leg in weak
            if first_name_strength(given, _given_tokens(leg.first, leg.nickname)) > 0
        ]
    compatible = strong + weak
    if len(compatible) == 1:
        leg = compatible[0]
        term = _resolve_term(leg, window, member, raw_terms)
        tier = "strong" if strong else "weak"
        return MatchResult(member, STATUS_MATCHED, leg, term, [leg], reason=f"{tier} first-name match")
    if len(compatible) > 1:
        return MatchResult(
            member, STATUS_AMBIGUOUS, candidates=compatible,
            reason=f"{len(strong)} strong / {len(weak)} weak first-name candidates in window",
        )

    # No compatible first name. A unique surname in the window is a useful hint
    # (first names lost by the parser), but never safe to apply blindly.
    first_is_surname = normalize_token(member.first_name) == normalize_token(member.last_name)
    if len(in_window) == 1:
        leg = in_window[0]
        why = "first name equals surname (parser casualty)" if first_is_surname else "first name does not match"
        return MatchResult(
            member, STATUS_REVIEW, leg, _resolve_term(leg, window, member, raw_terms), [leg],
            reason=f"unique surname in window but {why}",
        )
    return MatchResult(
        member, STATUS_UNMATCHED, candidates=in_window,
        reason="surname served in window but no first-name match",
    )


def match_members(
    members: Sequence[MemberRecord],
    index: LegislatorIndex,
    existing_bioguides: Optional[Dict[str, str]] = None,
    grace_days: int = DEFAULT_GRACE_DAYS,
    raw_terms: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> List[MatchResult]:
    """Match a batch and enforce bioguide uniqueness.

    ``existing_bioguides`` maps bioguide -> full_name of rows that already
    hold it. A match onto one of those becomes ``duplicate``; two rows in the
    batch resolving to the same bioguide both become ``ambiguous``.
    """
    existing_bioguides = existing_bioguides or {}
    results = [match_member(m, index, grace_days, raw_terms) for m in members]

    claims: Dict[str, List[MatchResult]] = {}
    for r in results:
        if r.status == STATUS_MATCHED and r.legislator:
            claims.setdefault(r.legislator.bioguide, []).append(r)

    for bioguide, rs in claims.items():
        if bioguide in existing_bioguides:
            for r in rs:
                r.status = STATUS_DUPLICATE
                r.reason = f"bioguide already on row '{existing_bioguides[bioguide]}' (merge needed)"
        elif len(rs) > 1:
            names = ", ".join(r.member.full_name for r in rs)
            for r in rs:
                r.status = STATUS_AMBIGUOUS
                r.reason = f"several rows resolve to {bioguide}: {names}"
    return results


# ---------------------------------------------------------------------------
# Loading the dataset
# ---------------------------------------------------------------------------

def _fetch_json(url: str, timeout: int = 60) -> Any:
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def load_legislator_records(data_dir: Optional[str] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return (current, historical) raw records, from ``data_dir`` or the web."""
    if data_dir:
        base = Path(data_dir)
        with open(base / "legislators-current.json", encoding="utf-8") as fh:
            current = json.load(fh)
        with open(base / "legislators-historical.json", encoding="utf-8") as fh:
            historical = json.load(fh)
    else:
        current = _fetch_json(LEGISLATORS_CURRENT_URL)
        historical = _fetch_json(LEGISLATORS_HISTORICAL_URL)
    if not isinstance(current, list) or not isinstance(historical, list):
        raise ValueError("unexpected congress-legislators payload shape")
    return current, historical


def build_index(current: List[Dict[str, Any]], historical: List[Dict[str, Any]]):
    legislators = parse_legislators(current, True) + parse_legislators(historical, False)
    raw_terms = _raw_terms_by_bioguide(historical)
    raw_terms.update(_raw_terms_by_bioguide(current))
    return LegislatorIndex(legislators), raw_terms


# ---------------------------------------------------------------------------
# DB helpers (sync session; SELECT-only unless apply_matches is called)
# ---------------------------------------------------------------------------

_MEMBERS_SQL = """
SELECT m.id::text, m.first_name, m.last_name, m.full_name, m.prefix,
       m.bioguide_id, MIN(t.transaction_date), MAX(t.transaction_date), COUNT(t.id)
FROM congress_members m
LEFT JOIN congressional_trades t ON t.member_id = m.id
WHERE m.bioguide_id IS NULL OR m.party IS NULL OR m.chamber IS NULL OR m.state IS NULL
GROUP BY m.id
ORDER BY COUNT(t.id) DESC, m.full_name
"""

_EXISTING_SQL = "SELECT bioguide_id, full_name FROM congress_members WHERE bioguide_id IS NOT NULL"

_FILLABLE = ("bioguide_id", "party", "chamber", "state", "district", "term_start", "term_end")


def load_members(session) -> Tuple[List[MemberRecord], Dict[str, str], Dict[str, str]]:
    """Return (members needing enrichment, existing bioguide->name, member id->bioguide)."""
    from sqlalchemy import text

    rows = session.execute(text(_MEMBERS_SQL)).all()
    members, known_bioguide = [], {}
    for r in rows:
        members.append(MemberRecord(
            id=r[0], first_name=r[1] or "", last_name=r[2] or "", full_name=r[3] or "",
            prefix=r[4], first_trade=r[6], last_trade=r[7], trade_count=int(r[8] or 0),
        ))
        if r[5]:
            known_bioguide[r[0]] = r[5]
    existing = {b: n for b, n in session.execute(text(_EXISTING_SQL)).all()}
    return members, existing, known_bioguide


def run_enrichment(session, current, historical, apply: bool = False,
                   grace_days: int = DEFAULT_GRACE_DAYS) -> Dict[str, Any]:
    """Match all members missing identity fields; optionally write matches.

    Rows that already have a bioguide_id but miss party/chamber/state are
    resolved directly by bioguide. Only NULL columns are ever written.
    """
    index, raw_terms = build_index(current, historical)
    members, existing, known_bioguide = load_members(session)

    by_name = [m for m in members if m.id not in known_bioguide]
    results = match_members(by_name, index, existing, grace_days, raw_terms)
    for m in members:
        bg = known_bioguide.get(m.id)
        if not bg:
            continue
        leg = index.by_bioguide.get(bg)
        if leg is None:
            results.append(MatchResult(m, STATUS_UNMATCHED, reason=f"bioguide {bg} not in dataset"))
            continue
        window = trade_window(m, grace_days)
        term = _resolve_term(leg, window, m, raw_terms) or max(leg.terms, key=lambda t: t.start)
        results.append(MatchResult(m, STATUS_MATCHED, leg, term, [leg], reason="existing bioguide"))

    updates = 0
    if apply:
        updates = apply_matches(session, [r for r in results if r.status == STATUS_MATCHED])
    return {"results": results, "updated_rows": updates}


def apply_matches(session, matches: Sequence[MatchResult]) -> int:
    """Fill NULL columns from matched results. Commits once. Returns rows changed."""
    from sqlalchemy import text

    changed = 0
    for r in matches:
        proposed = r.proposed_fields()
        if not proposed:
            continue
        sets = ", ".join(f"{col} = COALESCE({col}, :{col})" for col in _FILLABLE if col in proposed)
        params = {col: proposed[col] for col in _FILLABLE if col in proposed}
        params["id"] = r.member.id
        res = session.execute(
            text(f"UPDATE congress_members SET {sets}, updated_at = now() WHERE id = CAST(:id AS uuid)"),
            params,
        )
        changed += res.rowcount or 0
    session.commit()
    return changed
