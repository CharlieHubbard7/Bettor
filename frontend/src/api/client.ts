// All HTTP calls to the backend live here. Pages and hooks never call fetch directly.
import type {
  ApiUsageSummary,
  BankrollSnapshot,
  BettorEvent,
  CLVStats,
  EdgeAnalytics,
  EdgeOpportunity,
  EventOdds,
  PnLSummary,
  PollResult,
  SeedResult,
  Sport,
  SystemStats,
  Trade,
  TradeCreate,
  TradeUpdate,
} from "@/types";

const BASE_URL = "/api";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type Params = Record<string, string | number | boolean | undefined | null>;

function buildQuery(params?: Params): string {
  if (!params) return "";
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      search.append(key, String(value));
    }
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // non-JSON error body — keep statusText
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

async function get<T>(path: string, params?: Params): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}${buildQuery(params)}`);
  return handle<T>(res);
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handle<T>(res);
}

async function put<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handle<T>(res);
}

export const api = {
  sports: {
    list: (params?: Params) => get<Sport[]>("/sports", params),
  },
  events: {
    list: (params?: Params) => get<BettorEvent[]>("/events", params),
  },
  opportunities: {
    list: (params?: Params) => get<EdgeOpportunity[]>("/opportunities", params),
  },
  odds: {
    byEvent: (id: string) => get<EventOdds>(`/odds/${id}`),
  },
  trades: {
    list: (params?: Params) => get<Trade[]>("/trades", params),
    create: (body: TradeCreate) => post<Trade>("/trades", body),
    update: (id: string, body: TradeUpdate) => put<Trade>(`/trades/${id}`, body),
  },
  analytics: {
    clv: () => get<CLVStats>("/analytics/clv"),
    pnl: () => get<PnLSummary>("/analytics/pnl"),
    edge: () => get<EdgeAnalytics>("/analytics/edge"),
    bankroll: () => get<BankrollSnapshot[]>("/analytics/bankroll"),
  },
  system: {
    credits: () => get<ApiUsageSummary>("/system/credits"),
    poll: () => post<PollResult>("/system/poll", {}),
    stats: () => get<SystemStats>("/system/stats"),
    seed: () => post<SeedResult>("/system/seed", {}),
  },
};
