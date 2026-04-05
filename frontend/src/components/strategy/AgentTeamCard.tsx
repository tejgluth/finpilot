import type { CompiledTeam } from "../../api/types";
import Panel from "../common/Panel";
import AgentBadge from "./AgentBadge";
import AgentWeightSlider from "./AgentWeightSlider";

const ANALYSIS_AGENTS = [
  "fundamentals",
  "technicals",
  "sentiment",
  "macro",
  "value",
  "momentum",
  "growth",
] as const;

export default function AgentTeamCard({
  team,
  onWeightChange,
  onToggleAgent,
  onRiskChange,
  onHorizonChange,
}: {
  team: CompiledTeam;
  onWeightChange: (agent: string, value: number) => void;
  onToggleAgent: (agent: string, enabled: boolean) => void;
  onRiskChange: (risk: string) => void;
  onHorizonChange: (horizon: string) => void;
}) {
  return (
    <Panel title={team.name} eyebrow={`${team.risk_level} / ${team.time_horizon}`}>
      <div className="space-y-4">
        <p className="text-sm text-ink/70">{team.description}</p>

        <div className="grid gap-3 md:grid-cols-2">
          <label className="space-y-2 text-sm">
            <span className="block font-semibold text-ink">Risk level</span>
            <select
              className="w-full rounded-2xl border border-ink/10 bg-white px-4 py-3"
              onChange={(event) => onRiskChange(event.target.value)}
              value={team.risk_level}
            >
              <option value="conservative">Conservative</option>
              <option value="moderate">Moderate</option>
              <option value="aggressive">Aggressive</option>
            </select>
          </label>
          <label className="space-y-2 text-sm">
            <span className="block font-semibold text-ink">Time horizon</span>
            <select
              className="w-full rounded-2xl border border-ink/10 bg-white px-4 py-3"
              onChange={(event) => onHorizonChange(event.target.value)}
              value={team.time_horizon}
            >
              <option value="short">Short</option>
              <option value="medium">Medium</option>
              <option value="long">Long</option>
            </select>
          </label>
        </div>

        <div className="flex flex-wrap gap-2">
          {ANALYSIS_AGENTS.map((agent) => {
            const spec = team.compiled_agent_specs[agent];
            return (
              <AgentBadge
                enabled={team.enabled_agents.includes(agent)}
                key={agent}
                name={agent}
                sources={spec?.owned_sources ?? []}
                variant={spec?.variant_id}
              />
            );
          })}
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          {ANALYSIS_AGENTS.map((agent) => {
            const enabled = team.enabled_agents.includes(agent);
            const spec = team.compiled_agent_specs[agent];
            return (
              <div className="space-y-2 rounded-[24px] border border-ink/10 bg-white px-4 py-4" key={agent}>
                <label className="flex items-center justify-between text-sm font-semibold text-ink">
                  <span className="capitalize">{agent}</span>
                  <input checked={enabled} onChange={(event) => onToggleAgent(agent, event.target.checked)} type="checkbox" />
                </label>
                <div className="text-xs text-ink/55">
                  Variant: {spec?.variant_id ?? "balanced"} | freshness {spec?.freshness_limit_minutes ?? 60}m
                </div>
                <AgentWeightSlider
                  agent={agent}
                  disabled={!enabled}
                  onChange={(value) => onWeightChange(agent, value)}
                  value={team.agent_weights[agent] ?? 0}
                />
              </div>
            );
          })}
        </div>

        {team.validation_report.warnings.length ? (
          <div className="rounded-2xl bg-amber-100 px-4 py-3 text-sm text-amber-900">
            {team.validation_report.warnings.join(" ")}
          </div>
        ) : null}
      </div>
    </Panel>
  );
}
