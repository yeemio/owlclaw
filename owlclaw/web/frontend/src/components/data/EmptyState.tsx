export function EmptyState({ title, description }: { title: string; description: string }): JSX.Element {
  return (
    <div className="rounded-lg border border-dashed border-border bg-card p-6 text-center">
      <p className="text-sm font-semibold text-foreground">{title}</p>
      <p className="mt-1 text-xs text-foreground/70">{description}</p>
    </div>
  );
}
