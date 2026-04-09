import type { PropsWithChildren } from "react";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";

export default function AppShell({ children }: PropsWithChildren) {
  return (
    <div className="grid min-h-screen grid-cols-1 gap-5 p-3 lg:grid-cols-[260px_minmax(0,1fr)] lg:p-5">
      {/* Sidebar wrapper — grid-sheen gives it the subtle grid texture */}
      <div className="grid-sheen self-start sticky top-3 rounded-[36px] p-1.5 lg:top-5">
        <Sidebar />
      </div>

      {/* Main content */}
      <main className="space-y-5 min-w-0">
        <TopBar />
        <div className="space-y-5">{children}</div>
      </main>
    </div>
  );
}
