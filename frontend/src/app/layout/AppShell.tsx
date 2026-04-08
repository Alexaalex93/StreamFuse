import { ReactNode } from "react";

import { AppSection } from "@/app/App";
import { StreamFuseLogo } from "@/shared/branding/StreamFuseLogo";
import { cn } from "@/shared/lib/cn";
import { Button } from "@/shared/ui/button";

type AppShellProps = {
  currentSection: AppSection;
  onChangeSection: (section: AppSection) => void;
  children: ReactNode;
};

const navItems: Array<{ id: AppSection; label: string; hint: string }> = [
  { id: "dashboard", label: "Dashboard", hint: "Live control room" },
  { id: "history", label: "History", hint: "Playback timeline" },
  { id: "stats", label: "Stats", hint: "Analytics & trends" },
  { id: "settings", label: "Settings", hint: "System config" },
];

export function AppShell({ currentSection, onChangeSection, children }: AppShellProps) {
  return (
    <div className="min-h-screen bg-app-gradient text-fg">
      <div className="mx-auto grid min-h-screen max-w-[1440px] grid-cols-1 lg:grid-cols-[280px_1fr]">
        <aside className="border-r border-white/10 bg-sidebar px-4 py-6 backdrop-blur-xl">
          <div className="mb-8 flex items-center gap-3 px-2">
            <StreamFuseLogo className="h-10 w-10" />
            <div>
              <p className="font-display text-lg font-bold tracking-wide text-white">StreamFuse</p>
              <p className="text-xs text-fg-muted">Unified media activity</p>
            </div>
          </div>

          <nav className="space-y-2">
            {navItems.map((item) => {
              const active = currentSection === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => onChangeSection(item.id)}
                  className={cn(
                    "group w-full rounded-xl border px-4 py-3 text-left transition",
                    active
                      ? "border-primary/60 bg-card/80 shadow-premium"
                      : "border-transparent bg-white/[0.02] hover:border-white/10 hover:bg-white/[0.04]",
                  )}
                >
                  <p className={cn("font-medium", active ? "text-white" : "text-fg")}>{item.label}</p>
                  <p className="text-xs text-fg-muted">{item.hint}</p>
                </button>
              );
            })}
          </nav>

          <div className="mt-8 rounded-xl border border-white/10 bg-card/50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-fg-muted">Source Health</p>
            <div className="mt-3 space-y-2 text-sm text-fg-muted">
              <p>Tautulli: connected</p>
              <p>SFTPGo: connected</p>
            </div>
          </div>
        </aside>

        <div className="flex min-h-screen flex-col">
          <header className="sticky top-0 z-20 border-b border-white/10 bg-topbar/70 px-4 py-3 backdrop-blur-xl md:px-8">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h1 className="font-display text-xl font-semibold text-white">StreamFuse Console</h1>
                <p className="text-xs text-fg-muted">Premium visibility for media sessions and transfer activity.</p>
              </div>
              <div className="flex items-center gap-3">
                <Button variant="ghost">Refresh</Button>
                <Button variant="default">New Filter</Button>
              </div>
            </div>
          </header>

          <main className="flex-1 px-4 py-6 md:px-8">{children}</main>
        </div>
      </div>
    </div>
  );
}
