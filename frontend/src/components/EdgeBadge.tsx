import { Badge } from "./Badge";
import { formatPct } from "@/lib/format";

/** Edge% pill: emerald above 5%, amber 2–5%, neutral below 2%. */
export function EdgeBadge({ edge }: { edge: number }) {
  const tone = edge > 0.05 ? "profit" : edge >= 0.02 ? "warn" : "neutral";
  return <Badge tone={tone}>{formatPct(edge)}</Badge>;
}
