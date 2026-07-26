"""
Composite Scrutiny Score.

Blends the four signal engines into a single, ranked, *explainable* per-member
score. It is a prioritisation aid for journalists, oversight, and research, not
an accusation: a high score means "worth a closer look", and every point traces
back to a named factor with its underlying value.

Factors (each percentile-ranked across the eligible member cohort, higher =
more scrutiny-worthy), and their weights:

  edge      0.31  benchmark-adjusted alpha, damped by statistical significance
                  (a big edge that is not significant counts for less)
  conflict  0.22  share of trades that are committee x sector conflicts
  cluster   0.19  involvement in notable herding events (sum of cluster
                  notability, which is already base-popularity weighted)
  lag       0.15  share of filings past the 45-day STOCK Act clock
  size      0.13  trade-size anomaly vs the member's own book (90th-pctile
                  z-score of log notionals)

Weights are the roadmap rubric renormalised to the signals we currently have
(event/earnings proximity is a later phase). Score is 0-100.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from domains.analytics.clustering import detect_cluster_events
from domains.analytics.conflicts import detect_committee_conflicts
from domains.analytics.returns_analytics import (
    compute_member_performance,
    compute_member_size_anomaly,
)

logger = logging.getLogger(__name__)

WEIGHTS = {"edge": 0.31, "conflict": 0.22, "cluster": 0.19, "lag": 0.15, "size": 0.13}


def _percentiles(values: List[float]) -> Dict[int, float]:
    """Map each index to its fractional rank in [0, 1] (ties share the average
    rank). Constant input maps everything to 0.5."""
    n = len(values)
    if n <= 1:
        return {0: 0.5} if n == 1 else {}
    order = sorted(range(n), key=lambda i: values[i])
    pct: Dict[int, float] = {}
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg_rank = (i + j) / 2.0
        for k in range(i, j + 1):
            pct[order[k]] = avg_rank / (n - 1)
        i = j + 1
    return pct


def _significance_factor(t_stat: float) -> float:
    """0..1 damping: full weight at |t| >= 2, half at |t| = 1."""
    return min(abs(t_stat) / 2.0, 1.0)


def compute_scrutiny_scores(session: Session, min_trades: int = 10) -> List[Dict[str, Any]]:
    perf = compute_member_performance(session, min_trades=min_trades)
    conflicts = {c["member"]: c for c in detect_committee_conflicts(session, min_conflicts=1)["leaderboard"]}
    clusters = detect_cluster_events(session)
    sizes = compute_member_size_anomaly(session)

    cluster_involvement: Dict[str, float] = defaultdict(float)
    for cl in clusters:
        for name in cl["members"]:
            cluster_involvement[name] += cl["notability_score"]

    # Assemble raw factors per member (perf is the eligibility gate).
    raw: List[Dict[str, Any]] = []
    for p in perf:
        name, trades = p["member"], p["trades"]
        conf = conflicts.get(name)
        size = sizes.get(name)
        raw.append({
            "member": name, "party": p["party"], "chamber": p["chamber"], "trades": trades,
            "edge_raw": p["avg_alpha_30d"], "t_stat": p["t_stat"],
            "edge_signal": p["avg_alpha_30d"] * _significance_factor(p["t_stat"]),
            "conflict_rate": (conf["conflict_trades"] / trades) if (conf and trades) else 0.0,
            "conflict_trades": conf["conflict_trades"] if conf else 0,
            "cluster_raw": cluster_involvement.get(name, 0.0),
            "lag_raw": p["late_pct"] or 0.0,
            "size_raw": size["size_z"] if size else 0.0,
            "size_biggest": size["biggest"] if size else None,
            "size_median": size["median_notional"] if size else None,
            "avg_alpha_30d": p["avg_alpha_30d"], "hit_rate": p["hit_rate"],
            "avg_lag_days": p["avg_lag_days"], "late_pct": p["late_pct"],
        })

    if not raw:
        return []

    # Percentile-normalise each factor across the cohort.
    pct = {
        "edge": _percentiles([r["edge_signal"] for r in raw]),
        "conflict": _percentiles([r["conflict_rate"] for r in raw]),
        "cluster": _percentiles([r["cluster_raw"] for r in raw]),
        "lag": _percentiles([r["lag_raw"] for r in raw]),
        "size": _percentiles([r["size_raw"] for r in raw]),
    }

    out: List[Dict[str, Any]] = []
    for i, r in enumerate(raw):
        contributions = {f: round(WEIGHTS[f] * pct[f][i], 4) for f in WEIGHTS}
        score = round(100 * sum(contributions.values()), 1)
        out.append({
            "member": r["member"], "party": r["party"], "chamber": r["chamber"],
            "scrutiny_score": score,
            "trades": r["trades"],
            "factors": {
                "edge": {"weight": WEIGHTS["edge"], "percentile": round(pct["edge"][i], 3),
                         "contribution": round(100 * contributions["edge"], 1),
                         "avg_alpha_30d": r["avg_alpha_30d"], "t_stat": r["t_stat"]},
                "conflict": {"weight": WEIGHTS["conflict"], "percentile": round(pct["conflict"][i], 3),
                             "contribution": round(100 * contributions["conflict"], 1),
                             "conflict_rate": round(r["conflict_rate"], 3),
                             "conflict_trades": r["conflict_trades"]},
                "cluster": {"weight": WEIGHTS["cluster"], "percentile": round(pct["cluster"][i], 3),
                            "contribution": round(100 * contributions["cluster"], 1),
                            "cluster_involvement": round(r["cluster_raw"], 2)},
                "lag": {"weight": WEIGHTS["lag"], "percentile": round(pct["lag"][i], 3),
                        "contribution": round(100 * contributions["lag"], 1),
                        "late_pct": r["late_pct"], "avg_lag_days": r["avg_lag_days"]},
                "size": {"weight": WEIGHTS["size"], "percentile": round(pct["size"][i], 3),
                         "contribution": round(100 * contributions["size"], 1),
                         "size_z": r["size_raw"], "biggest": r["size_biggest"],
                         "median_notional": r["size_median"]},
            },
        })

    out.sort(key=lambda r: r["scrutiny_score"], reverse=True)
    return out
