import { useMemo, useState } from "react";
import { useEvents, useTrades } from "@/hooks";
import { Column, DataTable } from "@/components/DataTable";
import { Badge, type BadgeTone } from "@/components/Badge";
import { PriceDisplay } from "@/components/PriceDisplay";
import { StatCard } from "@/components/StatCard";
import { Button, Card } from "@/components/ui";
import { ErrorState, LoadingSpinner, PageHeader } from "@/components/feedback";
import {
  formatBook,
  formatDate,
  formatDateTime,
  formatMarket,
  formatPct,
  formatPctValue,
  formatSport,
  formatUnits,
} from "@/lib/format";
import type { Trade, TradeResult, TradeStatus, TradeType } from "@/types";

const PAGE_SIZE = 25;

const RESULT_TONE: Record<TradeResult, BadgeTone> = {
  win: "profit",
  loss: "loss",
  push: "warn",
};

function clvTone(clv: number | null): string {
  if (clv == null) return "text-zinc-600";
  return clv > 0 ? "text-signal-profit" : clv < 0 ? "text-signal-loss" : "text-zinc-400";
}

function toCsv(trades: Trade[]): string {
  const headers = [
    "date",
    "event_id",
    "market",
    "outcome",
    "entry_price",
    "edge_pct",
    "clv",
    "stake_units",
    "result",
    "pnl_units",
    "pnl_dollars",
    "bookmaker",
    "trade_type",
    "status",
  ];
  const rows = trades.map((t) =>
    [
      t.created_at,
      t.event_id,
      t.market_key,
      `"${t.outcome_name}"`,
      t.entry_price_american,
      t.edge_pct,
      t.clv ?? "",
      t.stake_units,
      t.result ?? "",
      t.profit_loss_units ?? "",
      t.profit_loss_dollars ?? "",
      t.bookmaker,
      t.trade_type,
      t.status,
    ].join(",")
  );
  return [headers.join(","), ...rows].join("\n");
}

export function TradeJournal() {
  const { data, loading, error, refetch } = useTrades();
  const events = useEvents();
  const [status, setStatus] = useState<TradeStatus | "">("");
  const [type, setType] = useState<TradeType | "">("");
  const [result, setResult] = useState<TradeResult | "">("");
  const [sport, setSport] = useState("");
  const [market, setMarket] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [page, setPage] = useState(0);

  const sportByEvent = useMemo(() => {
    const map = new Map<string, string>();
    for (const e of events.data ?? []) map.set(e.id, e.sport_key);
    return map;
  }, [events.data]);

  const filtered = useMemo(() => {
    const rows = data ?? [];
    return rows.filter((t) => {
      if (status && t.status !== status) return false;
      if (type && t.trade_type !== type) return false;
      if (result && t.result !== result) return false;
      if (market && t.market_key !== market) return false;
      if (sport && sportByEvent.get(t.event_id) !== sport) return false;
      if (startDate && t.created_at < startDate) return false;
      if (endDate && t.created_at > `${endDate}T23:59:59`) return false;
      return true;
    });
  }, [data, status, type, result, market, sport, startDate, endDate, sportByEvent]);

  const summary = useMemo(() => {
    const settled = filtered.filter((t) => t.status === "settled");
    const wins = settled.filter((t) => t.result === "win").length;
    const decisive = settled.filter((t) => t.result === "win" || t.result === "loss").length;
    const clvs = filtered.filter((t) => t.clv != null).map((t) => t.clv as number);
    const units = settled.reduce((a, t) => a + (t.profit_loss_units ?? 0), 0);
    const dollars = settled.reduce((a, t) => a + (t.profit_loss_dollars ?? 0), 0);
    const staked = settled.reduce((a, t) => a + t.stake_units, 0);
    return {
      total: filtered.length,
      winRate: decisive ? (wins / decisive) * 100 : 0,
      avgClv: clvs.length ? clvs.reduce((a, b) => a + b, 0) / clvs.length : 0,
      units,
      dollars,
      roi: staked ? (units / staked) * 100 : 0,
    };
  }, [filtered]);

  const pageRows = filtered.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));

  const exportCsv = () => {
    const blob = new Blob([toCsv(filtered)], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "bettor-trades.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const columns: Column<Trade>[] = [
    { key: "date", header: "Date", sortValue: (t) => t.created_at, render: (t) => formatDate(t.created_at) },
    {
      key: "sport",
      header: "Sport",
      render: (t) => formatSport(sportByEvent.get(t.event_id) ?? ""),
    },
    { key: "market", header: "Market", render: (t) => formatMarket(t.market_key) },
    { key: "outcome", header: "Outcome", render: (t) => <span className="text-zinc-200">{t.outcome_name}</span> },
    { key: "entry", header: "Entry", align: "right", render: (t) => <PriceDisplay american={t.entry_price_american} /> },
    { key: "edge", header: "Edge", align: "right", sortValue: (t) => t.edge_pct, render: (t) => formatPct(t.edge_pct) },
    {
      key: "clv",
      header: "CLV",
      align: "right",
      sortValue: (t) => t.clv ?? -999,
      render: (t) => (
        <span className={clvTone(t.clv)}>{t.clv == null ? "—" : formatPctValue(t.clv, 2, true)}</span>
      ),
    },
    { key: "stake", header: "Stake", align: "right", render: (t) => `${t.stake_units.toFixed(2)}u` },
    {
      key: "result",
      header: "Result",
      render: (t) =>
        t.result ? <Badge tone={RESULT_TONE[t.result]}>{t.result}</Badge> : <span className="text-zinc-600">open</span>,
    },
    {
      key: "pnl",
      header: "P&L",
      align: "right",
      sortValue: (t) => t.profit_loss_units ?? 0,
      render: (t) =>
        t.profit_loss_units == null ? (
          "—"
        ) : (
          <span className={t.profit_loss_units >= 0 ? "text-signal-profit" : "text-signal-loss"}>
            {formatUnits(t.profit_loss_units)}
          </span>
        ),
    },
    {
      key: "type",
      header: "Type",
      render: (t) => <Badge tone={t.trade_type === "real" ? "info" : "zinc"}>{t.trade_type}</Badge>,
    },
    { key: "book", header: "Book", render: (t) => formatBook(t.bookmaker) },
  ];

  return (
    <div>
      <PageHeader
        title="Trade Journal"
        subtitle={`${summary.total} trades`}
        action={<Button onClick={exportCsv}>Export CSV</Button>}
      />

      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-6">
        <StatCard label="Trades" value={summary.total} />
        <StatCard label="Win Rate" value={formatPctValue(summary.winRate)} />
        <StatCard
          label="Avg CLV"
          value={formatPctValue(summary.avgClv, 2, true)}
          deltaTone={summary.avgClv >= 0 ? "profit" : "loss"}
        />
        <StatCard
          label="Units"
          value={formatUnits(summary.units)}
          deltaTone={summary.units >= 0 ? "profit" : "loss"}
        />
        <StatCard label="P&L $" value={`$${summary.dollars.toFixed(2)}`} />
        <StatCard label="ROI" value={formatPctValue(summary.roi)} />
      </div>

      <Card className="mb-4">
        <div className="flex flex-wrap items-end gap-3 text-sm">
          <Select label="Sport" value={sport} onChange={setSport} options={[["", "All"], ["americanfootball_nfl", "NFL"], ["basketball_nba", "NBA"], ["baseball_mlb", "MLB"]]} />
          <Select label="Market" value={market} onChange={setMarket} options={[["", "All"], ["h2h", "Moneyline"], ["spreads", "Spread"], ["totals", "Total"], ["player_points", "Props"]]} />
          <Select label="Status" value={status} onChange={(v) => setStatus(v as TradeStatus | "")} options={[["", "All"], ["open", "Open"], ["settled", "Settled"], ["void", "Void"]]} />
          <Select label="Type" value={type} onChange={(v) => setType(v as TradeType | "")} options={[["", "All"], ["paper", "Paper"], ["real", "Real"]]} />
          <Select label="Result" value={result} onChange={(v) => setResult(v as TradeResult | "")} options={[["", "All"], ["win", "Win"], ["loss", "Loss"], ["push", "Push"]]} />
          <label className="flex flex-col gap-1">
            <span className="text-xs uppercase tracking-wide text-zinc-500">From</span>
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="rounded border border-surface-border bg-surface px-2 py-1 text-zinc-200" />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs uppercase tracking-wide text-zinc-500">To</span>
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="rounded border border-surface-border bg-surface px-2 py-1 text-zinc-200" />
          </label>
        </div>
      </Card>

      {loading && !data ? (
        <LoadingSpinner label="Loading trades…" />
      ) : error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : (
        <>
          <DataTable
            columns={columns}
            rows={pageRows}
            rowKey={(t) => t.id}
            initialSort={{ key: "date", dir: "desc" }}
            emptyLabel="No trades match these filters."
            expandable={(t) => (
              <div className="grid grid-cols-2 gap-x-8 gap-y-1 text-xs text-zinc-400 sm:grid-cols-3">
                <Detail label="Our Prob" value={formatPct(t.our_prob, 2)} />
                <Detail label="Sharp Consensus" value={formatPct(t.sharp_consensus_prob, 2)} />
                <Detail label="Full Kelly" value={formatPct(t.kelly_fraction, 2)} />
                <Detail label="Entry Decimal" value={t.entry_price_decimal.toFixed(3)} />
                <Detail label="Closing Price" value={t.closing_price_american != null ? String(t.closing_price_american) : "—"} />
                <Detail label="Stake $" value={t.stake_dollars != null ? `$${t.stake_dollars.toFixed(2)}` : "—"} />
                <Detail label="Created" value={formatDateTime(t.created_at)} />
                <Detail label="Settled" value={t.settled_at ? formatDateTime(t.settled_at) : "—"} />
                <Detail label="Notes" value={t.notes ?? "—"} />
              </div>
            )}
          />
          <div className="mt-3 flex items-center justify-between text-sm text-zinc-500">
            <span>
              Page {page + 1} of {totalPages}
            </span>
            <div className="flex gap-2">
              <Button variant="secondary" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                Prev
              </Button>
              <Button variant="secondary" disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}>
                Next
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-zinc-600">{label}: </span>
      <span className="text-zinc-300">{value}</span>
    </div>
  );
}

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: [string, string][];
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-zinc-500">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded border border-surface-border bg-surface px-2 py-1 text-zinc-200"
      >
        {options.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </label>
  );
}
