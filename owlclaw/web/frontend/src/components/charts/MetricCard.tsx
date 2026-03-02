import { fmtCurrency } from "@/lib/format";

type Props = {
  title: string;
  value: number;
  delta?: number;
};

export function MetricCard({ title, value, delta = 0 }: Props): JSX.Element {
  const trend = delta >= 0 ? "▲" : "▼";
  return (
    <div className="rounded-lg border border-border bg-card p-4" data-testid="metric-card">
      <p className="text-xs text-foreground/70">{title}</p>
      <p className="mt-2 text-2xl font-bold text-foreground">{fmtCurrency(value)}</p>
      <p className="mt-1 text-xs text-foreground/70">{trend} {Math.abs(delta).toFixed(1)}%</p>
    </div>
  );
}
