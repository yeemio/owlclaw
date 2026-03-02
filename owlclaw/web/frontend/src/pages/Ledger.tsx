import { useState } from "react";
import { useLedger } from "@/hooks/useApi";

export default function Ledger(): JSX.Element {
  const { data } = useLedger();
  const [filter, setFilter] = useState("");

  const rows = (data?.items ?? []).filter((item) => JSON.stringify(item).toLowerCase().includes(filter.toLowerCase()));

  return (
    <section className="space-y-3">
      <input
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        placeholder="Filter by agent/capability/status"
        className="w-full rounded border border-border bg-card p-2 text-sm text-foreground"
      />
      <div className="rounded-lg border border-border bg-card p-4">
        <table className="w-full text-left text-sm text-foreground">
          <thead>
            <tr><th>ID</th><th>Status</th></tr>
          </thead>
          <tbody>
            {rows.map((item, i) => (
              <tr key={i}><td>{String(item.id ?? "-")}</td><td>{String(item.status ?? "-")}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
