import { useState } from "react";
import { BudgetTrend } from "@/components/charts/BudgetTrend";
import { CircuitBreakerCard } from "@/components/data/CircuitBreakerCard";
import { VisibilityMatrix } from "@/components/data/VisibilityMatrix";
import { useBudget } from "@/hooks/useApi";

export default function Governance(): JSX.Element {
  const [granularity, setGranularity] = useState<"day" | "week" | "month">("day");
  const { data } = useBudget(granularity);

  return (
    <section className="space-y-4">
      <div className="flex gap-2">
        {(["day", "week", "month"] as const).map((g) => (
          <button
            key={g}
            className="rounded border border-border bg-card px-3 py-1 text-sm text-foreground"
            onClick={() => setGranularity(g)}
          >
            {g}
          </button>
        ))}
      </div>
      <BudgetTrend data={data ?? []} />
      <div className="grid gap-3 md:grid-cols-2">
        <CircuitBreakerCard items={[{ capability_name: "entry-monitor", state: "closed" }]} />
        <VisibilityMatrix items={[{ capability_name: "entry-monitor", visible: true }]} />
      </div>
      <div className="rounded-lg border border-border bg-card p-4 text-sm text-foreground">migration_weight: 70%</div>
    </section>
  );
}
