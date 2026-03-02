import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";

export type HealthStatus = "healthy" | "degraded" | "unhealthy";

export type HealthCheck = {
  component: string;
  healthy: boolean;
  latency_ms?: number | null;
  message?: string | null;
};

export type OverviewAlert = {
  level: "info" | "warning" | "critical";
  message: string;
};

export type OverviewSnapshot = {
  total_cost_today: number;
  total_executions_today: number;
  success_rate_today: number;
  active_agents: number;
  health_checks: HealthCheck[];
  alerts: OverviewAlert[];
};

function toNumber(value: unknown): number {
  if (typeof value === "number") {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
}

function normalizeOverviewSnapshot(raw: unknown): OverviewSnapshot {
  const input = (raw as Partial<OverviewSnapshot>) ?? {};
  return {
    total_cost_today: toNumber(input.total_cost_today),
    total_executions_today: toNumber(input.total_executions_today),
    success_rate_today: toNumber(input.success_rate_today),
    active_agents: toNumber(input.active_agents),
    health_checks: Array.isArray(input.health_checks) ? input.health_checks : [],
    alerts: Array.isArray(input.alerts) ? input.alerts : [],
  };
}

export function useOverview() {
  return useQuery({
    queryKey: ["overview"],
    queryFn: async () => normalizeOverviewSnapshot(await apiFetch<unknown>("/overview")),
    refetchInterval: 30_000,
  });
}
