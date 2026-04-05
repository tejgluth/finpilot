import { create } from "zustand";
import { api } from "../api/client";
import type { PermissionsPayload, TradingStatusPayload } from "../api/types";

interface PermissionsStore {
  permissions: PermissionsPayload | null;
  tradingStatus: TradingStatusPayload | null;
  loading: boolean;
  error: string | null;
  fetchAll: () => Promise<void>;
  updateLevel: (level: string) => Promise<void>;
}

export const usePermissionsStore = create<PermissionsStore>((set, get) => ({
  permissions: null,
  tradingStatus: null,
  loading: false,
  error: null,
  fetchAll: async () => {
    set({ loading: true, error: null });
    try {
      const [permissions, tradingStatus] = await Promise.all([api.getPermissions(), api.getTradingStatus()]);
      set({ permissions, tradingStatus, loading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Unable to load trading state.",
        loading: false,
      });
    }
  },
  updateLevel: async (level) => {
    set({ loading: true, error: null });
    try {
      await api.updatePermissions(level);
      await get().fetchAll();
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Unable to update permission level.",
        loading: false,
      });
    }
  },
}));
