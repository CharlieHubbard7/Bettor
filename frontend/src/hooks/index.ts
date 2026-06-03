// One hook per data domain. Each wraps `api.*` via the generic useApi hook.
import { api } from "@/api/client";
import { useApi } from "./useApi";

type Params = Record<string, string | number | boolean | undefined | null>;

/** Opportunities auto-refresh every 60s. */
export function useOpportunities(params?: Params) {
  const key = JSON.stringify(params ?? {});
  return useApi(() => api.opportunities.list(params), [key], 60_000);
}

export function useTrades(params?: Params) {
  const key = JSON.stringify(params ?? {});
  return useApi(() => api.trades.list(params), [key]);
}

export function usePnl() {
  return useApi(() => api.analytics.pnl(), []);
}

export function useCLV() {
  return useApi(() => api.analytics.clv(), []);
}

export function useEdgeAnalytics() {
  return useApi(() => api.analytics.edge(), []);
}

export function useBankroll() {
  return useApi(() => api.analytics.bankroll(), []);
}

export function useCredits() {
  return useApi(() => api.system.credits(), []);
}

export function useSports() {
  return useApi(() => api.sports.list(), []);
}

export function useEvents(params?: Params) {
  const key = JSON.stringify(params ?? {});
  return useApi(() => api.events.list(params), [key]);
}

export function useSystemStats() {
  return useApi(() => api.system.stats(), []);
}

export { useApi } from "./useApi";
export { useSettingsStore } from "@/store/settingsStore";
