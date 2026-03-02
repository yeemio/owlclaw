import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "@/components/layout/Layout";
import { AgentsPage } from "@/pages/Agents";
import { CapabilitiesPage } from "@/pages/Capabilities";
import { ExternalDashboardPage } from "@/pages/ExternalDashboard";
import { GovernancePage } from "@/pages/Governance";
import { LedgerPage } from "@/pages/Ledger";
import { OverviewPage } from "@/pages/Overview";
import { SettingsPage } from "@/pages/Settings";
import { TriggersPage } from "@/pages/Triggers";

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/agents" element={<AgentsPage />} />
        <Route path="/governance" element={<GovernancePage />} />
        <Route path="/capabilities" element={<CapabilitiesPage />} />
        <Route path="/triggers" element={<TriggersPage />} />
        <Route path="/ledger" element={<LedgerPage />} />
        <Route path="/traces" element={<ExternalDashboardPage kind="traces" />} />
        <Route path="/workflows" element={<ExternalDashboardPage kind="workflows" />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate replace to="/" />} />
      </Routes>
    </Layout>
  );
}

export default App;
