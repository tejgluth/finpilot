import type { TeamVersion } from "../../api/types";
import TeamClassificationBadge from "../studio/TeamClassificationBadge";
import Panel from "../common/Panel";

export default function SavedTeamsPanel({
  teams,
  activeTeam,
  onSelect,
}: {
  teams: TeamVersion[];
  activeTeam: TeamVersion | null;
  onSelect: (teamId: string, versionNumber: number) => void;
}) {
  return (
    <Panel title="Saved teams" eyebrow="Library">
      <div className="space-y-3">
        {teams.map((team) => {
          const isActive =
            activeTeam?.team_id === team.team_id && activeTeam.version_number === team.version_number;
          return (
            <div className="rounded-2xl bg-slate px-4 py-3" key={`${team.team_id}:${team.version_number}`}>
              <div className="mb-2 flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold">
                      {team.compiled_team.name} v{team.version_number}
                    </span>
                    <TeamClassificationBadge classification={team.team_classification} />
                  </div>
                  <div className="text-sm text-ink/60">{team.compiled_team.description}</div>
                </div>
                <button
                  className={`rounded-full px-4 py-2 text-xs font-semibold ${
                    isActive ? "bg-ink text-white" : "border border-ink/10 bg-white text-ink/70"
                  }`}
                  onClick={() => onSelect(team.team_id, team.version_number)}
                  type="button"
                >
                  {isActive ? "Active" : "Use team"}
                </button>
              </div>
              <div className="text-xs text-ink/50">
                {team.is_default ? "Premade default" : team.label} | {team.status}
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}
