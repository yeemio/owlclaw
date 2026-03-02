import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type Point = { period_start: string; total_cost: string };

export function BudgetTrend({ data }: { data: Point[] }): JSX.Element {
  const chartData = data.map((item) => ({ x: item.period_start.slice(5, 10), y: Number(item.total_cost) }));
  return (
    <div className="h-56 rounded-lg border border-border bg-card p-4">
      <h3 className="mb-2 text-sm text-foreground">Budget Trend</h3>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <XAxis dataKey="x" stroke="#8ea0b6" />
          <YAxis stroke="#8ea0b6" />
          <Tooltip />
          <Line type="monotone" dataKey="y" stroke="#16a085" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
