"""Sharp-consensus edge detection and Kelly sizing.

The edge model anchors to the sharpest available bookmaker (Pinnacle first), strips its
vig to obtain a fair "true" probability, then flags any book offering a price whose raw
implied probability is enough below that fair probability to clear the edge threshold.
"""

from collections import defaultdict
from dataclasses import dataclass

from app.analytics.no_vig import calculate_no_vig, implied_probability

# Sharpest books first. Used to pick the consensus anchor for a market.
SHARP_HIERARCHY: list[str] = [
    "pinnacle",
    "betfair",
    "circa",
    "bookmaker",
    "draftkings",
    "fanduel",
    "betmgm",
    "caesars",
]

# Label used when no sharp-hierarchy book is present and we fall back to a consensus
# average across the remaining books.
CONSENSUS_AVERAGE_ANCHOR = "consensus_average"


@dataclass
class OddsLineData:
    """A single normalized odds line, the input unit for edge detection.

    Attributes:
        bookmaker_key: Bookmaker identifier, e.g. ``pinnacle``.
        market_key: Market identifier, e.g. ``h2h``, ``spreads``, ``player_points``.
        outcome_name: Outcome label (team name, or player + over/under).
        price_decimal: Decimal odds offered.
        price_american: American odds offered.
        point: Spread/total/prop line value, if applicable.
        player_name: Player name for prop markets, if applicable.
    """

    bookmaker_key: str
    market_key: str
    outcome_name: str
    price_decimal: float
    price_american: int
    point: float | None = None
    player_name: str | None = None


@dataclass
class EdgeOpportunity:
    """A flagged positive-expected-value play.

    Attributes:
        event_id: The event this opportunity belongs to.
        market_key: Market identifier.
        outcome_name: Outcome we'd bet on.
        player_name: Player name for prop markets, if applicable.
        our_prob: Our true probability (sharp no-vig consensus).
        book_implied_prob: Raw implied probability of the best available price.
        edge_pct: ``our_prob - book_implied_prob`` (as a fraction).
        best_book: Bookmaker offering the best price for this outcome.
        best_price_american: Best price in American odds.
        best_price_decimal: Best price in decimal odds.
        sharp_anchor_book: Book used as the sharp anchor (or consensus-average label).
        kelly_fraction: Full Kelly fraction (clamped at 0).
        recommended_stake_units: Fractional-Kelly stake in units.
    """

    event_id: str
    market_key: str
    outcome_name: str
    player_name: str | None
    our_prob: float
    book_implied_prob: float
    edge_pct: float
    best_book: str
    best_price_american: int
    best_price_decimal: float
    sharp_anchor_book: str
    kelly_fraction: float
    recommended_stake_units: float


def select_sharp_anchor(available_books: list[str]) -> str | None:
    """Return the sharpest book from :data:`SHARP_HIERARCHY` present in the input.

    Args:
        available_books: Bookmaker keys available for a market.

    Returns:
        The highest-priority sharp book present, or ``None`` if none of the
        hierarchy books are available.
    """
    available = {book.lower() for book in available_books}
    for book in SHARP_HIERARCHY:
        if book in available:
            return book
    return None


def calculate_kelly(
    our_prob: float,
    decimal_odds: float,
    kelly_fraction: float = 0.25,
) -> float:
    """Return the fractional-Kelly stake for a bet.

    Uses the standard Kelly criterion ``f* = (b*p - q) / b`` where ``b = decimal - 1``,
    scaled by ``kelly_fraction``. A non-positive edge yields a stake of ``0.0`` —
    we never stake into a negative edge.

    Args:
        our_prob: Our true win probability ``p`` (0 < p < 1).
        decimal_odds: Decimal odds offered (> 1.0).
        kelly_fraction: Fraction of full Kelly to stake (default quarter Kelly).

    Returns:
        The recommended stake as a fraction of bankroll, never negative.
    """
    b = decimal_odds - 1.0
    if b <= 0:
        return 0.0
    p = our_prob
    q = 1.0 - p
    full_kelly = (b * p - q) / b
    if full_kelly <= 0:
        return 0.0
    return full_kelly * kelly_fraction


def _full_kelly(our_prob: float, decimal_odds: float) -> float:
    """Return the full (unscaled) Kelly fraction, clamped at 0."""
    b = decimal_odds - 1.0
    if b <= 0:
        return 0.0
    return max(0.0, (b * our_prob - (1.0 - our_prob)) / b)


def _group_key(line: OddsLineData) -> tuple[str, str | None, float | None]:
    """Group lines that share a no-vig market: (market, player, point)."""
    return (line.market_key, line.player_name, line.point)


def _sharp_probs_for_group(
    lines_by_book: dict[str, dict[str, OddsLineData]],
) -> tuple[dict[str, float], str] | None:
    """Compute sharp no-vig probabilities for one market group.

    Picks the sharp anchor from the books present. If none of the sharp-hierarchy books
    are present, falls back to averaging each book's no-vig probabilities per outcome.

    Args:
        lines_by_book: Mapping of bookmaker -> {outcome_name: line} for one group.

    Returns:
        A tuple of (outcome -> sharp probability, anchor label), or ``None`` if no book
        in the group has the two+ outcomes required to strip vig.
    """
    anchor = select_sharp_anchor(list(lines_by_book.keys()))

    if anchor is not None:
        anchor_outcomes = {
            name: line.price_decimal
            for name, line in lines_by_book[anchor].items()
        }
        if len(anchor_outcomes) < 2:
            return None
        result = calculate_no_vig(anchor_outcomes)
        return result.outcome_probs, anchor

    # Fallback: average no-vig probabilities across every book with a full market.
    accumulated: dict[str, list[float]] = defaultdict(list)
    for outcomes in lines_by_book.values():
        odds = {name: line.price_decimal for name, line in outcomes.items()}
        if len(odds) < 2:
            continue
        novig = calculate_no_vig(odds)
        for name, prob in novig.outcome_probs.items():
            accumulated[name].append(prob)

    if not accumulated:
        return None

    averaged = {name: sum(probs) / len(probs) for name, probs in accumulated.items()}
    return averaged, CONSENSUS_AVERAGE_ANCHOR


def find_edges(
    event_id: str,
    lines: list[OddsLineData],
    edge_threshold: float = 0.02,
    kelly_fraction: float = 0.25,
) -> list[EdgeOpportunity]:
    """Find positive-EV opportunities across all books for one event.

    Algorithm:
        1. Group lines by market (market_key, player_name, point).
        2. For each group, pick the sharp anchor and compute its no-vig probabilities.
        3. For each outcome, find the best available price across all books.
        4. Compare that price's raw implied probability against the sharp probability.
        5. Flag outcomes whose edge exceeds ``edge_threshold``.

    Args:
        event_id: The event identifier.
        lines: All normalized odds lines for the event.
        edge_threshold: Minimum edge (fraction) required to flag (default 2%).
        kelly_fraction: Fraction of full Kelly used to size the stake.

    Returns:
        Flagged opportunities sorted by descending edge.
    """
    # Group lines: market group -> bookmaker -> outcome -> line.
    groups: dict[
        tuple[str, str | None, float | None], dict[str, dict[str, OddsLineData]]
    ] = defaultdict(lambda: defaultdict(dict))
    for line in lines:
        groups[_group_key(line)][line.bookmaker_key.lower()][line.outcome_name] = line

    opportunities: list[EdgeOpportunity] = []

    for (market_key, player_name, _point), lines_by_book in groups.items():
        sharp = _sharp_probs_for_group(lines_by_book)
        if sharp is None:
            continue
        sharp_probs, anchor_label = sharp

        # Collect every (book, outcome) candidate price for this group.
        outcome_candidates: dict[str, list[OddsLineData]] = defaultdict(list)
        for outcomes in lines_by_book.values():
            for outcome_name, line in outcomes.items():
                outcome_candidates[outcome_name].append(line)

        for outcome_name, sharp_prob in sharp_probs.items():
            candidates = outcome_candidates.get(outcome_name, [])
            if not candidates:
                continue
            # Best price = highest decimal odds (best payout for us).
            best = max(candidates, key=lambda ln: ln.price_decimal)
            book_implied = implied_probability(best.price_decimal)
            edge = sharp_prob - book_implied
            if edge <= edge_threshold:
                continue
            opportunities.append(
                EdgeOpportunity(
                    event_id=event_id,
                    market_key=market_key,
                    outcome_name=outcome_name,
                    player_name=player_name,
                    our_prob=sharp_prob,
                    book_implied_prob=book_implied,
                    edge_pct=edge,
                    best_book=best.bookmaker_key,
                    best_price_american=best.price_american,
                    best_price_decimal=best.price_decimal,
                    sharp_anchor_book=anchor_label,
                    kelly_fraction=_full_kelly(sharp_prob, best.price_decimal),
                    recommended_stake_units=calculate_kelly(
                        sharp_prob, best.price_decimal, kelly_fraction
                    ),
                )
            )

    opportunities.sort(key=lambda opp: opp.edge_pct, reverse=True)
    return opportunities
