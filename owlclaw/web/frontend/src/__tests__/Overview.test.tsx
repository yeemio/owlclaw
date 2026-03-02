import { render, screen } from "@testing-library/react";
import Overview from "@/pages/Overview";

vi.mock("@/hooks/useWebSocket", () => ({ useConsoleWebSocket: () => undefined }));
vi.mock("@/hooks/useApi", () => ({
  useOverview: () => ({
    data: {
      total_cost_today: "1.00",
      total_executions_today: 1,
      success_rate_today: 1,
      active_agents: 1,
      health_checks: [{ component: "runtime", healthy: true }],
    },
    isLoading: false,
    error: null,
  }),
}));

describe("Overview page", () => {
  it("renders overview payload", async () => {
    render(<Overview />);
    expect(await screen.findByTestId("overview-page")).toBeInTheDocument();
    expect(screen.getByText("Health")).toBeInTheDocument();
  });
});
