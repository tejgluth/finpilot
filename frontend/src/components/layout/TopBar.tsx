import { useLocation } from "react-router-dom";
import StatusBadge from "../common/StatusBadge";

const PAGE_META: Record<
  string,
  { title: string; subtitle: string }
> = {
  "/": {
    title: "Setup",
    subtitle: "Configure your AI provider, data sources, and local credentials",
  },
  "/strategy": {
    title: "Strategy",
    subtitle: "Build, compare, and manage agent teams for analysis",
  },
  "/backtest": {
    title: "Backtest",
    subtitle: "Test team performance against historical data and a benchmark",
  },
  "/portfolio": {
    title: "Portfolio",
    subtitle: "Monitor positions, P&L, and per-agent contribution",
  },
  "/trading": {
    title: "Trading",
    subtitle: "Review orders and manage live or paper execution",
  },
  "/audit": {
    title: "Audit log",
    subtitle: "Append-only local record of every agent decision",
  },
  "/settings": {
    title: "Settings",
    subtitle: "LLM, data, agent weights, backtesting, and system options",
  },
};

export default function TopBar() {
  const { pathname } = useLocation();
  const meta = PAGE_META[pathname] ?? {
    title: "FinPilot",
    subtitle: "Local-first investing lab",
  };

  return (
    <header className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
      <div>
        <h1 className="font-display text-3xl leading-none text-ink">{meta.title}</h1>
        <p className="mt-1.5 text-sm text-ink/55">{meta.subtitle}</p>
      </div>
      <div className="flex flex-col items-start gap-2 lg:items-end">
        <StatusBadge label="Paper default" tone="good" />
      </div>
    </header>
  );
}
