"""Tests for the Closing Line Value module."""

import pytest

from app.analytics.clv import aggregate_clv_stats, calculate_clv


def test_negative_clv_line_moved_against_us() -> None:
    """Entry 1.91, closing 1.83 → line moved against us → negative CLV."""
    clv = calculate_clv(1.91, 1.83)
    assert clv < 0
    assert clv == pytest.approx((1.83 - 1.91) / 1.91 * 100, abs=1e-9)


def test_positive_clv_got_better_than_closing() -> None:
    """Entry 1.91, closing 2.00 → we beat the close → positive CLV."""
    clv = calculate_clv(1.91, 2.00)
    assert clv > 0
    assert clv == pytest.approx((2.00 - 1.91) / 1.91 * 100, abs=1e-9)


def test_zero_clv_when_entry_equals_closing() -> None:
    """Entry == closing → exactly 0.0 CLV."""
    assert calculate_clv(1.91, 1.91) == 0.0


def test_invalid_entry_raises() -> None:
    """A non-positive entry price is invalid."""
    with pytest.raises(ValueError):
        calculate_clv(0.0, 1.91)


def test_aggregate_clv_stats_known_list(sample_clv_values: list[float]) -> None:
    """[2, -1, 4, -3, 3] → mean 1.0, 3/5 positive = 60%, sample size 5."""
    stats = aggregate_clv_stats(sample_clv_values)
    assert stats["mean"] == pytest.approx(1.0, abs=1e-9)
    assert stats["median"] == pytest.approx(2.0, abs=1e-9)
    assert stats["pct_positive"] == pytest.approx(60.0, abs=1e-9)
    assert stats["sample_size"] == 5
    assert stats["std_dev"] > 0


def test_aggregate_clv_stats_empty() -> None:
    """An empty input yields zeroed stats, not an error."""
    stats = aggregate_clv_stats([])
    assert stats == {
        "mean": 0.0,
        "median": 0.0,
        "std_dev": 0.0,
        "pct_positive": 0.0,
        "sample_size": 0,
    }
