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

export type BudgetTrendPoint = {
  date: string;
  cost: number;
};

export type CircuitBreakerState = {
  name: string;
  state: "open" | "closed" | "half_open";
};

export type VisibilityRow = {
  agent: string;
  capabilities: Record<string, boolean>;
};

export type SkillQualityItem = {
  skill: string;
  score: number;
};

export type GovernanceSnapshot = {
  budget_trend: BudgetTrendPoint[];
  circuit_breakers: CircuitBreakerState[];
  visibility: VisibilityRow[];
  migration_weight: number;
  skills_quality_rank: SkillQualityItem[];
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

function normalizeGovernanceSnapshot(raw: unknown): GovernanceSnapshot {
  const input = (raw as Partial<GovernanceSnapshot>) ?? {};
  return {
    budget_trend: Array.isArray(input.budget_trend)
      ? input.budget_trend.map((item) => ({
          date: String((item as BudgetTrendPoint).date ?? ""),
          cost: toNumber((item as BudgetTrendPoint).cost),
        }))
      : [],
    circuit_breakers: Array.isArray(input.circuit_breakers)
      ? input.circuit_breakers.map((item) => ({
          name: String((item as CircuitBreakerState).name ?? "unknown"),
          state: ((item as CircuitBreakerState).state ?? "closed") as CircuitBreakerState["state"],
        }))
      : [],
    visibility: Array.isArray(input.visibility)
      ? input.visibility.map((item) => ({
          agent: String((item as VisibilityRow).agent ?? "unknown"),
          capabilities:
            typeof (item as VisibilityRow).capabilities === "object" && (item as VisibilityRow).capabilities
              ? (item as VisibilityRow).capabilities
              : {},
        }))
      : [],
    migration_weight: toNumber(input.migration_weight),
    skills_quality_rank: Array.isArray(input.skills_quality_rank)
      ? input.skills_quality_rank.map((item) => ({
          skill: String((item as SkillQualityItem).skill ?? "unknown"),
          score: toNumber((item as SkillQualityItem).score),
        }))
      : [],
  };
}

export function useOverview() {
  return useQuery({
    queryKey: ["overview"],
    queryFn: async () => normalizeOverviewSnapshot(await apiFetch<unknown>("/overview")),
    refetchInterval: 30_000,
  });
}

export function useGovernance(granularity: "day" | "week" | "month" = "day") {
  return useQuery({
    queryKey: ["governance", granularity],
    queryFn: async () =>
      normalizeGovernanceSnapshot(await apiFetch<unknown>(`/governance?granularity=${granularity}`)),
    refetchInterval: 30_000,
  });
}
