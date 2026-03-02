import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "@/components/layout/Layout";

const Overview = lazy(() => import("@/pages/Overview"));
const Governance = lazy(() => import("@/pages/Governance"));
const Ledger = lazy(() => import("@/pages/Ledger"));
const Agents = lazy(() => import("@/pages/Agents"));
const AgentDetail = lazy(() => import("@/pages/AgentDetail"));
const Capabilities = lazy(() => import("@/pages/Capabilities"));
const Triggers = lazy(() => import("@/pages/Triggers"));
const Settings = lazy(() => import("@/pages/Settings"));
const ExternalDashboard = lazy(() => import("@/pages/ExternalDashboard"));

function Loading(): JSX.Element {
  return <div className="p-6 text-foreground">Loading...</div>;
}

export default function App(): JSX.Element {
  return (
    <Layout>
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/governance" element={<Governance />} />
          <Route path="/ledger" element={<Ledger />} />
          <Route path="/agents" element={<Agents />} />
          <Route path="/agents/:id" element={<AgentDetail />} />
          <Route path="/capabilities" element={<Capabilities />} />
          <Route path="/triggers" element={<Triggers />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/traces" element={<ExternalDashboard type="langfuse" />} />
          <Route path="/workflows" element={<ExternalDashboard type="hatchet" />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </Layout>
  );
}
