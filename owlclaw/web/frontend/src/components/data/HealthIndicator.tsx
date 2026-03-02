import type { HealthCheck } from "@/api/types";

export function HealthIndicator({ item }: { item: HealthCheck }): JSX.Element {
  const cls = item.healthy ? "bg-emerald-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2 text-sm text-foreground" data-testid="health-indicator">
      <span className={`inline-block h-2.5 w-2.5 rounded-full ${cls}`} />
      <span>{item.component}</span>
    </div>
  );
}
