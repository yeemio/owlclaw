import { render, screen } from "@testing-library/react";
import { HealthIndicator } from "@/components/data/HealthIndicator";

describe("HealthIndicator", () => {
  it("shows component name", () => {
    render(<HealthIndicator item={{ component: "runtime", healthy: true }} />);
    expect(screen.getByText("runtime")).toBeInTheDocument();
  });
});
