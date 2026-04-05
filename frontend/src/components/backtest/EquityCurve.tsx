import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { TeamBacktestRun } from "../../api/types";
import Panel from "../common/Panel";

const TEAM_COLORS = ["#2f6f6d", "#ca5f3f", "#5570d6", "#8d6cab"];

export default function EquityCurve({
  teamRuns,
}: {
  teamRuns: TeamBacktestRun[];
}) {
  const points = teamRuns[0]?.equity_curve ?? [];
  if (!points.length) {
    return (
      <Panel title="Equity vs SPY" eyebrow="Always visible benchmark">
        <div className="rounded-2xl bg-slate px-4 py-5 text-sm text-ink/65">
          No equity curve is available for this run.
        </div>
      </Panel>
    );
  }

  const merged = points.map((point, index) => {
    const row: Record<string, string | number> = {
      timestamp: point.timestamp,
      benchmark: point.benchmark_equity,
    };
    teamRuns.forEach((run) => {
      row[`${run.team_id}:${run.version_number}`] = run.equity_curve[index]?.strategy_equity ?? point.strategy_equity;
    });
    return row;
  });

  return (
    <Panel title="Equity vs SPY" eyebrow="Always visible benchmark">
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={merged}>
            <XAxis dataKey="timestamp" hide />
            <YAxis hide />
            <Tooltip />
            <Line type="monotone" dataKey="benchmark" name="SPY" stroke="#ca5f3f" strokeWidth={2} dot={false} />
            {teamRuns.map((run, index) => (
              <Line
                key={`${run.team_id}:${run.version_number}`}
                type="monotone"
                dataKey={`${run.team_id}:${run.version_number}`}
                name={`${run.team_name} v${run.version_number}`}
                stroke={TEAM_COLORS[index % TEAM_COLORS.length]}
                strokeWidth={index === 0 ? 3 : 2}
                dot={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  );
}
