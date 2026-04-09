import { create } from "zustand";
import { api } from "../api/client";
import type { BacktestLiveTeamUpdate, BacktestResult } from "../api/types";

interface BacktestStore {
  result: BacktestResult | null;
  loading: boolean;
  progress: number;
  stage: string | null;
  liveTeams: BacktestLiveTeamUpdate[];
  error: string | null;
  runBacktest: (payload: Record<string, unknown>) => Promise<void>;
}

function upsertLiveTeam(
  current: BacktestLiveTeamUpdate[],
  next: BacktestLiveTeamUpdate,
): BacktestLiveTeamUpdate[] {
  const key = `${next.team_id}:${next.version_number}`;
  const existingIndex = current.findIndex((item) => `${item.team_id}:${item.version_number}` === key);
  if (existingIndex === -1) {
    return [...current, next];
  }
  const copy = current.slice();
  copy[existingIndex] = next;
  return copy;
}

export const useBacktestStore = create<BacktestStore>((set) => ({
  result: null,
  loading: false,
  progress: 0,
  stage: null,
  liveTeams: [],
  error: null,
  runBacktest: async (payload) => {
    set({ loading: true, progress: 0, stage: "starting", liveTeams: [], error: null, result: null });
    try {
      await api.streamBacktest(payload, {
        onProgress: (event) => {
          set((state) => ({
            progress: Number(event.progress ?? 0),
            stage: String(event.stage ?? state.stage ?? "running"),
            liveTeams: event.team_live
              ? upsertLiveTeam(state.liveTeams, event.team_live as BacktestLiveTeamUpdate)
              : state.liveTeams,
          }));
        },
        onComplete: (result) => {
          set({ result, loading: false, progress: 100, stage: "complete", liveTeams: [], error: null });
        },
        onError: (message) => {
          set({ loading: false, progress: 0, stage: "error", liveTeams: [], error: message });
        },
      });
    } catch (error) {
      set({
        loading: false,
        progress: 0,
        stage: "error",
        liveTeams: [],
        error: error instanceof Error ? error.message : "Backtest failed.",
      });
    }
  },
}));
