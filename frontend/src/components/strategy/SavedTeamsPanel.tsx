import type { TeamVersion } from "../../api/types";
import TeamClassificationBadge from "../studio/TeamClassificationBadge";
import Panel from "../common/Panel";

export default function SavedTeamsPanel({
  teams,
  activeTeam,
  onSelect,
  onDelete,
}: {
  teams: TeamVersion[];
  activeTeam: TeamVersion | null;
  onSelect: (teamId: string, versionNumber: number) => void;
  onDelete?: (teamId: string, versionNumber: number) => void;
}) {
  const savedTeams = teams.filter((t) => !t.is_default);

  return (
    <Panel title="Saved teams" eyebrow="Library">
      <div className="space-y-3">
        {savedTeams.length === 0 ? (
          <p className="text-sm text-ink/50">No saved teams yet. Build and save a team to see it here.</p>
        ) : (
          savedTeams.map((team) => {
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
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      className={`rounded-full px-4 py-2 text-xs font-semibold ${
                        isActive ? "bg-ink text-white" : "border border-ink/10 bg-white text-ink/70"
                      }`}
                      onClick={() => onSelect(team.team_id, team.version_number)}
                      type="button"
                    >
                      {isActive ? "Active" : "Use team"}
                    </button>
                    {onDelete && (
                      <button
                        className="rounded-full border border-ember/20 px-3 py-2 text-xs text-ember/70 hover:border-ember/40 hover:text-ember"
                        onClick={() => {
                          if (confirm(`Delete "${team.compiled_team.name} v${team.version_number}"? This cannot be undone.`)) {
                            onDelete(team.team_id, team.version_number);
                          }
                        }}
                        title="Delete team"
                        type="button"
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </div>
                <div className="text-xs text-ink/50">
                  {team.label} | {team.status}
                </div>
              </div>
            );
          })
        )}
      </div>
    </Panel>
  );
}
