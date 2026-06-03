// Global app settings, persisted to localStorage via Zustand.
import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface SettingsState {
  paperTradingMode: boolean;
  activeBankroll: number;
  edgeThreshold: number; // fraction, 0.02 default
  kellyFraction: number; // 0.25 default
  pollIntervalMinutes: number;
  activeSports: string[];
  oddsApiKey: string; // stored locally for display only; the real key lives in backend .env
  setPaperTradingMode: (v: boolean) => void;
  setActiveBankroll: (v: number) => void;
  setEdgeThreshold: (v: number) => void;
  setKellyFraction: (v: number) => void;
  setPollIntervalMinutes: (v: number) => void;
  setActiveSports: (v: string[]) => void;
  toggleSport: (sportKey: string) => void;
  setOddsApiKey: (v: string) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      paperTradingMode: true,
      activeBankroll: 1000,
      edgeThreshold: 0.02,
      kellyFraction: 0.25,
      pollIntervalMinutes: 5,
      activeSports: ["americanfootball_nfl", "basketball_nba", "baseball_mlb"],
      oddsApiKey: "",
      setPaperTradingMode: (v) => set({ paperTradingMode: v }),
      setActiveBankroll: (v) => set({ activeBankroll: v }),
      setEdgeThreshold: (v) => set({ edgeThreshold: v }),
      setKellyFraction: (v) => set({ kellyFraction: v }),
      setPollIntervalMinutes: (v) => set({ pollIntervalMinutes: v }),
      setActiveSports: (v) => set({ activeSports: v }),
      toggleSport: (sportKey) =>
        set((state) => ({
          activeSports: state.activeSports.includes(sportKey)
            ? state.activeSports.filter((s) => s !== sportKey)
            : [...state.activeSports, sportKey],
        })),
      setOddsApiKey: (v) => set({ oddsApiKey: v }),
    }),
    { name: "bettor-settings" }
  )
);
