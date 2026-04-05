import type { TeamBacktestRun } from "../../api/types";
import Panel from "../common/Panel";

export default function MetricsTable({
  benchmark,
  teamRuns,
}: {
  benchmark: Record<string, number>;
  teamRuns: TeamBacktestRun[];
}) {
  const keys = Array.from(
    new Set([
      ...Object.keys(benchmark),
      ...teamRuns.flatMap((run) => Object.keys(run.metrics)),
    ]),
  );
  return (
    <Panel title="Backtest metrics" eyebrow="Reality check">
      <div className="overflow-hidden rounded-2xl border border-ink/10">
        <table className="w-full text-sm">
          <thead className="bg-slate text-left">
            <tr>
              <th className="px-4 py-3">Metric</th>
              <th className="px-4 py-3">SPY</th>
              {teamRuns.map((run) => (
                <th className="px-4 py-3" key={`${run.team_id}:${run.version_number}`}>
                  {run.team_name} v{run.version_number}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {keys.map((key) => (
              <tr key={key} className="border-t border-ink/10">
                <td className="px-4 py-3">{key}</td>
                <td className="px-4 py-3">{benchmark[key] ?? "-"}</td>
                {teamRuns.map((run) => (
                  <td className="px-4 py-3" key={`${run.team_id}:${run.version_number}-${key}`}>
                    {run.metrics[key] ?? "-"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
