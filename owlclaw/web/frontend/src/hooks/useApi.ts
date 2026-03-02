import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import type { OverviewData } from "@/api/types";

export function useOverview() {
  return useQuery({
    queryKey: ["overview"],
    queryFn: () => apiFetch<OverviewData>("/overview"),
    refetchInterval: 30_000,
  });
}

export function useBudget(granularity: "day" | "week" | "month") {
  return useQuery({
    queryKey: ["governance", "budget", granularity],
    queryFn: () => apiFetch<Array<{ period_start: string; total_cost: string }>>(`/governance/budget?granularity=${granularity}`),
  });
}

export function useLedger() {
  return useQuery({
    queryKey: ["ledger"],
    queryFn: () => apiFetch<{ items: Array<Record<string, unknown>>; total: number; offset: number; limit: number }>("/ledger"),
  });
}

export function useAgents() {
  return useQuery({ queryKey: ["agents"], queryFn: () => apiFetch<Array<Record<string, unknown>>>("/agents") });
}

export function useCapabilities() {
  return useQuery({ queryKey: ["capabilities"], queryFn: () => apiFetch<Array<Record<string, unknown>>>("/capabilities") });
}

export function useTriggers() {
  return useQuery({ queryKey: ["triggers"], queryFn: () => apiFetch<Array<Record<string, unknown>>>("/triggers") });
}

export function useSettings() {
  return useQuery({ queryKey: ["settings"], queryFn: () => apiFetch<Record<string, unknown>>("/settings") });
}
