"""
Public member pages: auth surface + disclosure stats.

Member pages (/members, /members/:id) are public, so the read endpoints they
use must accept anonymous requests. User-specific endpoints (mirror
portfolios, member comparison, legislation) must stay authenticated and
tier-gated. These tests inspect the FastAPI dependency tree of each route, so
they need no DB and no running app.

The second half pins compute_disclosure_stats: averages/medians, the 45-day
late rule (amendments excluded), future-dated trades dropped, and the
reported volume range in cents.
"""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

import schemas  # noqa: F401  (resolve circular-import ordering)
from core.auth import get_current_user, get_current_active_user
from api import members as members_api
from api import portfolios as portfolios_api
from api.members import compute_disclosure_stats, normalize_member_filters

pytestmark = pytest.mark.unit

AUTH_DEPS = {get_current_user, get_current_active_user}


def _dep_calls(dependant):
    """Every dependency callable reachable from a route's dependant tree."""
    out = set()
    for sub in dependant.dependencies:
        if sub.call is not None:
            out.add(sub.call)
        out |= _dep_calls(sub)
    return out


def _route(router, path, method="GET"):
    for r in router.routes:
        if getattr(r, "path", None) == path and method in getattr(r, "methods", set()):
            return r
    raise AssertionError(f"route {method} {path} not found")


def _requires_auth(router, path, method="GET"):
    return bool(_dep_calls(_route(router, path, method).dependant) & AUTH_DEPS)


class TestMemberEndpointsArePublic:
    @pytest.mark.parametrize("path", ["/", "/{member_id}", "/{member_id}/stats", "/{member_id}/trades"])
    def test_member_reads_accept_anonymous(self, path):
        assert not _requires_auth(members_api.router, path)

    @pytest.mark.parametrize("path", ["/member/{member_id}/holdings", "/member/{member_id}/performance"])
    def test_member_portfolio_reads_accept_anonymous(self, path):
        assert not _requires_auth(portfolios_api.router, path)


class TestUserSpecificEndpointsStayGated:
    @pytest.mark.parametrize(
        "path,method",
        [
            ("/mirror", "GET"),
            ("/mirror", "POST"),
            ("/mirror/{mirror_id}", "GET"),
            ("/mirror/{mirror_id}", "DELETE"),
            ("/mirror/{mirror_id}/members", "PUT"),
            ("/mirror/{mirror_id}/holdings", "GET"),
            ("/mirror/{mirror_id}/performance", "GET"),
            ("/members/compare", "GET"),
            ("/", "GET"),
            ("/{portfolio_id}/performance", "GET"),
        ],
    )
    def test_portfolio_user_endpoints_require_auth(self, path, method):
        assert _requires_auth(portfolios_api.router, path, method)

    def test_mirror_endpoints_keep_tier_gate(self):
        # require_subscription() builds a closure named "decorator"; its presence
        # (on top of the auth dependency) means the Pro+ gate is still wired.
        for path, method in [("/mirror", "GET"), ("/mirror/{mirror_id}/holdings", "GET")]:
            names = {getattr(c, "__name__", "") for c in _dep_calls(_route(portfolios_api.router, path, method).dependant)}
            assert "decorator" in names

    @pytest.mark.parametrize("path", ["/{member_id}/legislation", "/search", "/state/{state_code}"])
    def test_member_user_endpoints_require_auth(self, path):
        assert _requires_auth(members_api.router, path)

    def test_member_admin_endpoints_require_auth(self):
        assert _requires_auth(members_api.router, "/sync", "POST")


# ---------------------------------------------------------------------------
# compute_disclosure_stats
# ---------------------------------------------------------------------------

TODAY = date(2026, 10, 23)


def _t(trade_days_ago, lag_days, lo=100_100, hi=1_500_000, exact=None, status="N", ttype="P"):
    td = TODAY - timedelta(days=trade_days_ago)
    return SimpleNamespace(
        transaction_date=td,
        notification_date=td + timedelta(days=lag_days),
        amount_min=lo,
        amount_max=hi,
        amount_exact=exact,
        filing_status=status,
        transaction_type=ttype,
    )


class TestComputeDisclosureStats:
    def test_empty(self):
        s = compute_disclosure_stats([], TODAY)
        assert s["total_trades"] == 0
        assert s["avg_days_to_disclose"] is None
        assert s["median_days_to_disclose"] is None
        assert s["late_count"] == 0
        assert s["late_pct"] is None
        assert s["first_trade_date"] is None

    def test_average_median_and_late(self):
        rows = [_t(100, 10), _t(90, 20), _t(80, 30), _t(70, 46), _t(60, 100)]
        s = compute_disclosure_stats(rows, TODAY)
        assert s["total_trades"] == 5
        assert s["avg_days_to_disclose"] == 41.2
        assert s["median_days_to_disclose"] == 30.0
        assert s["max_days_to_disclose"] == 100
        assert s["late_count"] == 2  # 46 and 100; 45 exactly is on time
        assert s["late_pct"] == 40.0

    def test_exactly_45_days_is_not_late(self):
        assert compute_disclosure_stats([_t(100, 45)], TODAY)["late_count"] == 0

    def test_even_median(self):
        s = compute_disclosure_stats([_t(10, 4), _t(10, 10)], TODAY)
        assert s["median_days_to_disclose"] == 7.0

    def test_amendments_excluded_from_timing_but_counted(self):
        rows = [_t(400, 10), _t(400, 300, status="A")]
        s = compute_disclosure_stats(rows, TODAY)
        assert s["total_trades"] == 2
        assert s["amended_count"] == 1
        assert s["late_count"] == 0
        assert s["avg_days_to_disclose"] == 10.0
        assert s["timed_trades"] == 1

    def test_future_dated_trades_dropped(self):
        future = _t(-30, 0)
        s = compute_disclosure_stats([_t(5, 3), future], TODAY)
        assert s["total_trades"] == 1
        assert s["last_trade_date"] == (TODAY - timedelta(days=5)).isoformat()

    def test_volume_range_in_cents(self):
        rows = [
            _t(10, 5, lo=100_100, hi=1_500_000),
            _t(10, 5, lo=None, hi=None, exact=250_000),
            _t(10, 5, lo=5_000_000_100, hi=None),  # open-ended top band
        ]
        s = compute_disclosure_stats(rows, TODAY)
        assert s["volume_min"] == 100_100 + 250_000 + 5_000_000_100
        assert s["volume_max"] == 1_500_000 + 250_000 + 5_000_000_100
        assert s["volume_open_ended"] is True

    def test_last_12_months_window_and_type_counts(self):
        rows = [_t(30, 10, ttype="P"), _t(200, 60, ttype="S"), _t(500, 50, ttype="S")]
        s = compute_disclosure_stats(rows, TODAY)
        assert s["trades_last_12_months"] == 2
        assert s["median_days_last_12_months"] == 35.0
        assert s["late_count_last_12_months"] == 1
        assert s["purchase_count"] == 1
        assert s["sale_count"] == 2
        assert s["first_trade_date"] == (TODAY - timedelta(days=500)).isoformat()


class TestNormalizeMemberFilters:
    def test_names_codes_and_commas(self):
        parties, chambers, states = normalize_member_filters(
            ["Democratic", "R,i", "x"], ["house", "SENATE", "joint"], ["nj,ca", "XYZ"]
        )
        assert parties == ["D", "I", "R"]
        assert chambers == ["House", "Senate"]
        assert states == ["CA", "NJ"]

    def test_none(self):
        assert normalize_member_filters(None, None, None) == ([], [], [])
