import { useMemo, useState } from "react";

import { AppShell } from "@/app/layout/AppShell";
import { DashboardPage } from "@/pages/DashboardPage";
import { HistoryPage } from "@/pages/HistoryPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { StatsPage } from "@/pages/StatsPage";

export type AppSection = "dashboard" | "history" | "stats" | "settings";

export function App() {
  const [section, setSection] = useState<AppSection>("dashboard");

  const content = useMemo(() => {
    switch (section) {
      case "history":
        return <HistoryPage />;
      case "stats":
        return <StatsPage />;
      case "settings":
        return <SettingsPage />;
      case "dashboard":
      default:
        return <DashboardPage />;
    }
  }, [section]);

  return <AppShell currentSection={section} onChangeSection={setSection}>{content}</AppShell>;
}
