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

export type LedgerStatus = "success" | "failed" | "running";

export type LedgerRecord = {
  id: string;
  timestamp: string;
  agent: string;
  capability: string;
  status: LedgerStatus;
  cost_usd: number;
  model: string;
  latency_ms: number;
  input: string;
  output: string;
  reasoning: string;
};

export type LedgerFilters = {
  agent?: string;
  capability?: string;
  status?: LedgerStatus | "";
  start_time?: string;
  end_time?: string;
  min_cost?: number;
  max_cost?: number;
};

export type PaginatedLedger = {
  records: LedgerRecord[];
  total: number;
  limit: number;
  offset: number;
};

export type AgentStatus = "active" | "idle" | "error";

export type AgentSummary = {
  id: string;
  name: string;
  role: string;
  status: AgentStatus;
  identity_summary: string;
};

export type AgentRunRecord = {
  timestamp: string;
  capability: string;
  status: LedgerStatus;
  cost_usd: number;
};

export type AgentDetail = {
  id: string;
  name: string;
  role: string;
  status: AgentStatus;
  identity: Record<string, string>;
  memory: {
    short_term_count: number;
    long_term_count: number;
  };
  knowledge: {
    skills: string[];
    references_count: number;
  };
  recent_runs: AgentRunRecord[];
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

function normalizeLedgerRecord(raw: unknown): LedgerRecord {
  const item = (raw as Partial<LedgerRecord>) ?? {};
  return {
    id: String(item.id ?? ""),
    timestamp: String(item.timestamp ?? ""),
    agent: String(item.agent ?? "unknown"),
    capability: String(item.capability ?? "unknown"),
    status: ((item.status ?? "success") as LedgerStatus),
    cost_usd: toNumber(item.cost_usd),
    model: String(item.model ?? "unknown"),
    latency_ms: toNumber(item.latency_ms),
    input: String(item.input ?? ""),
    output: String(item.output ?? ""),
    reasoning: String(item.reasoning ?? ""),
  };
}

function normalizePaginatedLedger(raw: unknown, limit: number, offset: number): PaginatedLedger {
  const input = (raw as Partial<PaginatedLedger>) ?? {};
  return {
    records: Array.isArray(input.records) ? input.records.map((record) => normalizeLedgerRecord(record)) : [],
    total: toNumber(input.total),
    limit: toNumber(input.limit) || limit,
    offset: toNumber(input.offset) || offset,
  };
}

function normalizeAgentSummary(raw: unknown): AgentSummary {
  const item = (raw as Partial<AgentSummary>) ?? {};
  return {
    id: String(item.id ?? ""),
    name: String(item.name ?? "Unnamed Agent"),
    role: String(item.role ?? "agent"),
    status: (item.status ?? "idle") as AgentStatus,
    identity_summary: String(item.identity_summary ?? ""),
  };
}

function normalizeAgentDetail(raw: unknown): AgentDetail {
  const item = (raw as Partial<AgentDetail>) ?? {};
  const memory = item.memory ?? { short_term_count: 0, long_term_count: 0 };
  const knowledge = item.knowledge ?? { skills: [], references_count: 0 };

  return {
    id: String(item.id ?? ""),
    name: String(item.name ?? "Unnamed Agent"),
    role: String(item.role ?? "agent"),
    status: (item.status ?? "idle") as AgentStatus,
    identity:
      typeof item.identity === "object" && item.identity
        ? Object.fromEntries(Object.entries(item.identity).map(([key, value]) => [key, String(value)]))
        : {},
    memory: {
      short_term_count: toNumber(memory.short_term_count),
      long_term_count: toNumber(memory.long_term_count),
    },
    knowledge: {
      skills: Array.isArray(knowledge.skills) ? knowledge.skills.map((skill) => String(skill)) : [],
      references_count: toNumber(knowledge.references_count),
    },
    recent_runs: Array.isArray(item.recent_runs)
      ? item.recent_runs.map((run) => ({
          timestamp: String((run as AgentRunRecord).timestamp ?? ""),
          capability: String((run as AgentRunRecord).capability ?? "unknown"),
          status: ((run as AgentRunRecord).status ?? "success") as LedgerStatus,
          cost_usd: toNumber((run as AgentRunRecord).cost_usd),
        }))
      : [],
  };
}

function buildLedgerQuery(filters: LedgerFilters, limit: number, offset: number): string {
  const params = new URLSearchParams();
  if (filters.agent) {
    params.set("agent", filters.agent);
  }
  if (filters.capability) {
    params.set("capability", filters.capability);
  }
  if (filters.status) {
    params.set("status", filters.status);
  }
  if (filters.start_time) {
    params.set("start_time", filters.start_time);
  }
  if (filters.end_time) {
    params.set("end_time", filters.end_time);
  }
  if (typeof filters.min_cost === "number") {
    params.set("min_cost", String(filters.min_cost));
  }
  if (typeof filters.max_cost === "number") {
    params.set("max_cost", String(filters.max_cost));
  }
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  return params.toString();
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

export function useLedger(filters: LedgerFilters, limit = 20, offset = 0) {
  return useQuery({
    queryKey: ["ledger", filters, limit, offset],
    queryFn: async () =>
      normalizePaginatedLedger(
        await apiFetch<unknown>(`/ledger?${buildLedgerQuery(filters, limit, offset)}`),
        limit,
        offset
      ),
    refetchInterval: 30_000,
  });
}

export function useAgents() {
  return useQuery({
    queryKey: ["agents"],
    queryFn: async () => {
      const raw = await apiFetch<unknown>("/agents");
      const items = Array.isArray(raw) ? raw : [];
      return items.map((item) => normalizeAgentSummary(item));
    },
    refetchInterval: 30_000,
  });
}

export function useAgentDetail(agentId: string | null) {
  return useQuery({
    queryKey: ["agent", agentId],
    queryFn: async () => normalizeAgentDetail(await apiFetch<unknown>(`/agents/${agentId}`)),
    enabled: Boolean(agentId),
    refetchInterval: 30_000,
  });
}
