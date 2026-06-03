import { NavLink, Outlet } from "react-router-dom";
import { useSettingsStore } from "@/store/settingsStore";
import { Badge } from "./Badge";
import { Toaster } from "./ui";

const NAV = [
  { to: "/", label: "Dashboard", end: true, icon: "▦" },
  { to: "/opportunities", label: "Opportunities", icon: "◎" },
  { to: "/trades/new", label: "Trade Logger", icon: "✎" },
  { to: "/trades", label: "Trade Journal", end: true, icon: "▤" },
  { to: "/analytics", label: "Analytics", icon: "📈" },
  { to: "/settings", label: "Settings", icon: "⚙" },
];

function navClass({ isActive }: { isActive: boolean }): string {
  return `flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
    isActive
      ? "bg-surface-card text-zinc-100"
      : "text-zinc-400 hover:bg-surface-card/60 hover:text-zinc-200"
  }`;
}

export function Layout() {
  const paperMode = useSettingsStore((s) => s.paperTradingMode);

  return (
    <div className="flex min-h-screen bg-surface text-zinc-200">
      {/* Sidebar (desktop) */}
      <aside className="hidden w-56 shrink-0 flex-col border-r border-surface-border bg-surface px-3 py-4 md:flex">
        <div className="px-3 pb-4">
          <div className="text-lg font-bold tracking-tight text-zinc-100">
            Bettor
          </div>
          <div className="text-xs text-zinc-600">edge-finding terminal</div>
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={navClass}>
              <span className="w-4 text-center text-zinc-500">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-2 pt-4">
          {paperMode ? (
            <Badge tone="warn" className="w-full justify-center py-1">
              ● Paper Trading
            </Badge>
          ) : (
            <Badge tone="loss" className="w-full justify-center py-1">
              ● LIVE — Real Money
            </Badge>
          )}
        </div>
      </aside>

      {/* Main */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Mobile top bar */}
        <header className="flex items-center justify-between border-b border-surface-border px-4 py-3 md:hidden">
          <span className="font-bold text-zinc-100">Bettor</span>
          {paperMode && <Badge tone="warn">Paper</Badge>}
        </header>

        <main className="flex-1 px-4 py-6 md:px-8">
          <Outlet />
        </main>

        {/* Mobile bottom nav */}
        <nav className="sticky bottom-0 flex items-center justify-around border-t border-surface-border bg-surface px-2 py-2 md:hidden">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className="flex flex-col items-center gap-0.5 px-2 text-[10px] text-zinc-500 aria-[current=page]:text-zinc-100"
            >
              <span>{item.icon}</span>
              {item.label.split(" ")[0]}
            </NavLink>
          ))}
        </nav>
      </div>

      <Toaster />
    </div>
  );
}
