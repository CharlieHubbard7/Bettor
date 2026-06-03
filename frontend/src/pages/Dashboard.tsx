import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  AreaChart,
  Area,
  ResponsiveContainer,
  Tooltip as RTooltip,
  YAxis,
} from "recharts";
import { useBankroll, useCredits, useOpportunities, usePnl } from "@/hooks";
import { api } from "@/api/client";
import { Column, DataTable } from "@/components/DataTable";
import { EdgeBadge } from "@/components/EdgeBadge";
import { PriceDisplay } from "@/components/PriceDisplay";
import { StatCard } from "@/components/StatCard";
import { Card, Button, useToastStore } from "@/components/ui";
import { EmptyState, ErrorState, LoadingSpinner, PageHeader } from "@/components/feedback";
import { tradeLoggerLink } from "@/lib/links";
import {
  formatBook,
  formatDateTime,
  formatDollars,
  formatMarket,
  formatPct,
  formatUnits,
} from "@/lib/format";
import type { BankrollSnapshot, EdgeOpportunity } from "@/types";

function rangeTotals(snaps: BankrollSnapshot[], days: number) {
  const slice = days > 0 ? snaps.slice(-days) : snaps;
  const units = slice.reduce((acc, s) => acc + s.units_won - s.units_lost, 0);
  const dollars = slice.reduce(
    (acc, s) => acc + (s.ending_bankroll - s.starting_bankroll),
    0
  );
  return { units, dollars };
}

export function Dashboard() {
  const navigate = useNavigate();
  const opps = useOpportunities();
  const pnl = usePnl();
  const credits = useCredits();
  const bankroll = useBankroll();
  const pushToast = useToastStore((s) => s.push);

  const columns: Column<EdgeOpportunity>[] = useMemo(
    () => [
      {
        key: "event",
        header: "Event",
        render: (o) =>
          o.away_team && o.home_team ? `${o.away_team} @ ${o.home_team}` : o.event_id,
      },
      { key: "market", header: "Market", render: (o) => formatMarket(o.market_key) },
      {
        key: "outcome",
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
        header: "Our Prob",
        align: "right",
        render: (o) => formatPct(o.our_prob, 1),
      },
      {
        key: "book",
        header: "Book Prob",
        align: "right",
        render: (o) => formatPct(o.book_implied_prob, 1),
      },
      {
        key: "price",
        header: "Best Price",
        align: "right",
        render: (o) => <PriceDisplay american={o.best_price_american} />,
      },
      {
        key: "bestbook",
        header: "Book",
        render: (o) => formatBook(o.best_book),
      },
      {
        key: "kelly",
        header: "Kelly",
        align: "right",
        render: (o) => formatPct(o.kelly_fraction, 1),
      },
      {
        key: "units",
        header: "Units",
        align: "right",
        render: (o) => o.recommended_stake_units.toFixed(2),
      },
    ],
    []
  );

  const allTime = bankroll.data ? rangeTotals(bankroll.data, 0) : null;
  const week = bankroll.data ? rangeTotals(bankroll.data, 7) : null;
  const today = bankroll.data ? rangeTotals(bankroll.data, 1) : null;
  const spark =
    bankroll.data?.slice(-7).map((s) => ({ date: s.date, v: s.ending_bankroll })) ??
    [];

  const handlePoll = async () => {
    try {
      await api.system.poll();
      pushToast("Poll complete — odds refreshed");
      opps.refetch();
      credits.refetch();
    } catch (e) {
      pushToast(e instanceof Error ? e.message : "Poll failed", "error");
    }
  };

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle="Live edge feed and account overview"
        action={<Button onClick={handlePoll}>Poll Now</Button>}
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left: opportunity feed */}
        <div className="lg:col-span-2">
          <Card
            title="Opportunity Feed"
            subtitle={
              opps.data
                ? `${opps.data.length} live +EV plays · refreshes every 60s`
                : undefined
            }
            action={
              <span className="text-xs text-zinc-600">
                {opps.loading ? "updating…" : `as of ${formatDateTime(new Date().toISOString())}`}
              </span>
            }
          >
            {opps.loading && !opps.data ? (
              <LoadingSpinner label="Loading opportunities…" />
            ) : opps.error ? (
              <ErrorState message={opps.error} onRetry={opps.refetch} />
            ) : opps.data && opps.data.length > 0 ? (
              <DataTable
                columns={columns}
                rows={opps.data}
                rowKey={(o) => `${o.event_id}-${o.market_key}-${o.outcome_name}`}
                initialSort={{ key: "edge", dir: "desc" }}
                onRowClick={(o) => navigate(tradeLoggerLink(o))}
              />
            ) : (
              <EmptyState title="No opportunities above threshold">
                Trigger a poll to pull fresh odds, then check back.
                <div className="mt-3">
                  <Button onClick={handlePoll}>Poll Now</Button>
                </div>
              </EmptyState>
            )}
          </Card>
        </div>

        {/* Right: widgets */}
        <div className="flex flex-col gap-6">
          <Card title="P&L">
            {pnl.loading && !pnl.data ? (
              <LoadingSpinner />
            ) : pnl.error ? (
              <ErrorState message={pnl.error} onRetry={pnl.refetch} />
            ) : (
              <div className="grid grid-cols-1 gap-3">
                <StatCard
                  label="Today"
                  value={formatUnits(today?.units ?? 0)}
                  delta={formatDollars(today?.dollars ?? 0)}
                  deltaTone={(today?.dollars ?? 0) >= 0 ? "profit" : "loss"}
                />
                <StatCard
                  label="This Week"
                  value={formatUnits(week?.units ?? 0)}
                  delta={formatDollars(week?.dollars ?? 0)}
                  deltaTone={(week?.dollars ?? 0) >= 0 ? "profit" : "loss"}
                />
                <StatCard
                  label="All Time"
                  value={formatUnits(allTime?.units ?? pnl.data?.net_units ?? 0)}
                  delta={formatDollars(allTime?.dollars ?? 0)}
                  deltaTone={(allTime?.dollars ?? 0) >= 0 ? "profit" : "loss"}
                  hint={pnl.data ? `ROI ${pnl.data.roi_pct.toFixed(1)}%` : undefined}
                />
              </div>
            )}
          </Card>

          <Card title="API Credits" action={<Button variant="ghost" onClick={handlePoll}>Poll</Button>}>
            {credits.loading && !credits.data ? (
              <LoadingSpinner />
            ) : credits.data ? (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-zinc-500">Remaining</span>
                  <span className="tabular-nums text-zinc-200">
                    {credits.data.latest_credits_remaining.toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-500">Used</span>
                  <span className="tabular-nums text-zinc-200">
                    {credits.data.total_credits_used.toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-500">Last poll</span>
                  <span className="text-zinc-400">
                    {credits.data.last_called_at
                      ? formatDateTime(credits.data.last_called_at)
                      : "never"}
                  </span>
                </div>
              </div>
            ) : (
              <ErrorState message={credits.error ?? "unavailable"} onRetry={credits.refetch} />
            )}
          </Card>

          <Card title="Bankroll">
            {bankroll.data && bankroll.data.length > 0 ? (
              <div>
                <div className="flex items-baseline justify-between">
                  <span className="text-2xl font-semibold tabular-nums text-zinc-100">
                    {formatDollars(bankroll.data[bankroll.data.length - 1].ending_bankroll)}
                  </span>
                  <span
                    className={`text-sm tabular-nums ${
                      (today?.dollars ?? 0) >= 0
                        ? "text-signal-profit"
                        : "text-signal-loss"
                    }`}
                  >
                    {formatDollars(today?.dollars ?? 0)} today
                  </span>
                </div>
                <div className="mt-3 h-16">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={spark} margin={{ top: 4, bottom: 0, left: 0, right: 0 }}>
                      <YAxis hide domain={["dataMin", "dataMax"]} />
                      <RTooltip
                        contentStyle={{
                          background: "#27272a",
                          border: "1px solid #3f3f46",
                          borderRadius: 6,
                          fontSize: 12,
                        }}
                        formatter={(v: number) => formatDollars(v)}
                      />
                      <Area
                        type="monotone"
                        dataKey="v"
                        stroke="#34d399"
                        fill="#34d39922"
                        strokeWidth={2}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
                <div className="mt-1 text-xs text-zinc-600">last 7 days</div>
              </div>
            ) : (
              <LoadingSpinner />
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
