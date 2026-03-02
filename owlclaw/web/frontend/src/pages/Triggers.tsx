import { useTriggers } from "@/hooks/useApi";

export default function Triggers(): JSX.Element {
  const { data } = useTriggers();
  return (
    <section className="rounded-lg border border-border bg-card p-4">
      <h3 className="mb-2 text-sm text-foreground">Unified Trigger List</h3>
      <table className="w-full text-left text-sm text-foreground">
        <thead>
          <tr><th>ID</th><th>Type</th><th>Enabled</th></tr>
        </thead>
        <tbody>
          {(data ?? []).map((item, i) => (
            <tr key={i}><td>{String(item.id ?? "-")}</td><td>{String(item.type ?? "-")}</td><td>{String(item.enabled ?? "-")}</td></tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
