import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/app/layout/AppShell";
import { clearAuthToken, getAuthToken, apiGet } from "@/shared/api/client";
import { LoginPage } from "@/pages/LoginPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { HistoryPage } from "@/pages/HistoryPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { StatsPage } from "@/pages/StatsPage";
import { AuthStatusResponse } from "@/types/auth";

export type AppSection = "dashboard" | "history" | "stats" | "settings";

export function App() {
  const [section, setSection] = useState<AppSection>("dashboard");
  const [authenticated, setAuthenticated] = useState<boolean>(Boolean(getAuthToken()));
  const [checking, setChecking] = useState<boolean>(Boolean(getAuthToken()));

  useEffect(() => {
    if (!getAuthToken()) {
      setChecking(false);
      setAuthenticated(false);
      return;
    }

    let mounted = true;
    apiGet<AuthStatusResponse>("/auth/me")
      .then(() => {
        if (mounted) {
          setAuthenticated(true);
          setChecking(false);
        }
      })
      .catch(() => {
        clearAuthToken();
        if (mounted) {
          setAuthenticated(false);
          setChecking(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, []);

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

  if (checking) {
    return <div className="min-h-screen bg-app-gradient" />;
  }

  if (!authenticated) {
    return <LoginPage onAuthenticated={() => setAuthenticated(true)} />;
  }

  return (
    <AppShell
      currentSection={section}
      onChangeSection={setSection}
      onLogout={() => {
        clearAuthToken();
        setAuthenticated(false);
      }}
    >
      {content}
    </AppShell>
  );
}
