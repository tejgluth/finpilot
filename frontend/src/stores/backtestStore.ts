import { create } from "zustand";
import { api } from "../api/client";
import type { BacktestResult } from "../api/types";

interface BacktestStore {
  result: BacktestResult | null;
  loading: boolean;
  progress: number;
  error: string | null;
  runBacktest: (payload: Record<string, unknown>) => Promise<void>;
}

export const useBacktestStore = create<BacktestStore>((set) => ({
  result: null,
  loading: false,
  progress: 0,
  error: null,
  runBacktest: async (payload) => {
    set({ loading: true, progress: 0, error: null, result: null });
    try {
      await api.streamBacktest(payload, {
        onProgress: (event) => {
          set({
            progress: Number(event.progress ?? 0),
          });
        },
        onComplete: (result) => {
          set({ result, loading: false, progress: 100, error: null });
        },
        onError: (message) => {
          set({ loading: false, progress: 0, error: message });
        },
      });
    } catch (error) {
      set({
        loading: false,
        progress: 0,
        error: error instanceof Error ? error.message : "Backtest failed.",
      });
    }
  },
}));
