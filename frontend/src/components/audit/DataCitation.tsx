import type { DataCitation as Citation } from "../../api/types";

export default function DataCitation({ citation }: { citation: Citation }) {
  return (
    <div className="rounded-2xl bg-slate px-4 py-3 text-sm text-ink/70">
      <div className="font-semibold text-ink">{citation.field_name}</div>
      <div className="mt-1">{citation.value}</div>
      <div className="mt-2 font-mono text-xs uppercase text-ink/50">
        {citation.source} • {citation.fetched_at}
      </div>
    </div>
  );
}
