import { useDeferredValue, useMemo, useState } from "react";
import type { AuditEntry } from "../../api/types";
import Panel from "../common/Panel";

function humanizeEventType(raw: string): string {
  return raw
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatTimestamp(raw: string): string {
  try {
    const d = new Date(raw);
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return raw;
  }
}

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
    <Panel title="Audit log" eyebrow="Local record">
      <input
        className="mb-4 w-full rounded-2xl border border-ink/[0.08] bg-slate px-4 py-2.5 text-sm text-ink outline-none transition focus:border-tide/40 focus:ring-2 focus:ring-tide/10"
        placeholder="Filter by event type, actor, or any field…"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />
      <div className="space-y-2.5">
        {filtered.length ? (
          filtered.map((entry, index) => {
            const details = Object.entries(entry).filter(([key]) => !["timestamp", "actor", "event_type"].includes(key));
            const eventLabel = humanizeEventType(String(entry.event_type ?? "event"));
            const actor = String(entry.actor ?? "system");
            const timestamp = entry.timestamp ? formatTimestamp(String(entry.timestamp)) : "";
            return (
              <div key={`${entry.timestamp}-${index}`} className="rounded-2xl bg-slate p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="font-semibold text-ink">{eventLabel}</div>
                    <div className="mt-0.5 font-mono text-[10px] uppercase tracking-[0.15em] text-ink/45">{actor}</div>
                  </div>
                  <div className="font-mono text-[10px] text-ink/40 tabular-nums">{timestamp}</div>
                </div>
                {details.length ? (
                  <div className="mt-3 grid gap-1.5">
                    {details.map(([key, value]) => (
                      <div key={key} className="flex gap-2 rounded-xl bg-white/70 px-3 py-2 text-xs">
                        <span className="font-mono text-ink/45 shrink-0">{key}</span>
                        <span className="text-ink/70 break-all">{typeof value === "object" ? JSON.stringify(value) : String(value)}</span>
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
