import { Fragment, type ReactNode, useMemo, useState } from "react";

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => ReactNode;
  /** Value used for sorting; if omitted the column is not sortable. */
  sortValue?: (row: T) => number | string;
  align?: "left" | "right" | "center";
  headerClassName?: string;
  cellClassName?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  initialSort?: { key: string; dir: "asc" | "desc" };
  /** If provided, clicking a row toggles inline expansion rendering this content. */
  expandable?: (row: T) => ReactNode;
  /** If provided, clicking a row calls this instead of expanding. */
  onRowClick?: (row: T) => void;
  emptyLabel?: string;
}

const alignClass = (align?: "left" | "right" | "center") =>
  align === "right"
    ? "text-right"
    : align === "center"
      ? "text-center"
      : "text-left";

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  initialSort,
  expandable,
  onRowClick,
  emptyLabel = "No data",
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(initialSort?.key ?? null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">(
    initialSort?.dir ?? "desc"
  );
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const sorted = useMemo(() => {
    if (!sortKey) return rows;
    const col = columns.find((c) => c.key === sortKey);
    if (!col?.sortValue) return rows;
    const factor = sortDir === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => {
      const av = col.sortValue!(a);
      const bv = col.sortValue!(b);
      if (av < bv) return -1 * factor;
      if (av > bv) return 1 * factor;
      return 0;
    });
  }, [rows, columns, sortKey, sortDir]);

  const toggleSort = (col: Column<T>) => {
    if (!col.sortValue) return;
    if (sortKey === col.key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(col.key);
      setSortDir("desc");
    }
  };

  const handleRowClick = (row: T) => {
    if (onRowClick) {
      onRowClick(row);
      return;
    }
    if (expandable) {
      const key = rowKey(row);
      setExpanded((prev) => {
        const next = new Set(prev);
        next.has(key) ? next.delete(key) : next.add(key);
        return next;
      });
    }
  };

  const clickable = Boolean(onRowClick || expandable);

  if (rows.length === 0) {
    return (
      <div className="rounded-lg border border-surface-border bg-surface-card py-10 text-center text-sm text-zinc-500">
        {emptyLabel}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-surface-border">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="bg-surface-card text-xs uppercase tracking-wide text-zinc-500">
            {columns.map((col) => (
              <th
                key={col.key}
                onClick={() => toggleSort(col)}
                className={`px-3 py-2 font-medium ${alignClass(col.align)} ${
                  col.sortValue ? "cursor-pointer select-none hover:text-zinc-300" : ""
                } ${col.headerClassName ?? ""}`}
              >
                {col.header}
                {sortKey === col.key && (
                  <span className="ml-1">{sortDir === "asc" ? "▲" : "▼"}</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row) => {
            const key = rowKey(row);
            const isExpanded = expanded.has(key);
            return (
              <Fragment key={key}>
                <tr
                  onClick={() => handleRowClick(row)}
                  className={`border-t border-surface-border ${
                    clickable ? "cursor-pointer hover:bg-surface-card/60" : ""
                  }`}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={`px-3 py-2 tabular-nums ${alignClass(col.align)} ${
                        col.cellClassName ?? ""
                      }`}
                    >
                      {col.render ? col.render(row) : String((row as Record<string, unknown>)[col.key] ?? "")}
                    </td>
                  ))}
                </tr>
                {expandable && isExpanded && (
                  <tr className="border-t border-surface-border bg-surface-card/40">
                    <td colSpan={columns.length} className="px-4 py-3">
                      {expandable(row)}
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
