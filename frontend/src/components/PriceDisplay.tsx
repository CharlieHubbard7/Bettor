import { formatAmerican } from "@/lib/format";

/** American odds, colored: positive (underdog) emerald, negative (favorite) red. */
export function PriceDisplay({
  american,
  className = "",
}: {
  american: number;
  className?: string;
}) {
  const tone = american > 0 ? "text-signal-profit" : "text-signal-loss";
  return (
    <span className={`font-mono tabular-nums ${tone} ${className}`}>
      {formatAmerican(american)}
    </span>
  );
}
