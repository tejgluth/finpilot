export type AgentCategory = "quantitative" | "qualitative" | "macro" | "risk" | "execution";

export interface AgentMeta {
  label: string;
  description: string;
  category: AgentCategory;
  role: "analysis" | "decision";
  defaultSources: string[];
}

export const AGENT_META: Record<string, AgentMeta> = {
  fundamentals: {
    label: "Fundamentals",
    description:
      "Evaluates earnings quality, balance sheet health, and cash flow sustainability from filings and earnings data.",
    category: "quantitative",
    role: "analysis",
    defaultSources: ["EDGAR", "FMP"],
  },
  technicals: {
    label: "Technicals",
    description:
      "Interprets price action, momentum indicators, and chart structure including RSI, MACD, and moving averages.",
    category: "quantitative",
    role: "analysis",
    defaultSources: ["yfinance"],
  },
  sentiment: {
    label: "Sentiment",
    description:
      "Aggregates news tone, social media signals, and options positioning to gauge short-term market mood.",
    category: "qualitative",
    role: "analysis",
    defaultSources: ["MarketAux", "Reddit", "Finnhub"],
  },
  macro: {
    label: "Macro",
    description:
      "Incorporates interest rates, inflation, GDP growth, and yield curve signals to assess the broader economic regime.",
    category: "macro",
    role: "analysis",
    defaultSources: ["FRED"],
  },
  value: {
    label: "Value",
    description:
      "Scores stocks against intrinsic value using P/E, P/B, free cash flow yield, and historical valuation multiples.",
    category: "quantitative",
    role: "analysis",
    defaultSources: ["FMP", "EDGAR"],
  },
  momentum: {
    label: "Momentum",
    description:
      "Tracks relative price strength, 3–12 month return rankings, and cross-asset momentum signals.",
    category: "quantitative",
    role: "analysis",
    defaultSources: ["yfinance"],
  },
  growth: {
    label: "Growth",
    description:
      "Identifies companies with accelerating revenue and earnings trajectories by analyzing quarterly growth trends.",
    category: "quantitative",
    role: "analysis",
    defaultSources: ["EDGAR", "FMP"],
  },
  risk_manager: {
    label: "Risk Manager",
    description:
      "Enforces position limits, drawdown guardrails, and volatility constraints before any signal reaches execution.",
    category: "risk",
    role: "decision",
    defaultSources: [],
  },
  portfolio_manager: {
    label: "Portfolio Manager",
    description:
      "Synthesizes all agent signals into final BUY/SELL/HOLD decisions and rebalancing allocations.",
    category: "execution",
    role: "decision",
    defaultSources: [],
  },
};

export const ANALYSIS_AGENT_IDS = [
  "fundamentals",
  "technicals",
  "sentiment",
  "macro",
  "value",
  "momentum",
  "growth",
] as const;

export const DECISION_AGENT_IDS = ["risk_manager", "portfolio_manager"] as const;

export function agentLabel(id: string): string {
  return (
    AGENT_META[id]?.label ??
    id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
  );
}
