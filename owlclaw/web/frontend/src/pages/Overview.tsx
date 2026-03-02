import { useOverview } from "@/hooks/useApi";
import { useConsoleWebSocket } from "@/hooks/useWebSocket";
import { MetricCard } from "@/components/charts/MetricCard";
import { HealthIndicator } from "@/components/data/HealthIndicator";
import { EmptyState } from "@/components/data/EmptyState";

export default function Overview(): JSX.Element {
  useConsoleWebSocket();
  const { data, isLoading, error } = useOverview();

  if (isLoading) {
    return <div className="text-foreground">Loading overview...</div>;
  }
  if (error || !data) {
    return <EmptyState title="Overview unavailable" description="Check API and token settings." />;
  }

  return (
    <section className="space-y-4" data-testid="overview-page">
      <div className="rounded-lg border border-border bg-card p-4">
        <p className="text-sm text-foreground">Get started</p>
        <p className="mt-1 text-xs text-foreground/70">Quick Start | Complete Workflow | SKILL.md Guide</p>
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        <MetricCard title="Cost Today" value={Number(data.total_cost_today)} delta={2.3} />
        <MetricCard title="Executions" value={data.total_executions_today} delta={1.2} />
        <MetricCard title="Success" value={data.success_rate_today * 100} delta={0.4} />
        <MetricCard title="Active Agents" value={data.active_agents} delta={0} />
      </div>
      <div className="rounded-lg border border-border bg-card p-4">
        <h2 className="mb-2 text-sm text-foreground">Health</h2>
        <div className="grid gap-2 md:grid-cols-2">
          {data.health_checks.map((item) => (
            <HealthIndicator key={item.component} item={item} />
          ))}
        </div>
      </div>
    </section>
  );
}
