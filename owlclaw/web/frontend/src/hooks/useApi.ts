import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";

type HealthStatus = "healthy" | "degraded" | "unhealthy";

export type OverviewSnapshot = {
  health_status: HealthStatus;
  active_agents: number;
  executions_today: number;
  success_rate: number;
  cost_today_usd: number;
};

export function useOverview() {
  return useQuery({
    queryKey: ["overview"],
    queryFn: () => apiFetch<OverviewSnapshot>("/overview"),
    refetchInterval: 30_000,
  });
}
