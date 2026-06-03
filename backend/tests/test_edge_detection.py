"""Tests for the edge detection and Kelly sizing module."""

from collections.abc import Callable

import pytest

from app.analytics.edge_detection import (
    CONSENSUS_AVERAGE_ANCHOR,
    OddsLineData,
    calculate_kelly,
    find_edges,
    select_sharp_anchor,
)

LineFactory = Callable[..., OddsLineData]


# --- select_sharp_anchor -------------------------------------------------------------


def test_pinnacle_is_preferred_anchor() -> None:
    """Pinnacle wins the hierarchy when present."""
    assert select_sharp_anchor(["draftkings", "pinnacle", "fanduel"]) == "pinnacle"


def test_betfair_used_when_pinnacle_absent() -> None:
    """Betfair is the anchor when Pinnacle is absent."""
    assert select_sharp_anchor(["draftkings", "betfair", "fanduel"]) == "betfair"


def test_circa_used_when_pinnacle_and_betfair_absent() -> None:
    """Hierarchy falls through to circa."""
    assert select_sharp_anchor(["caesars", "circa", "fanduel"]) == "circa"


def test_no_sharp_book_returns_none() -> None:
    """No hierarchy book present → None (caller falls back to consensus average)."""
    assert select_sharp_anchor(["superbook", "betrivers"]) is None


# --- calculate_kelly -----------------------------------------------------------------


def test_quarter_kelly_5pct_edge_at_even() -> None:
    """A 5% edge at +100 (p=0.55, decimal 2.0) → full Kelly 0.10, quarter Kelly 0.025."""
    # full_kelly = (b*p - q)/b = (1*0.55 - 0.45)/1 = 0.10
    assert calculate_kelly(0.55, 2.0, 0.25) == pytest.approx(0.025, abs=1e-9)


def test_kelly_negative_edge_returns_zero() -> None:
    """A negative edge must never produce a positive stake."""
    # p=0.45 at +100 → full kelly = (0.45 - 0.55)/1 = -0.10 → clamp to 0
    assert calculate_kelly(0.45, 2.0, 0.25) == 0.0


def test_kelly_zero_edge_returns_zero() -> None:
    """A break-even edge produces no stake."""
    # p=0.5 at +100 → full kelly = (0.5 - 0.5)/1 = 0.0
    assert calculate_kelly(0.5, 2.0, 0.25) == 0.0


# --- find_edges ----------------------------------------------------------------------


def test_pinnacle_anchor_positive_edge(make_line: LineFactory) -> None:
    """Pinnacle anchor + a generous DraftKings price → flagged opportunity."""
    lines = [
        make_line("pinnacle", "h2h", "Team A", american=-110),
        make_line("pinnacle", "h2h", "Team B", american=-110),
        # DraftKings offers Team A at +120 (implied ~0.4545) vs sharp 0.50 → ~4.5% edge.
        make_line("draftkings", "h2h", "Team A", american=120),
        make_line("draftkings", "h2h", "Team B", american=-140),
    ]
    opps = find_edges("evt1", lines, edge_threshold=0.02, kelly_fraction=0.25)
    assert len(opps) >= 1
    team_a = next(o for o in opps if o.outcome_name == "Team A")
    assert team_a.sharp_anchor_book == "pinnacle"
    assert team_a.best_book == "draftkings"
    assert team_a.our_prob == pytest.approx(0.5, abs=1e-9)
    assert team_a.edge_pct == pytest.approx(0.5 - (1 / 2.2), abs=1e-4)
    assert team_a.recommended_stake_units > 0


def test_betfair_anchor_when_pinnacle_absent(make_line: LineFactory) -> None:
    """With Pinnacle absent, Betfair becomes the sharp anchor in find_edges."""
    lines = [
        make_line("betfair", "h2h", "Team A", american=-110),
        make_line("betfair", "h2h", "Team B", american=-110),
        make_line("draftkings", "h2h", "Team A", american=120),
        make_line("draftkings", "h2h", "Team B", american=-140),
    ]
    opps = find_edges("evt2", lines, edge_threshold=0.02)
    assert opps, "expected at least one opportunity"
    assert all(o.sharp_anchor_book == "betfair" for o in opps)


def test_consensus_average_when_all_sharp_absent(make_line: LineFactory) -> None:
    """No sharp book present → consensus-average anchor still finds edges."""
    lines = [
        make_line("lowvig", "h2h", "Team A", american=-110),
        make_line("lowvig", "h2h", "Team B", american=-110),
        # betrivers offers a very generous Team A price, dragging best price up.
        make_line("betrivers", "h2h", "Team A", american=130),
        make_line("betrivers", "h2h", "Team B", american=-110),
    ]
    opps = find_edges("evt3", lines, edge_threshold=0.02)
    assert opps, "expected a flagged opportunity from the consensus average"
    assert all(o.sharp_anchor_book == CONSENSUS_AVERAGE_ANCHOR for o in opps)


def test_edge_below_threshold_returns_nothing(make_line: LineFactory) -> None:
    """A tiny positive edge below the threshold is not flagged."""
    lines = [
        make_line("pinnacle", "h2h", "Team A", american=-110),
        make_line("pinnacle", "h2h", "Team B", american=-110),
        # DraftKings at +104 (decimal 2.04, implied ~0.490) → edge ~1% < 2% threshold.
        make_line("draftkings", "h2h", "Team A", american=104),
        make_line("draftkings", "h2h", "Team B", american=-120),
    ]
    opps = find_edges("evt4", lines, edge_threshold=0.02)
    assert all(o.outcome_name != "Team A" for o in opps)


def test_no_edge_when_book_matches_fair(make_line: LineFactory) -> None:
    """When the only other book prices at fair, nothing clears the threshold."""
    lines = [
        make_line("pinnacle", "h2h", "Team A", american=-110),
        make_line("pinnacle", "h2h", "Team B", american=-110),
        make_line("draftkings", "h2h", "Team A", american=100),  # implied 0.5 == fair
        make_line("draftkings", "h2h", "Team B", american=100),
    ]
    opps = find_edges("evt5", lines, edge_threshold=0.02)
    assert opps == []
