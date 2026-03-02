import { NavLink } from "react-router-dom";
import { cn } from "@/lib/utils";

const links = [
  ["Overview", "/"],
  ["Agents", "/agents"],
  ["Governance", "/governance"],
  ["Capabilities", "/capabilities"],
  ["Triggers", "/triggers"],
  ["Ledger", "/ledger"],
  ["Traces", "/traces"],
  ["Workflows", "/workflows"],
  ["Settings", "/settings"],
] as const;

export function Sidebar(): JSX.Element {
  return (
    <aside className="w-full border-r border-border bg-card p-4 md:w-64">
      <h1 className="mb-4 text-lg font-bold text-foreground">OwlClaw Console</h1>
      <nav className="flex flex-col gap-2">
        {links.map(([label, to]) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn("rounded px-3 py-2 text-sm text-foreground/80", isActive && "bg-muted text-foreground")
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
