import { create } from "zustand";
import { api } from "../api/client";
import type {
  AlpacaPlanResponse,
  SaveSetupSecretsResponse,
  SecretKeyStatus,
  SetupGuidesResponse,
  SetupStatus,
} from "../api/types";

interface SetupStore {
  status: SetupStatus | null;
  plan: AlpacaPlanResponse | null;
  keys: SecretKeyStatus[];
  guides: SetupGuidesResponse | null;
  loading: boolean;
  saving: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  saveSecrets: (payload: {
    ai_provider: "openai" | "anthropic" | "google" | "ollama";
    alpaca_mode: "paper" | "live";
    values: Record<string, string>;
  }) => Promise<SaveSetupSecretsResponse>;
}

export const useSetupStore = create<SetupStore>((set) => ({
  status: null,
  plan: null,
  keys: [],
  guides: null,
  loading: false,
  saving: false,
  error: null,
  refresh: async () => {
    set({ loading: true, error: null });
    try {
      const [status, plan, keys, guides] = await Promise.all([
        api.getSetupStatus(),
        api.getPlan(),
        api.validateKeys(),
        api.getSetupGuides(),
      ]);
      set({ status, plan, keys: keys.keys, guides, loading: false });
    } catch (error) {
      set({ loading: false, error: error instanceof Error ? error.message : "Unable to load setup." });
      throw error;
    }
  },
  saveSecrets: async (payload) => {
    set({ saving: true, error: null });
    try {
      const response = await api.saveSetupSecrets(payload);
      const plan = await api.getPlan();
      set({
        status: response.status,
        keys: response.keys,
        plan,
        saving: false,
      });
      return response;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to save setup details.";
      set({ saving: false, error: message });
      throw error;
    }
  },
}));
