import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { PortfolioHistoryPoint } from "../../api/types";
import Panel from "../common/Panel";

export default function PnLChart({ history }: { history: PortfolioHistoryPoint[] }) {
  if (!history.length) {
    return (
      <Panel title="Local P&L trend" eyebrow="Portfolio">
        <div className="rounded-2xl bg-slate px-4 py-5 text-sm text-ink/65">
          Portfolio history will appear here after FinPilot records paper or broker-backed fills.
        </div>
      </Panel>
    );
  }
  return (
    <Panel title="Local P&L trend" eyebrow="Portfolio">
      <div className="h-60">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={history}>
            <XAxis dataKey="timestamp" hide />
            <YAxis hide />
            <Tooltip />
            <Area type="monotone" dataKey="equity" stroke="#2f6f6d" fill="rgba(47,111,109,0.18)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  );
}
