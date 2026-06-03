import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useEvents } from "@/hooks";
import { useSettingsStore } from "@/store/settingsStore";
import { api, ApiError } from "@/api/client";
import { Button, Card, useToastStore } from "@/components/ui";
import { PageHeader } from "@/components/feedback";
import { StatCard } from "@/components/StatCard";
import {
  americanToDecimal,
  fullKelly,
  formatBook,
  formatMarket,
  impliedProbability,
} from "@/lib/format";
import type { TradeCreate } from "@/types";

const MARKETS = ["h2h", "spreads", "totals", "player_points", "player_rebounds", "player_assists"];
const BOOKS = ["draftkings", "fanduel", "betmgm", "caesars", "pinnacle", "bookmaker"];

const labelClass = "flex flex-col gap-1 text-sm";
const labelText = "text-xs uppercase tracking-wide text-zinc-500";
const inputClass =
  "rounded border border-surface-border bg-surface px-3 py-2 text-zinc-200 focus:border-signal-neutral focus:outline-none";

export function TradeLogger() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const events = useEvents();
  const pushToast = useToastStore((s) => s.push);
  const { paperTradingMode, activeBankroll, kellyFraction } = useSettingsStore();

  const [eventId, setEventId] = useState(params.get("event_id") ?? "");
  const [eventSearch, setEventSearch] = useState("");
  const [marketKey, setMarketKey] = useState(params.get("market_key") ?? "h2h");
  const [outcomeName, setOutcomeName] = useState(params.get("outcome_name") ?? "");
  const [playerName, setPlayerName] = useState(params.get("player_name") ?? "");
  const [entryPrice, setEntryPrice] = useState(
    params.get("entry_price_american") ?? "-110"
  );
  const [ourProb, setOurProb] = useState(params.get("our_prob") ?? "");
  const [bookmaker, setBookmaker] = useState(params.get("bookmaker") ?? "draftkings");
  const [stakeDollars, setStakeDollars] = useState("");
  const [isReal, setIsReal] = useState(!paperTradingMode);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const isProp = marketKey.startsWith("player_");
  const american = Number(entryPrice);
  const decimal = Number.isFinite(american) && american !== 0 ? americanToDecimal(american) : 0;

  // Default our_prob to the entry price's implied probability if the user hasn't set one.
  useEffect(() => {
    if (!params.get("our_prob") && decimal > 1 && ourProb === "") {
      setOurProb(impliedProbability(decimal).toFixed(4));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [decimal]);

  const prob = Number(ourProb);
  const kelly = useMemo(() => {
    if (!(decimal > 1) || !(prob > 0 && prob < 1)) {
      return { full: 0, quarter: 0, units: 0, dollars: 0 };
    }
    const full = fullKelly(prob, decimal);
    const quarter = full * kellyFraction;
    return {
      full,
      quarter,
      units: quarter,
      dollars: quarter * activeBankroll,
    };
  }, [decimal, prob, kellyFraction, activeBankroll]);

  const filteredEvents = (events.data ?? []).filter((e) => {
    const q = eventSearch.toLowerCase();
    return (
      !q ||
      e.home_team.toLowerCase().includes(q) ||
      e.away_team.toLowerCase().includes(q)
    );
  });

  const canSubmit =
    eventId &&
    outcomeName &&
    Number.isFinite(american) &&
    american !== 0 &&
    prob > 0 &&
    prob < 1 &&
    !submitting;

  const submit = async () => {
    setSubmitting(true);
    const body: TradeCreate = {
      event_id: eventId,
      market_key: marketKey,
      outcome_name: outcomeName,
      player_name: isProp ? playerName || null : null,
      entry_price_american: american,
      our_prob: prob,
      sharp_consensus_prob: Number(params.get("sharp_consensus_prob") ?? prob),
      bookmaker,
      stake_dollars: stakeDollars ? Number(stakeDollars) : null,
      trade_type: isReal ? "real" : "paper",
      notes: notes || null,
    };
    try {
      await api.trades.create(body);
      pushToast("Trade logged");
      navigate("/trades");
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Failed to log trade";
      pushToast(msg, "error");
      setSubmitting(false);
    }
  };

  return (
    <div>
      <PageHeader title="Log Trade" subtitle="Record a paper or real bet" />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <label className={`${labelClass} sm:col-span-2`}>
                <span className={labelText}>Event</span>
                <input
                  className={inputClass}
                  placeholder="Search teams…"
                  value={eventSearch}
                  onChange={(e) => setEventSearch(e.target.value)}
                />
                <select
                  className={inputClass}
                  value={eventId}
                  onChange={(e) => setEventId(e.target.value)}
                >
                  <option value="">Select an event…</option>
                  {filteredEvents.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.away_team} @ {e.home_team}
                    </option>
                  ))}
                </select>
              </label>

              <label className={labelClass}>
                <span className={labelText}>Market</span>
                <select
                  className={inputClass}
                  value={marketKey}
                  onChange={(e) => setMarketKey(e.target.value)}
                >
                  {MARKETS.map((m) => (
                    <option key={m} value={m}>
                      {formatMarket(m)}
                    </option>
                  ))}
                </select>
              </label>

              <label className={labelClass}>
                <span className={labelText}>Bookmaker</span>
                <select
                  className={inputClass}
                  value={bookmaker}
                  onChange={(e) => setBookmaker(e.target.value)}
                >
                  {BOOKS.map((b) => (
                    <option key={b} value={b}>
                      {formatBook(b)}
                    </option>
                  ))}
                </select>
              </label>

              {isProp && (
                <label className={labelClass}>
                  <span className={labelText}>Player</span>
                  <input
                    className={inputClass}
                    value={playerName}
                    onChange={(e) => setPlayerName(e.target.value)}
                    placeholder="Player name"
                  />
                </label>
              )}

              <label className={labelClass}>
                <span className={labelText}>Outcome</span>
                <input
                  className={inputClass}
                  value={outcomeName}
                  onChange={(e) => setOutcomeName(e.target.value)}
                  placeholder="Team / Over 24.5 / etc."
                />
              </label>

              <label className={labelClass}>
                <span className={labelText}>Entry Price (American)</span>
                <input
                  className={inputClass}
                  value={entryPrice}
                  onChange={(e) => setEntryPrice(e.target.value)}
                  placeholder="-110"
                />
              </label>

              <label className={labelClass}>
                <span className={labelText}>Our Probability (0–1)</span>
                <input
                  className={inputClass}
                  value={ourProb}
                  onChange={(e) => setOurProb(e.target.value)}
                  placeholder="0.55"
                />
              </label>

              <label className={labelClass}>
                <span className={labelText}>Stake $ (optional)</span>
                <input
                  className={inputClass}
                  value={stakeDollars}
                  onChange={(e) => setStakeDollars(e.target.value)}
                  placeholder={kelly.dollars ? kelly.dollars.toFixed(2) : "auto"}
                />
              </label>

              <label className={`${labelClass} sm:col-span-2`}>
                <span className={labelText}>Notes</span>
                <textarea
                  className={inputClass}
                  rows={2}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                />
              </label>

              <label className="flex items-center gap-3 sm:col-span-2">
                <input
                  type="checkbox"
                  checked={isReal}
                  onChange={(e) => setIsReal(e.target.checked)}
                />
                <span className="text-sm text-zinc-300">
                  Real-money trade
                  {paperTradingMode && (
                    <span className="ml-2 text-xs text-signal-warn">
                      (paper mode is on — backend will reject real trades)
                    </span>
                  )}
                </span>
              </label>
            </div>

            <div className="mt-4 flex gap-2">
              <Button variant="primary" onClick={submit} disabled={!canSubmit}>
                {submitting ? "Logging…" : "Log Trade"}
              </Button>
              <Button variant="ghost" onClick={() => navigate("/opportunities")}>
                Cancel
              </Button>
            </div>
          </Card>
        </div>

        <div className="flex flex-col gap-4">
          <Card title="Kelly Suggestion" subtitle="Live from price + our probability">
            <div className="grid grid-cols-1 gap-3">
              <StatCard label="Full Kelly" value={`${(kelly.full * 100).toFixed(1)}%`} />
              <StatCard
                label="Quarter Kelly (recommended)"
                value={`${(kelly.quarter * 100).toFixed(1)}%`}
              />
              <StatCard
                label="Suggested Stake"
                value={`${kelly.units.toFixed(3)}u`}
                hint={`≈ $${kelly.dollars.toFixed(2)} @ $${activeBankroll} bankroll`}
              />
            </div>
            {decimal > 1 && prob > 0 && prob < 1 && (
              <p className="mt-3 text-xs text-zinc-500">
                Edge vs this price:{" "}
                <span
                  className={
                    prob - impliedProbability(decimal) > 0
                      ? "text-signal-profit"
                      : "text-signal-loss"
                  }
                >
                  {((prob - impliedProbability(decimal)) * 100).toFixed(2)}%
                </span>
              </p>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
