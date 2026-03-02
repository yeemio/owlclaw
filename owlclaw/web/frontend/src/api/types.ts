export type HealthCheck = {
  component: string;
  healthy: boolean;
  message?: string;
};

export type OverviewData = {
  total_cost_today: string;
  total_executions_today: number;
  success_rate_today: number;
  active_agents: number;
  health_checks: HealthCheck[];
};

export type ApiErrorPayload = {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
};
