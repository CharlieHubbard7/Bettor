"""Shared pytest fixtures for the analytics test suite."""

from collections.abc import Callable

import pytest

from app.analytics.edge_detection import OddsLineData
from app.analytics.no_vig import american_to_decimal


@pytest.fixture
def make_line() -> Callable[..., OddsLineData]:
    """Return a factory for :class:`OddsLineData`, deriving decimal odds from American.

    Usage::

        line = make_line("pinnacle", "h2h", "Team A", american=-110)
    """

    def _factory(
        bookmaker_key: str,
        market_key: str,
        outcome_name: str,
        american: int,
        point: float | None = None,
        player_name: str | None = None,
    ) -> OddsLineData:
        return OddsLineData(
            bookmaker_key=bookmaker_key,
            market_key=market_key,
            outcome_name=outcome_name,
            price_decimal=american_to_decimal(american),
            price_american=american,
            point=point,
            player_name=player_name,
        )

    return _factory


@pytest.fixture
def even_h2h_market() -> dict[str, float]:
    """A balanced -110/-110 two-way market keyed by outcome name (decimal odds)."""
    return {
        "Team A": american_to_decimal(-110),
        "Team B": american_to_decimal(-110),
    }


@pytest.fixture
def sample_clv_values() -> list[float]:
    """A small, hand-checkable list of CLV percentages (mean +1.0, 3 of 5 positive)."""
    return [2.0, -1.0, 4.0, -3.0, 3.0]
