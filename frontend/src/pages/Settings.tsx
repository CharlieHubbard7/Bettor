import { useState } from "react";
import { useCredits, useSystemStats } from "@/hooks";
import { useSettingsStore } from "@/store/settingsStore";
import { api } from "@/api/client";
import { Button, Card, useToastStore } from "@/components/ui";
import { StatCard } from "@/components/StatCard";
import { PageHeader } from "@/components/feedback";
import { formatSport } from "@/lib/format";

const SPORT_OPTIONS = [
  "americanfootball_nfl",
  "basketball_nba",
  "baseball_mlb",
  "basketball_ncaab",
  "icehockey_nhl",
  "soccer_epl",
];

const labelText = "text-xs uppercase tracking-wide text-zinc-500";

export function Settings() {
  const s = useSettingsStore();
  const credits = useCredits();
  const stats = useSystemStats();
  const pushToast = useToastStore((t) => t.push);
  const [revealKey, setRevealKey] = useState(false);
  const [busy, setBusy] = useState<"poll" | "seed" | null>(null);

  const maskedKey = s.oddsApiKey
    ? `${"•".repeat(Math.max(0, s.oddsApiKey.length - 4))}${s.oddsApiKey.slice(-4)}`
    : "";

  const poll = async () => {
    setBusy("poll");
    try {
      const r = await api.system.poll();
      pushToast(r.detail);
      credits.refetch();
      stats.refetch();
    } catch (e) {
      pushToast(e instanceof Error ? e.message : "Poll failed", "error");
    } finally {
      setBusy(null);
    }
  };

  const seed = async () => {
    setBusy("seed");
    try {
      const r = await api.system.seed();
      pushToast(r.detail);
      stats.refetch();
    } catch (e) {
      pushToast(e instanceof Error ? e.message : "Seed failed", "error");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div>
      <PageHeader title="Settings" subtitle="Configuration is stored locally in your browser" />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Section 1 — API */}
        <Card title="API Configuration">
          <div className="space-y-4">
            <label className="flex flex-col gap-1">
              <span className={labelText}>Odds API Key</span>
              <div className="flex gap-2">
                <input
                  type={revealKey ? "text" : "password"}
                  value={revealKey ? s.oddsApiKey : maskedKey}
                  onChange={(e) => s.setOddsApiKey(e.target.value)}
                  placeholder="Set ODDS_API_KEY in backend/.env for live polling"
                  className="flex-1 rounded border border-surface-border bg-surface px-3 py-2 text-zinc-200"
                />
                <Button variant="secondary" onClick={() => setRevealKey((v) => !v)}>
                  {revealKey ? "Hide" : "Reveal"}
                </Button>
              </div>
              <span className="text-xs text-zinc-600">
                Display only — the real key the backend uses lives in <code>.env</code>.
              </span>
            </label>

            <div className="flex items-center justify-between rounded border border-surface-border bg-surface px-3 py-2">
              <span className={labelText}>Credits Remaining</span>
              <span className="tabular-nums text-zinc-200">
                {credits.data ? credits.data.latest_credits_remaining.toLocaleString() : "—"}
              </span>
            </div>

            <label className="flex flex-col gap-1">
              <span className={labelText}>Polling Interval — {s.pollIntervalMinutes} min</span>
              <input
                type="range"
                min={5}
                max={60}
                step={5}
                value={s.pollIntervalMinutes}
                onChange={(e) => s.setPollIntervalMinutes(Number(e.target.value))}
              />
            </label>

            <div className="flex flex-col gap-2">
              <span className={labelText}>Active Sports</span>
              <div className="grid grid-cols-2 gap-2">
                {SPORT_OPTIONS.map((sport) => (
                  <label key={sport} className="flex items-center gap-2 text-sm text-zinc-300">
                    <input
                      type="checkbox"
                      checked={s.activeSports.includes(sport)}
                      onChange={() => s.toggleSport(sport)}
                    />
                    {formatSport(sport)}
                  </label>
                ))}
              </div>
            </div>
          </div>
        </Card>

        {/* Section 2 — Trading params */}
        <Card title="Trading Parameters">
          <div className="space-y-4">
            <div
              className={`flex items-center justify-between rounded-lg border p-3 ${
                s.paperTradingMode
                  ? "border-signal-warn/40 bg-signal-warn/10"
                  : "border-signal-loss/40 bg-signal-loss/10"
              }`}
            >
              <div>
                <div className="text-sm font-semibold text-zinc-100">Paper Trading Mode</div>
                <div className="text-xs text-zinc-500">
                  {s.paperTradingMode
                    ? "Real-money execution is blocked."
                    : "LIVE — real money execution enabled."}
                </div>
              </div>
              <button
                onClick={() => s.setPaperTradingMode(!s.paperTradingMode)}
                className={`relative h-7 w-12 rounded-full transition-colors ${
                  s.paperTradingMode ? "bg-signal-warn/60" : "bg-signal-loss/60"
                }`}
              >
                <span
                  className={`absolute top-1 h-5 w-5 rounded-full bg-zinc-100 transition-all ${
                    s.paperTradingMode ? "left-1" : "left-6"
                  }`}
                />
              </button>
            </div>

            <label className="flex flex-col gap-1">
              <span className={labelText}>Active Bankroll ($)</span>
              <input
                type="number"
                value={s.activeBankroll}
                onChange={(e) => s.setActiveBankroll(Number(e.target.value))}
                className="rounded border border-surface-border bg-surface px-3 py-2 text-zinc-200"
              />
            </label>

            <label className="flex flex-col gap-1">
              <span className={labelText}>
                Edge Threshold — {(s.edgeThreshold * 100).toFixed(1)}%
              </span>
              <input
                type="range"
                min={1}
                max={10}
                step={0.5}
                value={s.edgeThreshold * 100}
                onChange={(e) => s.setEdgeThreshold(Number(e.target.value) / 100)}
              />
            </label>

            <label className="flex flex-col gap-1">
              <span className={labelText}>
                Kelly Fraction — {s.kellyFraction.toFixed(2)}{" "}
                {s.kellyFraction === 0.25
                  ? "(Quarter)"
                  : s.kellyFraction === 0.5
                    ? "(Half)"
                    : s.kellyFraction === 1
                      ? "(Full)"
                      : ""}
              </span>
              <input
                type="range"
                min={0.1}
                max={1}
                step={0.05}
                value={s.kellyFraction}
                onChange={(e) => s.setKellyFraction(Number(e.target.value))}
              />
            </label>
          </div>
        </Card>

        {/* Section 3 — System */}
        <Card title="System" className="lg:col-span-2">
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <StatCard label="Trades" value={stats.data?.total_trades ?? "—"} />
              <StatCard label="Events" value={stats.data?.total_events ?? "—"} />
              <StatCard label="Snapshots" value={stats.data?.total_snapshots ?? "—"} />
              <StatCard label="Odds Lines" value={stats.data?.total_odds_lines ?? "—"} />
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant="primary" onClick={poll} disabled={busy !== null}>
                {busy === "poll" ? "Polling…" : "Poll Odds Now"}
              </Button>
              <Button variant="secondary" onClick={seed} disabled={busy !== null}>
                {busy === "seed" ? "Seeding…" : "Seed Demo Data"}
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
