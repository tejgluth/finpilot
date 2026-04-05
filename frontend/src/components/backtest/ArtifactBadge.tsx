import type { BacktestArtifact } from "../../api/types";
import Panel from "../common/Panel";

export default function ArtifactBadge({ artifact }: { artifact: BacktestArtifact }) {
  const copyConfig = async () => {
    await navigator.clipboard.writeText(JSON.stringify(artifact.config_snapshot, null, 2));
  };

  return (
    <Panel title="Reproducibility artifact" eyebrow="Artifact">
      <div className="flex flex-wrap items-center gap-3 text-sm text-ink/70">
        <span>Artifact ID: {artifact.artifact_id}</span>
        <span>Data hash: {artifact.data_hash.slice(0, 12)}…</span>
        <span>{artifact.created_at}</span>
      </div>
      <div className="mt-3 rounded-2xl bg-slate px-4 py-3 text-sm text-ink/65">
        Snapshot {artifact.execution_snapshot.snapshot_id} | team {artifact.execution_snapshot.effective_team.name} |{" "}
        {artifact.execution_snapshot.data_boundary.mode}
      </div>
      <button className="mt-4 rounded-full bg-ink px-4 py-2 text-sm text-white" onClick={() => void copyConfig()}>
        Copy config JSON
      </button>
    </Panel>
  );
}
