import { useEffect, useState } from "react";
import { useCapabilities } from "@/hooks/useApi";
import { apiFetch } from "@/api/client";
import { SchemaViewer } from "@/components/data/SchemaViewer";

export default function Capabilities(): JSX.Element {
  const { data } = useCapabilities();
  const [selected, setSelected] = useState<string | null>(null);
  const [schema, setSchema] = useState<unknown>(null);

  useEffect(() => {
    if (!selected) {
      return;
    }
    apiFetch(`/capabilities/${selected}/schema`).then(setSchema).catch(() => setSchema({ error: "schema fetch failed" }));
  }, [selected]);

  return (
    <section className="grid gap-4 md:grid-cols-[1fr_1.2fr]">
      <div className="rounded-lg border border-border bg-card p-4">
        <h3 className="mb-2 text-sm text-foreground">Handlers / Skills / Bindings</h3>
        <div className="space-y-2 text-sm">
          {(data ?? []).map((item) => (
            <button
              key={String(item.name ?? item.id ?? Math.random())}
              className="block w-full rounded bg-muted px-2 py-1 text-left text-foreground"
              onClick={() => setSelected(String(item.name ?? ""))}
            >
              {String(item.name ?? "unknown")}
            </button>
          ))}
        </div>
      </div>
      <SchemaViewer schema={schema ?? { hint: "Select capability to view schema" }} />
    </section>
  );
}
