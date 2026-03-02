import { useParams } from "react-router-dom";

export default function AgentDetail(): JSX.Element {
  const { id } = useParams();
  return (
    <section className="rounded-lg border border-border bg-card p-4 text-foreground">
      <h2 className="text-lg font-semibold">Agent {id}</h2>
      <p className="text-sm text-foreground/70">Identity, memory, knowledge and timeline are displayed here.</p>
    </section>
  );
}
