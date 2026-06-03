import type { ReactNode } from "react";

type BadgeTone =
  | "profit"
  | "loss"
  | "warn"
  | "neutral"
  | "info"
  | "zinc";

const TONE_CLASSES: Record<BadgeTone, string> = {
  profit: "bg-signal-profit/15 text-signal-profit ring-signal-profit/30",
  loss: "bg-signal-loss/15 text-signal-loss ring-signal-loss/30",
  warn: "bg-signal-warn/15 text-signal-warn ring-signal-warn/30",
  neutral: "bg-signal-neutral/15 text-signal-neutral ring-signal-neutral/30",
  info: "bg-blue-400/15 text-blue-300 ring-blue-400/30",
  zinc: "bg-zinc-700/40 text-zinc-300 ring-zinc-600/40",
};

export function Badge({
  children,
  tone = "zinc",
  className = "",
}: {
  children: ReactNode;
  tone?: BadgeTone;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium uppercase tracking-wide ring-1 ring-inset ${TONE_CLASSES[tone]} ${className}`}
    >
      {children}
    </span>
  );
}

export type { BadgeTone };
