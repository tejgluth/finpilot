import type { PropsWithChildren } from "react";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";

export default function AppShell({ children }: PropsWithChildren) {
  return (
    <div className="grid min-h-screen grid-cols-1 gap-6 p-4 lg:grid-cols-[280px_minmax(0,1fr)] lg:p-6">
      <div className="grid-sheen rounded-[36px] p-2">
        <Sidebar />
      </div>
      <main className="space-y-6">
        <TopBar />
        <div className="space-y-6">{children}</div>
      </main>
    </div>
  );
}
