import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/app/layout/AppShell";
import { clearAuthToken, getAuthToken, apiGet } from "@/shared/api/client";
import { getStoredLanguage, normalizeLanguage, UiLanguage, setStoredLanguage } from "@/shared/lib/i18n";
import { LoginPage } from "@/pages/LoginPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { HistoryPage } from "@/pages/HistoryPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { StatsPage } from "@/pages/StatsPage";
import { AuthStatusResponse } from "@/types/auth";
import { StreamFuseSettings } from "@/types/settings";

export type AppSection = "dashboard" | "history" | "stats" | "settings";

export function App() {
  const [section, setSection] = useState<AppSection>("dashboard");
  const [authenticated, setAuthenticated] = useState<boolean>(Boolean(getAuthToken()));
  const [checking, setChecking] = useState<boolean>(Boolean(getAuthToken()));
  const [language, setLanguage] = useState<UiLanguage>(getStoredLanguage());

  useEffect(() => {
    const onLanguageChanged = (event: Event) => {
      const detail = (event as CustomEvent<{ language?: string }>).detail;
      const nextLanguage = normalizeLanguage(detail?.language);
      setLanguage(nextLanguage);
    };
    window.addEventListener("streamfuse:language-changed", onLanguageChanged);
    return () => window.removeEventListener("streamfuse:language-changed", onLanguageChanged);
  }, []);

  useEffect(() => {
    if (!getAuthToken()) {
      setChecking(false);
      setAuthenticated(false);
      return;
    }

    let mounted = true;
    apiGet<AuthStatusResponse>("/auth/me")
      .then(async () => {
        if (mounted) {
          setAuthenticated(true);
        }
        try {
          const settings = await apiGet<StreamFuseSettings>("/settings");
          const nextLanguage = normalizeLanguage(settings.ui_language);
          setStoredLanguage(nextLanguage);
          if (mounted) {
            setLanguage(nextLanguage);
          }
        } catch {
          // Keep local language if settings endpoint fails temporarily.
        } finally {
          if (mounted) {
            setChecking(false);
          }
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
      language={language}
    >
      {content}
    </AppShell>
  );
}
