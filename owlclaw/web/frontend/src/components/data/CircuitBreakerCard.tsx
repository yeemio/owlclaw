type Item = { capability_name: string; state: string };

export function CircuitBreakerCard({ items }: { items: Item[] }): JSX.Element {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h3 className="mb-2 text-sm text-foreground">Circuit Breakers</h3>
      <div className="space-y-2 text-sm">
        {items.map((item) => (
          <div key={item.capability_name} className="flex justify-between text-foreground/85">
            <span>{item.capability_name}</span>
            <span>{item.state}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
