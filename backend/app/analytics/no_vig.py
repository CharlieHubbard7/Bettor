"""No-vig probability calculation.

The bookmaker's quoted odds embed a margin (the "vig"). Converting odds to implied
probabilities and normalizing them to sum to 1.0 strips that margin, yielding the
market's fair estimate of each outcome's probability.

All internal math operates on decimal odds. American odds are converted at the boundary.
"""

from dataclasses import dataclass


def american_to_decimal(american: int) -> float:
    """Convert American odds to decimal odds.

    Args:
        american: American odds, e.g. ``-110`` or ``+150``. Must be non-zero.

    Returns:
        The equivalent decimal odds (total return per unit staked, stake included).

    Raises:
        ValueError: If ``american`` is zero (not a valid line).
    """
    if american == 0:
        raise ValueError("American odds cannot be zero.")
    if american > 0:
        return 1.0 + american / 100.0
    return 1.0 + 100.0 / abs(american)


def decimal_to_american(decimal: float) -> int:
    """Convert decimal odds to American odds.

    Args:
        decimal: Decimal odds, strictly greater than 1.0.

    Returns:
        The equivalent American odds, rounded to the nearest integer.

    Raises:
        ValueError: If ``decimal`` is not greater than 1.0.
    """
    if decimal <= 1.0:
        raise ValueError("Decimal odds must be greater than 1.0.")
    if decimal >= 2.0:
        return round((decimal - 1.0) * 100.0)
    return round(-100.0 / (decimal - 1.0))


def implied_probability(decimal_odds: float) -> float:
    """Return the raw implied probability of decimal odds (``1 / decimal_odds``).

    Args:
        decimal_odds: Decimal odds, strictly greater than 1.0.

    Returns:
        The implied probability, still inclusive of vig.

    Raises:
        ValueError: If ``decimal_odds`` is not greater than 1.0.
    """
    if decimal_odds <= 1.0:
        raise ValueError("Decimal odds must be greater than 1.0.")
    return 1.0 / decimal_odds


@dataclass
class NoVigResult:
    """Result of stripping vig from a market.

    Attributes:
        outcome_probs: Mapping of outcome name to its no-vig (fair) probability.
        vig_pct: The bookmaker margin, as a percentage (e.g. ``4.76`` for a -110/-110).
        fair_decimal_odds: Mapping of outcome name to fair decimal odds (``1 / prob``).
    """

    outcome_probs: dict[str, float]
    vig_pct: float
    fair_decimal_odds: dict[str, float]


def calculate_no_vig(outcomes: dict[str, float]) -> NoVigResult:
    """Strip the vig from a market and return fair probabilities and odds.

    Args:
        outcomes: Mapping of outcome name to its decimal odds. Must contain at least two
            outcomes — vig cannot be stripped from a single-outcome market.

    Returns:
        A :class:`NoVigResult` with no-vig probabilities, the vig percentage, and fair
        decimal odds for every outcome.

    Raises:
        ValueError: If fewer than two outcomes are provided, or any odds are invalid.
    """
    if len(outcomes) < 2:
        raise ValueError(
            "At least two outcomes are required to strip vig from a market."
        )

    implied = {name: implied_probability(odds) for name, odds in outcomes.items()}
    total_implied = sum(implied.values())

    no_vig_probs = {name: prob / total_implied for name, prob in implied.items()}
    vig_pct = (total_implied - 1.0) * 100.0
    fair_odds = {name: 1.0 / prob for name, prob in no_vig_probs.items()}

    return NoVigResult(
        outcome_probs=no_vig_probs,
        vig_pct=vig_pct,
        fair_decimal_odds=fair_odds,
    )
