import type { ReactNode } from "react";

export function StatCard({
  label,
  value,
  delta,
  deltaTone,
  hint,
}: {
  label: string;
  value: ReactNode;
  delta?: string;
  deltaTone?: "profit" | "loss" | "neutral";
  hint?: string;
}) {
  const deltaClass =
    deltaTone === "profit"
      ? "text-signal-profit"
      : deltaTone === "loss"
        ? "text-signal-loss"
        : "text-signal-neutral";
  return (
    <div className="rounded-lg border border-surface-border bg-surface-card p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-zinc-500">
        {label}
      </div>
      <div className="mt-1 text-2xl font-semibold tabular-nums text-zinc-100">
        {value}
      </div>
      {(delta || hint) && (
        <div className="mt-1 flex items-center gap-2 text-xs">
          {delta && <span className={`tabular-nums ${deltaClass}`}>{delta}</span>}
          {hint && <span className="text-zinc-500">{hint}</span>}
        </div>
      )}
    </div>
  );
}
