import { Link } from "react-router-dom";
import { useAgents } from "@/hooks/useApi";

export default function Agents(): JSX.Element {
  const { data } = useAgents();
  return (
    <section className="grid gap-3 md:grid-cols-2">
      {(data ?? []).map((agent) => (
        <article key={String(agent.id)} className="rounded-lg border border-border bg-card p-4 text-foreground">
          <h3 className="font-semibold">{String(agent.id)}</h3>
          <p className="text-xs text-foreground/70">runtime status available</p>
          <Link className="mt-2 inline-block text-xs text-primary" to={`/agents/${String(agent.id)}`}>
            View detail
          </Link>
        </article>
      ))}
    </section>
  );
}
