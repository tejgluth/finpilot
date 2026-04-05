import { useEffect } from "react";
import AgentPerformance from "../components/portfolio/AgentPerformance";
import PnLChart from "../components/portfolio/PnLChart";
import PortfolioDashboard from "../components/portfolio/PortfolioDashboard";
import { usePortfolioStore } from "../stores/portfolioStore";

export default function PortfolioPage() {
  const { portfolio, fetchPortfolio } = usePortfolioStore();

  useEffect(() => {
    void fetchPortfolio();
  }, [fetchPortfolio]);

  if (!portfolio) {
    return <div className="rounded-[28px] bg-white/80 p-6 shadow-soft">Loading portfolio…</div>;
  }

  return (
    <div className="space-y-6">
      <PortfolioDashboard portfolio={portfolio} />
      <div className="grid gap-6 lg:grid-cols-2">
        <PnLChart history={portfolio.history} />
        <AgentPerformance items={portfolio.agent_performance} />
      </div>
    </div>
  );
}
