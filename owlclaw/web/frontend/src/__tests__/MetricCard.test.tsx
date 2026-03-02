import { render, screen } from "@testing-library/react";
import { MetricCard } from "@/components/charts/MetricCard";

describe("MetricCard", () => {
  it("renders title and value", () => {
    render(<MetricCard title="Cost" value={12.5} delta={1.1} />);
    expect(screen.getByText("Cost")).toBeInTheDocument();
    expect(screen.getByTestId("metric-card")).toBeInTheDocument();
  });
});
