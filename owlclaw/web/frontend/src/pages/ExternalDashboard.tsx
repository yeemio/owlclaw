import { PageShell } from "@/pages/PageShell";

type ExternalDashboardPageProps = {
  kind: "traces" | "workflows";
};

const PAGE_META: Record<ExternalDashboardPageProps["kind"], { title: string; description: string }> = {
  traces: {
    title: "Traces",
    description: "External trace links for Langfuse will be connected in Task 7.",
  },
  workflows: {
    title: "Workflows",
    description: "External workflow links for Hatchet will be connected in Task 7.",
  },
};

export function ExternalDashboardPage({ kind }: ExternalDashboardPageProps) {
  return <PageShell title={PAGE_META[kind].title} description={PAGE_META[kind].description} />;
}
