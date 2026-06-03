// TypeScript interfaces mirroring the backend Pydantic response schemas exactly.
// (See backend/app/schemas/*.py — these are the source of truth.)

export type TradeType = "paper" | "real";
export type TradeStatus = "open" | "settled" | "void";
export type TradeResult = "win" | "loss" | "push";

export interface Sport {
  sport_key: string;
  title: string;
  active: boolean;
  last_updated: string;
}

export interface BettorEvent {
  id: string;
  sport_key: string;
  commence_time: string;
  home_team: string;
  away_team: string;
  completed: boolean;
  home_score: number | null;
  away_score: number | null;
}

export interface OddsLine {
  id: string;
  event_id: string;
  sport_key: string;
  bookmaker_key: string;
  market_key: string;
  outcome_name: string;
  price_american: number;
  price_decimal: number;
  point: number | null;
  player_name: string | null;
  snapshot_timestamp: string;
  is_closing_line: boolean;
}

export interface EdgeOpportunity {
  event_id: string;
  market_key: string;
  outcome_name: string;
  player_name: string | null;
  our_prob: number;
  book_implied_prob: number;
  edge_pct: number; // fraction, e.g. 0.034 = 3.4%
  best_book: string;
  best_price_american: number;
  best_price_decimal: number;
  sharp_anchor_book: string;
  kelly_fraction: number; // full Kelly fraction
  recommended_stake_units: number;
  home_team: string | null;
  away_team: string | null;
  commence_time: string | null;
}

export interface EventOdds {
  event: BettorEvent;
  lines: OddsLine[];
  opportunities: EdgeOpportunity[];
}

export interface TradeCreate {
  event_id: string;
  market_key: string;
  outcome_name: string;
  player_name?: string | null;
  entry_price_american: number;
  our_prob: number;
  sharp_consensus_prob: number;
  bookmaker: string;
  stake_dollars?: number | null;
  trade_type?: TradeType;
  notes?: string | null;
}

export interface Trade {
  id: string;
  event_id: string;
  market_key: string;
  outcome_name: string;
  player_name: string | null;
  entry_price_american: number;
  entry_price_decimal: number;
  our_prob: number;
  sharp_consensus_prob: number;
  edge_pct: number;
  kelly_fraction: number;
  stake_units: number;
  stake_dollars: number | null;
  bookmaker: string;
  trade_type: TradeType;
  status: TradeStatus;
  result: TradeResult | null;
  closing_price_american: number | null;
  clv: number | null;
  profit_loss_units: number | null;
  profit_loss_dollars: number | null;
  created_at: string;
  settled_at: string | null;
  notes: string | null;
}

export interface TradeUpdate {
  notes?: string | null;
  status?: TradeStatus | null;
}

export interface CLVStats {
  mean: number;
  median: number;
  std_dev: number;
  pct_positive: number;
  sample_size: number;
}

export interface EquityPoint {
  date: string;
  bankroll: number;
  cumulative_pnl_units: number;
}

export interface PnLSummary {
  total_trades: number;
  settled_trades: number;
  wins: number;
  losses: number;
  pushes: number;
  win_rate_pct: number;
  net_units: number;
  roi_pct: number;
  starting_bankroll: number;
  current_bankroll: number;
  equity_curve: EquityPoint[];
}

export interface EdgeBucket {
  edge_bucket: string;
  trades: number;
  avg_edge_pct: number;
  net_units: number;
  roi_pct: number;
}

export interface EdgeAnalytics {
  avg_edge_pct: number;
  buckets: EdgeBucket[];
}

export interface BankrollSnapshot {
  date: string;
  starting_bankroll: number;
  ending_bankroll: number;
  trades_count: number;
  units_won: number;
  units_lost: number;
  roi_pct: number;
  cumulative_roi_pct: number;
}

export interface ApiUsageSummary {
  total_calls: number;
  total_credits_used: number;
  latest_credits_remaining: number;
  last_called_at: string | null;
}

export interface PollResult {
  status: string;
  sports_polled: string[];
  detail: string;
}

export interface SystemStats {
  total_trades: number;
  total_events: number;
  total_snapshots: number;
  total_odds_lines: number;
  active_sports: number;
}

export interface SeedResult {
  status: string;
  detail: string;
}
