import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useApi, useOpportunities } from "@/hooks";
import { api } from "@/api/client";
import { Column, DataTable } from "@/components/DataTable";
import { EdgeBadge } from "@/components/EdgeBadge";
import { PriceDisplay } from "@/components/PriceDisplay";
import { Badge } from "@/components/Badge";
import { Button, Card } from "@/components/ui";
import { ErrorState, LoadingSpinner, PageHeader } from "@/components/feedback";
import { tradeLoggerLink } from "@/lib/links";
import {
  formatBook,
  formatMarket,
  formatPct,
  impliedProbability,
} from "@/lib/format";
import type { EdgeOpportunity } from "@/types";

const SPORTS = [
  { key: "americanfootball_nfl", label: "NFL" },
  { key: "basketball_nba", label: "NBA" },
  { key: "baseball_mlb", label: "MLB" },
];
const MARKETS = [
  { key: "h2h", label: "Moneyline" },
  { key: "spreads", label: "Spread" },
  { key: "totals", label: "Total" },
  { key: "player_points", label: "Player Props" },
];
const BOOKS = ["draftkings", "fanduel", "betmgm", "caesars", "pinnacle", "bookmaker"];

/** Inline book-by-book comparison for one opportunity's event + market. */
function OddsComparison({
  eventId,
  marketKey,
  anchorBook,
}: {
  eventId: string;
  marketKey: string;
  anchorBook: string;
}) {
  const { data, loading, error } = useApi(
    () => api.odds.byEvent(eventId),
    [eventId]
  );

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorState message={error} />;
  if (!data) return null;

  const lines = data.lines.filter((l) => l.market_key === marketKey);
  if (lines.length === 0)
    return <div className="text-xs text-zinc-500">No line detail available.</div>;

  // Anchor implied probs per outcome (for delta).
  const anchorByOutcome = new Map<string, number>();
  for (const l of lines) {
    if (l.bookmaker_key === anchorBook) {
      anchorByOutcome.set(l.outcome_name, impliedProbability(l.price_decimal));
    }
  }
  // Best decimal per outcome (highlight).
  const bestByOutcome = new Map<string, number>();
  for (const l of lines) {
    const cur = bestByOutcome.get(l.outcome_name) ?? 0;
    if (l.price_decimal > cur) bestByOutcome.set(l.outcome_name, l.price_decimal);
  }

  return (
    <div>
      <div className="mb-2 text-xs text-zinc-500">
        Sharp anchor: <Badge tone="info">{formatBook(anchorBook)}</Badge>
      </div>
      <table className="w-full text-xs">
        <thead className="text-zinc-500">
          <tr>
            <th className="px-2 py-1 text-left">Book</th>
            <th className="px-2 py-1 text-left">Outcome</th>
            <th className="px-2 py-1 text-right">American</th>
            <th className="px-2 py-1 text-right">Decimal</th>
            <th className="px-2 py-1 text-right">Implied</th>
            <th className="px-2 py-1 text-right">Δ vs anchor</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((l) => {
            const implied = impliedProbability(l.price_decimal);
            const anchor = anchorByOutcome.get(l.outcome_name);
            const delta = anchor != null ? implied - anchor : null;
            const isBest = bestByOutcome.get(l.outcome_name) === l.price_decimal;
            return (
              <tr
                key={`${l.bookmaker_key}-${l.outcome_name}-${l.point ?? ""}`}
                className="border-t border-surface-border/60"
              >
                <td className="px-2 py-1">
                  {formatBook(l.bookmaker_key)}
                  {l.bookmaker_key === anchorBook && (
                    <span className="ml-1 text-zinc-600">★</span>
                  )}
                </td>
                <td className="px-2 py-1">
                  {l.outcome_name}
                  {l.point != null && (
                    <span className="text-zinc-500"> {l.point > 0 ? `+${l.point}` : l.point}</span>
                  )}
                </td>
                <td
                  className={`px-2 py-1 text-right font-mono ${
                    isBest ? "rounded bg-signal-profit/15 text-signal-profit" : ""
                  }`}
                >
                  {l.price_american > 0 ? `+${l.price_american}` : l.price_american}
                </td>
                <td className="px-2 py-1 text-right tabular-nums">
                  {l.price_decimal.toFixed(3)}
                </td>
                <td className="px-2 py-1 text-right tabular-nums">
                  {formatPct(implied, 1)}
                </td>
                <td
                  className={`px-2 py-1 text-right tabular-nums ${
                    delta == null
                      ? "text-zinc-600"
                      : delta < 0
                        ? "text-signal-profit"
                        : "text-signal-loss"
                  }`}
                >
                  {delta == null ? "—" : formatPct(delta, 1, true)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function Opportunities() {
  const navigate = useNavigate();
  const { data, loading, error, refetch } = useOpportunities();
  const [sports, setSports] = useState<string[]>([]);
  const [markets, setMarkets] = useState<string[]>([]);
  const [books, setBooks] = useState<string[]>([]);
  const [minEdge, setMinEdge] = useState(2);

  const toggle = (
    list: string[],
    setList: (v: string[]) => void,
    value: string
  ) => setList(list.includes(value) ? list.filter((x) => x !== value) : [...list, value]);

  const filtered = useMemo(() => {
    const rows = data ?? [];
    return rows.filter((o) => {
      if (markets.length && !markets.some((m) => o.market_key.startsWith(m.replace("player_points", "player_")) || o.market_key === m)) {
        return false;
      }
      if (books.length && !books.includes(o.best_book)) return false;
      if (o.edge_pct * 100 < minEdge) return false;
      return true;
      // NOTE: sport filtering needs event→sport mapping; opportunities carry team
      // names but not sport_key, so sport filter is best-effort via the backend param.
    });
  }, [data, markets, books, minEdge]);

  const columns: Column<EdgeOpportunity>[] = [
    {
      key: "event",
      header: "Event",
      render: (o) =>
        o.away_team && o.home_team ? `${o.away_team} @ ${o.home_team}` : o.event_id,
    },
    { key: "market", header: "Market", render: (o) => formatMarket(o.market_key) },
    {
      key: "player",
      header: "Player",
      render: (o) => o.player_name ?? <span className="text-zinc-600">—</span>,
    },
    {
      key: "pick",
      header: "Pick",
      render: (o) => <span className="text-zinc-200">{o.outcome_name}</span>,
    },
    {
      key: "edge",
      header: "Edge",
      align: "right",
      sortValue: (o) => o.edge_pct,
      render: (o) => <EdgeBadge edge={o.edge_pct} />,
    },
    {
      key: "our",
      header: "Our",
      align: "right",
      sortValue: (o) => o.our_prob,
      render: (o) => formatPct(o.our_prob, 1),
    },
    {
      key: "book",
      header: "Book",
      align: "right",
      sortValue: (o) => o.book_implied_prob,
      render: (o) => formatPct(o.book_implied_prob, 1),
    },
    {
      key: "price",
      header: "Price",
      align: "right",
      sortValue: (o) => o.best_price_american,
      render: (o) => <PriceDisplay american={o.best_price_american} />,
    },
    { key: "bestbook", header: "Best Book", render: (o) => formatBook(o.best_book) },
    {
      key: "anchor",
      header: "Anchor",
      render: (o) => <Badge tone="info">{formatBook(o.sharp_anchor_book)}</Badge>,
    },
    {
      key: "fullkelly",
      header: "Full Kelly",
      align: "right",
      sortValue: (o) => o.kelly_fraction,
      render: (o) => formatPct(o.kelly_fraction, 1),
    },
    {
      key: "units",
      header: "Units",
      align: "right",
      sortValue: (o) => o.recommended_stake_units,
      render: (o) => o.recommended_stake_units.toFixed(2),
    },
    {
      key: "action",
      header: "",
      render: (o) => (
        <Button
          variant="primary"
          onClick={(e) => {
            e.stopPropagation();
            navigate(tradeLoggerLink(o));
          }}
        >
          Log
        </Button>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Opportunities"
        subtitle="All current +EV plays above threshold"
        action={<Button onClick={refetch}>Refresh</Button>}
      />

      <Card className="mb-4">
        <div className="flex flex-wrap items-end gap-4 text-sm">
          <FilterGroup
            label="Sport"
            options={SPORTS.map((s) => ({ value: s.key, label: s.label }))}
            selected={sports}
            onToggle={(v) => toggle(sports, setSports, v)}
          />
          <FilterGroup
            label="Market"
            options={MARKETS.map((m) => ({ value: m.key, label: m.label }))}
            selected={markets}
            onToggle={(v) => toggle(markets, setMarkets, v)}
          />
          <FilterGroup
            label="Bookmaker"
            options={BOOKS.map((b) => ({ value: b, label: formatBook(b) }))}
            selected={books}
            onToggle={(v) => toggle(books, setBooks, v)}
          />
          <label className="flex flex-col gap-1">
            <span className="text-xs uppercase tracking-wide text-zinc-500">
              Min Edge %
            </span>
            <input
              type="number"
              value={minEdge}
              step={0.5}
              onChange={(e) => setMinEdge(Number(e.target.value))}
              className="w-20 rounded border border-surface-border bg-surface px-2 py-1 text-zinc-200"
            />
          </label>
        </div>
      </Card>

      {loading && !data ? (
        <LoadingSpinner label="Loading opportunities…" />
      ) : error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : (
        <DataTable
          columns={columns}
          rows={filtered}
          rowKey={(o) => `${o.event_id}-${o.market_key}-${o.outcome_name}`}
          initialSort={{ key: "edge", dir: "desc" }}
          emptyLabel="No opportunities match these filters."
          expandable={(o) => (
            <OddsComparison
              eventId={o.event_id}
              marketKey={o.market_key}
              anchorBook={o.sharp_anchor_book}
            />
          )}
        />
      )}
    </div>
  );
}

function FilterGroup({
  label,
  options,
  selected,
  onToggle,
}: {
  label: string;
  options: { value: string; label: string }[];
  selected: string[];
  onToggle: (value: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-zinc-500">{label}</span>
      <div className="flex flex-wrap gap-1">
        {options.map((opt) => {
          const active = selected.includes(opt.value);
          return (
            <button
              key={opt.value}
              onClick={() => onToggle(opt.value)}
              className={`rounded px-2 py-1 text-xs ring-1 ring-inset transition-colors ${
                active
                  ? "bg-signal-neutral/20 text-zinc-100 ring-signal-neutral/40"
                  : "bg-surface text-zinc-400 ring-surface-border hover:text-zinc-200"
              }`}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
