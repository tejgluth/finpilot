import { create } from "zustand";
import { api } from "../api/client";
import type { PortfolioPayload } from "../api/types";

interface PortfolioStore {
  portfolio: PortfolioPayload | null;
  loading: boolean;
  fetchPortfolio: () => Promise<void>;
}

export const usePortfolioStore = create<PortfolioStore>((set) => ({
  portfolio: null,
  loading: false,
  fetchPortfolio: async () => {
    set({ loading: true });
    const portfolio = await api.getPortfolio();
    set({ portfolio, loading: false });
  },
}));
