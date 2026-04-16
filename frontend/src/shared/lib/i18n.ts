export type UiLanguage = "es" | "en";

const STORAGE_KEY = "streamfuse.ui_language";

type TranslationKey =
  | "nav.dashboard"
  | "nav.dashboardHint"
  | "nav.history"
  | "nav.historyHint"
  | "nav.stats"
  | "nav.statsHint"
  | "nav.settings"
  | "nav.settingsHint"
  | "header.title"
  | "header.subtitle"
  | "header.refresh"
  | "header.newFilter"
  | "header.logout"
  | "header.disabled"
  | "source.health"
  | "source.connected"
  | "source.disconnected"
  | "source.checking";

const translations: Record<UiLanguage, Record<TranslationKey, string>> = {
  es: {
    "nav.dashboard": "Dashboard",
    "nav.dashboardHint": "Control en directo",
    "nav.history": "Historial",
    "nav.historyHint": "Timeline de reproduccion",
    "nav.stats": "Estadisticas",
    "nav.statsHint": "Analitica y tendencias",
    "nav.settings": "Ajustes",
    "nav.settingsHint": "Configuracion del sistema",
    "header.title": "StreamFuse Console",
    "header.subtitle": "Visibilidad premium de sesiones multimedia y transferencias.",
    "header.refresh": "Actualizar",
    "header.newFilter": "Nuevo filtro",
    "header.logout": "Cerrar sesion",
    "header.disabled": "Desactivado temporalmente",
    "source.health": "Estado de fuentes",
    "source.connected": "conectado",
    "source.disconnected": "desconectado",
    "source.checking": "comprobando",
  },
  en: {
    "nav.dashboard": "Dashboard",
    "nav.dashboardHint": "Live control room",
    "nav.history": "History",
    "nav.historyHint": "Playback timeline",
    "nav.stats": "Stats",
    "nav.statsHint": "Analytics & trends",
    "nav.settings": "Settings",
    "nav.settingsHint": "System config",
    "header.title": "StreamFuse Console",
    "header.subtitle": "Premium visibility for media sessions and transfer activity.",
    "header.refresh": "Refresh",
    "header.newFilter": "New filter",
    "header.logout": "Logout",
    "header.disabled": "Temporarily disabled",
    "source.health": "Source Health",
    "source.connected": "connected",
    "source.disconnected": "disconnected",
    "source.checking": "checking",
  },
};

export function normalizeLanguage(value: string | null | undefined): UiLanguage {
  return value === "en" ? "en" : "es";
}

export function getStoredLanguage(): UiLanguage {
  if (typeof window === "undefined") {
    return "es";
  }
  return normalizeLanguage(window.localStorage.getItem(STORAGE_KEY));
}

export function setStoredLanguage(language: UiLanguage): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(STORAGE_KEY, language);
  window.dispatchEvent(new CustomEvent("streamfuse:language-changed", { detail: { language } }));
}

export function t(language: UiLanguage, key: TranslationKey): string {
  return translations[language][key] ?? translations.es[key] ?? key;
}
