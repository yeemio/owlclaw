export function Header(): JSX.Element {
  return (
    <header className="flex items-center justify-between border-b border-border px-4 py-3">
      <span className="text-sm text-foreground/80">Governance Control Plane</span>
      <span className="rounded bg-muted px-2 py-1 text-xs text-foreground">Live</span>
    </header>
  );
}
