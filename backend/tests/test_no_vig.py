"""Tests for the no-vig probability module."""

import pytest

from app.analytics.no_vig import (
    american_to_decimal,
    calculate_no_vig,
    decimal_to_american,
    implied_probability,
)


def test_even_market_110_110(even_h2h_market: dict[str, float]) -> None:
    """-110/-110 → 52.38% implied each, 50% no-vig each, 4.76% vig."""
    # Raw implied probabilities embed the vig.
    decimal = american_to_decimal(-110)
    assert implied_probability(decimal) == pytest.approx(0.52381, abs=1e-5)

    result = calculate_no_vig(even_h2h_market)
    assert result.outcome_probs["Team A"] == pytest.approx(0.5, abs=1e-9)
    assert result.outcome_probs["Team B"] == pytest.approx(0.5, abs=1e-9)
    assert result.vig_pct == pytest.approx(4.7619, abs=1e-3)
    # Fair odds of a true coin flip are 2.0 decimal.
    assert result.fair_decimal_odds["Team A"] == pytest.approx(2.0, abs=1e-9)


def test_minus150_plus130_no_vig() -> None:
    """-150/+130 → no-vig probs ~0.5798 / ~0.4202, summing to 1.0 (verified by hand)."""
    outcomes = {
        "Favorite": american_to_decimal(-150),  # 1.6667 → implied 0.6000
        "Underdog": american_to_decimal(130),  # 2.3000 → implied 0.4348
    }
    result = calculate_no_vig(outcomes)
    assert result.outcome_probs["Favorite"] == pytest.approx(0.57983, abs=1e-4)
    assert result.outcome_probs["Underdog"] == pytest.approx(0.42017, abs=1e-4)
    assert sum(result.outcome_probs.values()) == pytest.approx(1.0, abs=1e-9)


def test_three_way_market_sums_to_one() -> None:
    """A soccer 1X2 three-way market's no-vig probabilities sum to 1.0."""
    outcomes = {
        "Home": american_to_decimal(150),
        "Draw": american_to_decimal(220),
        "Away": american_to_decimal(180),
    }
    result = calculate_no_vig(outcomes)
    assert len(result.outcome_probs) == 3
    assert sum(result.outcome_probs.values()) == pytest.approx(1.0, abs=1e-9)
    assert result.vig_pct > 0


def test_american_decimal_round_trip() -> None:
    """american_to_decimal / decimal_to_american round-trip for both signs."""
    for american in (-250, -150, -110, 100, 130, 250):
        decimal = american_to_decimal(american)
        assert decimal_to_american(decimal) == american


def test_decimal_conversions_known_values() -> None:
    """Spot-check a couple of well-known conversions."""
    assert american_to_decimal(100) == pytest.approx(2.0)
    assert american_to_decimal(-200) == pytest.approx(1.5)
    assert decimal_to_american(2.0) == 100


def test_single_outcome_raises() -> None:
    """A single-outcome market cannot have its vig stripped."""
    with pytest.raises(ValueError):
        calculate_no_vig({"Only Option": 1.91})


def test_zero_american_raises() -> None:
    """Zero is not a valid American line."""
    with pytest.raises(ValueError):
        american_to_decimal(0)


def test_invalid_decimal_raises() -> None:
    """Decimal odds at or below 1.0 are invalid."""
    with pytest.raises(ValueError):
        implied_probability(1.0)
    with pytest.raises(ValueError):
        decimal_to_american(0.5)
