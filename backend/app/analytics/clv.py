"""Closing Line Value (CLV) computation.

CLV measures whether we secured a better price than the market's closing line. Positive
CLV over a large sample is the primary signal that our edge detection is genuinely sharp.
"""

import statistics


def calculate_clv(
    entry_price_decimal: float,
    closing_price_decimal: float,
) -> float:
    """Return CLV as a percentage.

    A positive value means our entry odds were better (higher decimal) than the closing
    odds — i.e. the line moved in our favor after we bet.

    Args:
        entry_price_decimal: Decimal odds at which the bet was placed (> 0).
        closing_price_decimal: Decimal odds at game commence (the closing line).

    Returns:
        ``(closing - entry) / entry * 100`` as a percentage.

    Raises:
        ValueError: If ``entry_price_decimal`` is not positive.
    """
    if entry_price_decimal <= 0:
        raise ValueError("Entry price (decimal) must be positive.")
    return (closing_price_decimal - entry_price_decimal) / entry_price_decimal * 100.0


def aggregate_clv_stats(clv_values: list[float]) -> dict:
    """Summarize a set of CLV values.

    Args:
        clv_values: CLV percentages from settled/closed trades.

    Returns:
        A dict with ``mean``, ``median``, ``std_dev``, ``pct_positive``, and
        ``sample_size``. All numeric fields are ``0.0`` for an empty input.
    """
    sample_size = len(clv_values)
    if sample_size == 0:
        return {
            "mean": 0.0,
            "median": 0.0,
            "std_dev": 0.0,
            "pct_positive": 0.0,
            "sample_size": 0,
        }

    positive = sum(1 for value in clv_values if value > 0)
    return {
        "mean": statistics.fmean(clv_values),
        "median": statistics.median(clv_values),
        "std_dev": statistics.pstdev(clv_values) if sample_size > 1 else 0.0,
        "pct_positive": positive / sample_size * 100.0,
        "sample_size": sample_size,
    }
