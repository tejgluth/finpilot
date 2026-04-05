import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { AuditEntry } from "../api/types";
import AuditLog from "../components/audit/AuditLog";

export default function AuditPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);

  useEffect(() => {
    void api.getAudit().then((payload) => setEntries(payload.entries));
  }, []);

  return <AuditLog entries={entries} />;
}
