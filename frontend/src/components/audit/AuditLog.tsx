import { useDeferredValue, useMemo, useState } from "react";
import type { AuditEntry } from "../../api/types";
import Panel from "../common/Panel";

export default function AuditLog({ entries }: { entries: AuditEntry[] }) {
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query);
  const filtered = useMemo(
    () =>
      entries.filter((entry) =>
        JSON.stringify(entry).toLowerCase().includes(deferredQuery.toLowerCase()),
      ),
    [entries, deferredQuery],
  );

  return (
    <Panel title="Immutable audit log" eyebrow="Local trail">
      <input
        className="mb-4 w-full rounded-2xl bg-slate px-4 py-3"
        placeholder="Filter audit entries"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />
      <div className="space-y-3">
        {filtered.length ? (
          filtered.map((entry, index) => {
            const details = Object.entries(entry).filter(([key]) => !["timestamp", "actor", "event_type"].includes(key));
            return (
              <div key={`${entry.timestamp}-${index}`} className="rounded-2xl bg-slate p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <div className="font-semibold text-ink">{String(entry.event_type ?? "event")}</div>
                  <div className="text-xs text-ink/55">{String(entry.actor ?? "system")}</div>
                  <div className="text-xs text-ink/55">{String(entry.timestamp ?? "")}</div>
                </div>
                {details.length ? (
                  <div className="mt-3 grid gap-2">
                    {details.map(([key, value]) => (
                      <div key={key} className="rounded-2xl bg-white/75 px-3 py-2 text-xs text-ink/70">
                        <span className="font-semibold">{key}</span>: {typeof value === "object" ? JSON.stringify(value) : String(value)}
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            );
          })
        ) : (
          <div className="rounded-2xl bg-slate px-4 py-5 text-sm text-ink/65">
            No audit entries match this filter yet.
          </div>
        )}
      </div>
    </Panel>
  );
}
