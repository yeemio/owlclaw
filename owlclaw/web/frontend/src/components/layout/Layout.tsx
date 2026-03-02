import type { PropsWithChildren } from "react";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

export function Layout({ children }: PropsWithChildren): JSX.Element {
  return (
    <div className="min-h-screen md:flex">
      <Sidebar />
      <main className="min-h-screen flex-1">
        <Header />
        <div className="p-4">{children}</div>
      </main>
    </div>
  );
}
