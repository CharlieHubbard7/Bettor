import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useCLV, useEvents, usePnl, useTrades } from "@/hooks";
import { Card } from "@/components/ui";
import { ErrorState, LoadingSpinner, PageHeader } from "@/components/feedback";
import { formatBook, formatSport } from "@/lib/format";

const AXIS = { stroke: "#52525b", fontSize: 11 };
const GRID = "#27272a";
const SPORT_COLORS: Record<string, string> = {
  americanfootball_nfl: "#34d399",
  basketball_nba: "#60a5fa",
  baseball_mlb: "#fbbf24",
  unknown: "#94a3b8",
};
const tooltipStyle = {
  background: "#27272a",
  border: "1px solid #3f3f46",
  borderRadius: 6,
  fontSize: 12,
};

function linregEndpoints(points: { x: number; y: number }[]) {
  const n = points.length;
  if (n < 2) return null;
  const sx = points.reduce((a, p) => a + p.x, 0);
  const sy = points.reduce((a, p) => a + p.y, 0);
  const sxx = points.reduce((a, p) => a + p.x * p.x, 0);
  const sxy = points.reduce((a, p) => a + p.x * p.y, 0);
  const denom = n * sxx - sx * sx;
  if (denom === 0) return null;
  const slope = (n * sxy - sx * sy) / denom;
  const intercept = (sy - slope * sx) / n;
  const xs = points.map((p) => p.x);
  const x1 = Math.min(...xs);
  const x2 = Math.max(...xs);
  return [
    { x: x1, y: slope * x1 + intercept },
    { x: x2, y: slope * x2 + intercept },
  ];
}

export function Analytics() {
  const pnl = usePnl();
  const clv = useCLV();
  const trades = useTrades();
  const events = useEvents();

  const sportByEvent = useMemo(() => {
    const m = new Map<string, string>();
    for (const e of events.data ?? []) m.set(e.id, e.sport_key);
    return m;
  }, [events.data]);

  const settled = useMemo(
    () => (trades.data ?? []).filter((t) => t.status === "settled"),
    [trades.data]
  );

  // 1. Equity curve.
  const equity = (pnl.data?.equity_curve ?? []).map((p) => ({
    date: p.date.slice(5),
    units: Number(p.cumulative_pnl_units.toFixed(3)),
  }));

  // 2. CLV distribution histogram.
  const clvBuckets = useMemo(() => {
    const edges = [-6, -4, -2, 0, 2, 4, 6];
    const labels = ["<-6", "-6..-4", "-4..-2", "-2..0", "0..2", "2..4", "4..6", "6+"];
    const counts = new Array(labels.length).fill(0);
    for (const t of trades.data ?? []) {
      if (t.clv == null) continue;
      let idx = edges.findIndex((e) => t.clv! < e);
      if (idx === -1) idx = labels.length - 1;
      counts[idx]++;
    }
    return labels.map((label, i) => ({ label, count: counts[i], positive: i >= 4 }));
  }, [trades.data]);

  // 3. Edge vs ROI scatter, split by sport for coloring.
  const scatterBySport = useMemo(() => {
    const groups: Record<string, { x: number; y: number }[]> = {};
    for (const t of settled) {
      const sport = sportByEvent.get(t.event_id) ?? "unknown";
      (groups[sport] ??= []).push({
        x: Number((t.edge_pct * 100).toFixed(2)),
        y: Number((t.profit_loss_units ?? 0).toFixed(3)),
      });
    }
    return groups;
  }, [settled, sportByEvent]);

  const trend = useMemo(
    () => linregEndpoints(Object.values(scatterBySport).flat()),
    [scatterBySport]
  );

  // 4. P&L by sport (won vs lost units).
  const pnlByCategory = useMemo(() => {
    const map = new Map<string, { won: number; lost: number }>();
    for (const t of settled) {
      const sport = formatSport(sportByEvent.get(t.event_id) ?? "unknown");
      const entry = map.get(sport) ?? { won: 0, lost: 0 };
      const pl = t.profit_loss_units ?? 0;
      if (pl >= 0) entry.won += pl;
      else entry.lost += Math.abs(pl);
      map.set(sport, entry);
    }
    return [...map.entries()].map(([sport, v]) => ({
      sport,
      won: Number(v.won.toFixed(2)),
      lost: Number(v.lost.toFixed(2)),
    }));
  }, [settled, sportByEvent]);

  // 5. Rolling 50-bet win rate.
  const rollingWinRate = useMemo(() => {
    const ordered = [...settled]
      .filter((t) => t.result === "win" || t.result === "loss")
      .sort((a, b) => a.created_at.localeCompare(b.created_at));
    const window = 50;
    const out: { n: number; rate: number }[] = [];
    for (let i = 0; i < ordered.length; i++) {
      const start = Math.max(0, i - window + 1);
      const slice = ordered.slice(start, i + 1);
      const wins = slice.filter((t) => t.result === "win").length;
      out.push({ n: i + 1, rate: Number(((wins / slice.length) * 100).toFixed(1)) });
    }
    return out;
  }, [settled]);

  // 6. CLV by bookmaker.
  const clvByBook = useMemo(() => {
    const map = new Map<string, number[]>();
    for (const t of trades.data ?? []) {
      if (t.clv == null) continue;
      const arr = map.get(t.bookmaker) ?? [];
      arr.push(t.clv);
      map.set(t.bookmaker, arr);
    }
    return [...map.entries()]
      .map(([book, vals]) => ({
        book: formatBook(book),
        clv: Number((vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(2)),
      }))
      .sort((a, b) => b.clv - a.clv);
  }, [trades.data]);

  const anyLoading = pnl.loading || trades.loading || clv.loading;
  const anyError = pnl.error || trades.error || clv.error;

  if (anyLoading && !pnl.data) return <LoadingSpinner label="Loading analytics…" />;
  if (anyError)
    return <ErrorState message={anyError} onRetry={() => { pnl.refetch(); trades.refetch(); clv.refetch(); }} />;

  return (
    <div>
      <PageHeader title="Analytics" subtitle="Is the edge real? Watch the CLV." />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Equity Curve" subtitle="Cumulative P&L (units) over time">
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={equity}>
              <CartesianGrid stroke={GRID} />
              <XAxis dataKey="date" {...AXIS} minTickGap={24} />
              <YAxis {...AXIS} />
              <Tooltip contentStyle={tooltipStyle} />
              <ReferenceLine y={0} stroke="#52525b" strokeDasharray="3 3" />
              <Line type="monotone" dataKey="units" stroke="#34d399" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card title="CLV Distribution" subtitle={clv.data ? `mean ${clv.data.mean.toFixed(2)}% · ${clv.data.pct_positive.toFixed(0)}% positive` : undefined}>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={clvBuckets}>
              <CartesianGrid stroke={GRID} />
              <XAxis dataKey="label" {...AXIS} />
              <YAxis {...AXIS} allowDecimals={false} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="count">
                {clvBuckets.map((b, i) => (
                  <Cell key={i} fill={b.positive ? "#34d399" : "#f87171"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Edge % vs Actual P&L" subtitle="Does predicted edge translate to results?">
          <ResponsiveContainer width="100%" height={240}>
            <ScatterChart>
              <CartesianGrid stroke={GRID} />
              <XAxis type="number" dataKey="x" name="Edge %" unit="%" {...AXIS} />
              <YAxis type="number" dataKey="y" name="P&L units" {...AXIS} />
              <Tooltip contentStyle={tooltipStyle} cursor={{ strokeDasharray: "3 3" }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {Object.entries(scatterBySport).map(([sport, pts]) => (
                <Scatter
                  key={sport}
                  name={formatSport(sport)}
                  data={pts}
                  fill={SPORT_COLORS[sport] ?? SPORT_COLORS.unknown}
                />
              ))}
              {trend && (
                <ReferenceLine
                  segment={trend}
                  stroke="#e4e4e7"
                  strokeDasharray="4 4"
                  ifOverflow="extendDomain"
                />
              )}
            </ScatterChart>
          </ResponsiveContainer>
        </Card>

        <Card title="P&L by Sport" subtitle="Units won vs lost">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={pnlByCategory}>
              <CartesianGrid stroke={GRID} />
              <XAxis dataKey="sport" {...AXIS} />
              <YAxis {...AXIS} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="won" fill="#34d399" />
              <Bar dataKey="lost" fill="#f87171" />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Rolling Win Rate" subtitle="50-bet window">
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={rollingWinRate}>
              <CartesianGrid stroke={GRID} />
              <XAxis dataKey="n" {...AXIS} />
              <YAxis domain={[30, 70]} {...AXIS} unit="%" />
              <Tooltip contentStyle={tooltipStyle} />
              <ReferenceLine y={50} stroke="#52525b" strokeDasharray="3 3" />
              <ReferenceLine y={55} stroke="#34d399" strokeDasharray="3 3" />
              <Line type="monotone" dataKey="rate" stroke="#60a5fa" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card title="CLV by Bookmaker" subtitle="Which books have the softest lines?">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={clvByBook} layout="vertical">
              <CartesianGrid stroke={GRID} />
              <XAxis type="number" {...AXIS} unit="%" />
              <YAxis type="category" dataKey="book" width={80} {...AXIS} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="clv">
                {clvByBook.map((b, i) => (
                  <Cell key={i} fill={b.clv >= 0 ? "#34d399" : "#f87171"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>
    </div>
  );
}
