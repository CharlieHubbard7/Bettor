// Small formatting + betting-math helpers shared across the UI.

/** Format American odds with an explicit sign, e.g. 150 → "+150", -110 → "-110". */
export function formatAmerican(american: number): string {
  return american > 0 ? `+${american}` : `${american}`;
}

/** Convert American odds to decimal odds (mirrors backend no_vig.american_to_decimal). */
export function americanToDecimal(american: number): number {
  if (american === 0) return 1;
  return american > 0 ? 1 + american / 100 : 1 + 100 / Math.abs(american);
}

/** Convert decimal odds to American odds. */
export function decimalToAmerican(decimal: number): number {
  if (decimal <= 1) return 0;
  return decimal >= 2
    ? Math.round((decimal - 1) * 100)
    : Math.round(-100 / (decimal - 1));
}

/** Raw implied probability of decimal odds. */
export function impliedProbability(decimal: number): number {
  return decimal > 1 ? 1 / decimal : 0;
}

/** Full Kelly fraction; 0 if edge is non-positive. */
export function fullKelly(ourProb: number, decimalOdds: number): number {
  const b = decimalOdds - 1;
  if (b <= 0) return 0;
  const f = (b * ourProb - (1 - ourProb)) / b;
  return Math.max(0, f);
}

/** Format a fraction (0.034) as a percentage string ("+3.40%"). */
export function formatPct(fraction: number, digits = 2, signed = false): string {
  const value = fraction * 100;
  const sign = signed && value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}%`;
}

/** Format an already-percentage number (e.g. 55.0 from win_rate_pct). */
export function formatPctValue(value: number, digits = 1, signed = false): string {
  const sign = signed && value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}%`;
}

/** Format a dollar amount, e.g. 1256.02 → "$1,256.02". */
export function formatDollars(amount: number, digits = 2): string {
  return amount.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

/** Format units with a sign, e.g. 1.5 → "+1.50u". */
export function formatUnits(units: number, digits = 2): string {
  const sign = units > 0 ? "+" : "";
  return `${sign}${units.toFixed(digits)}u`;
}

/** Format an ISO timestamp as a short local date, e.g. "Jun 3, 2026". */
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/** Format an ISO timestamp as date + time. */
export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/** Short, human label for a market key. */
export function formatMarket(marketKey: string): string {
  const map: Record<string, string> = {
    h2h: "Moneyline",
    spreads: "Spread",
    totals: "Total",
  };
  if (map[marketKey]) return map[marketKey];
  if (marketKey.startsWith("player_")) {
    return marketKey
      .replace("player_", "")
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
  }
  return marketKey;
}

const SPORT_TITLES: Record<string, string> = {
  americanfootball_nfl: "NFL",
  basketball_nba: "NBA",
  baseball_mlb: "MLB",
  icehockey_nhl: "NHL",
  basketball_ncaab: "NCAAB",
};

/** Short title for a sport key. */
export function formatSport(sportKey: string): string {
  return SPORT_TITLES[sportKey] ?? sportKey;
}

/** Title-case a bookmaker key, e.g. "draftkings" → "DraftKings". */
export function formatBook(bookKey: string): string {
  const map: Record<string, string> = {
    draftkings: "DraftKings",
    fanduel: "FanDuel",
    betmgm: "BetMGM",
    caesars: "Caesars",
    pinnacle: "Pinnacle",
    bookmaker: "Bookmaker",
    betfair: "Betfair",
    circa: "Circa",
    consensus_average: "Consensus Avg",
  };
  return map[bookKey] ?? bookKey;
}
