export function SchemaViewer({ schema }: { schema: unknown }): JSX.Element {
  return (
    <pre className="max-h-96 overflow-auto rounded-lg border border-border bg-card p-4 text-xs text-foreground">
      {JSON.stringify(schema, null, 2)}
    </pre>
  );
}
