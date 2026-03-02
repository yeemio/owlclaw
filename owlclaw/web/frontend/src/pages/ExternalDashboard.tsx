export default function ExternalDashboard({ type }: { type: "langfuse" | "hatchet" }): JSX.Element {
  const links = {
    langfuse: "http://localhost:3000",
    hatchet: "http://localhost:8080",
  };

  return (
    <section className="rounded-lg border border-border bg-card p-4 text-foreground">
      <h3 className="text-sm font-semibold">{type === "langfuse" ? "Traces" : "Workflows"}</h3>
      <p className="mt-1 text-sm text-foreground/70">Open external dashboard:</p>
      <a className="text-primary" href={links[type]} target="_blank" rel="noreferrer">{links[type]}</a>
    </section>
  );
}
