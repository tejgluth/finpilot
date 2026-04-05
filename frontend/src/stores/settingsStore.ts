import { create } from "zustand";
import { api } from "../api/client";
import type { UserSettings } from "../api/types";

interface SettingsStore {
  settings: UserSettings | null;
  loading: boolean;
  error: string | null;
  fetchSettings: () => Promise<void>;
  patchSettings: (patch: Record<string, unknown>) => Promise<void>;
}

export const useSettingsStore = create<SettingsStore>((set) => ({
  settings: null,
  loading: false,
  error: null,
  fetchSettings: async () => {
    set({ loading: true, error: null });
    try {
      const settings = await api.getSettings();
      set({ settings, loading: false });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : "Unable to load settings", loading: false });
    }
  },
  patchSettings: async (patch) => {
    set({ loading: true, error: null });
    try {
      const settings = await api.patchSettings(patch);
      set({ settings, loading: false });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to save settings";
      set({ error: message, loading: false });
      throw error instanceof Error ? error : new Error(message);
    }
  },
}));
