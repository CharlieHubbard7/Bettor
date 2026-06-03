import type { EdgeOpportunity } from "@/types";

/** Build the /trades/new query string that pre-fills the logger from an opportunity. */
export function tradeLoggerLink(opp: EdgeOpportunity): string {
  const params = new URLSearchParams({
    event_id: opp.event_id,
    market_key: opp.market_key,
    outcome_name: opp.outcome_name,
    entry_price_american: String(opp.best_price_american),
    our_prob: String(opp.our_prob),
    sharp_consensus_prob: String(opp.our_prob),
    bookmaker: opp.best_book,
  });
  if (opp.player_name) params.set("player_name", opp.player_name);
  return `/trades/new?${params.toString()}`;
}
