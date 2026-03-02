import { useSettings } from "@/hooks/useApi";

export default function Settings(): JSX.Element {
  const { data } = useSettings();
  return (
    <section className="space-y-3">
      <div className="rounded-lg border border-border bg-card p-4 text-sm text-foreground">Version / MCP / DB / OwlHub status</div>
      <pre className="rounded-lg border border-border bg-card p-4 text-xs text-foreground">{JSON.stringify(data ?? {}, null, 2)}</pre>
      <div className="rounded-lg border border-border bg-card p-4 text-sm text-foreground">Docs: Quick Start | SKILL.md Guide | AI Assist</div>
    </section>
  );
}
