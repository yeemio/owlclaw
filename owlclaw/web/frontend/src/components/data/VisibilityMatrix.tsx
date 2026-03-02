type VisibilityItem = { capability_name: string; visible: boolean };

export function VisibilityMatrix({ items }: { items: VisibilityItem[] }): JSX.Element {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h3 className="mb-2 text-sm text-foreground">Visibility Matrix</h3>
      <div className="grid grid-cols-2 gap-2 text-xs">
        {items.map((item) => (
          <div key={item.capability_name} className="rounded bg-muted p-2 text-foreground">
            {item.capability_name}: {item.visible ? "visible" : "hidden"}
          </div>
        ))}
      </div>
    </div>
  );
}
