import { FormEvent, useEffect, useMemo, useState } from "react";

import { apiGet, apiPost, apiPut } from "@/shared/api/client";
import { Button } from "@/shared/ui/button";
import { getStoredLanguage, setStoredLanguage, UiLanguage } from "@/shared/lib/i18n";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { ChangePasswordRequest } from "@/types/auth";
import { DetectedUserAliasOption, StreamFuseSettings, StreamFuseSettingsUpdate } from "@/types/settings";

const TEXT = {
  es: {
    pageTitle: "Ajustes",
    pageSubtitle: "Configura proveedores, frecuencia de sondeo, posteres y retencion.",
    lastUpdate: "Ultima actualizacion",
    notSavedYet: "Sin guardar",
    validationError: "Error de validacion",
    settingsUnavailable: "Ajustes no disponibles",
    payloadEmpty: "Los ajustes estan vacios.",
    retry: "Reintentar",
    savedSuccess: "Ajustes guardados correctamente.",
    // Provider connections
    providerConnections: "Conexiones de proveedor",
    providerDesc: "URLs, credenciales y fuente de logs para Tautulli + SFTPGo.",
    tautulliUrl: "Tautulli URL",
    tautulliApiKey: "Tautulli API Key",
    sftpgoUrl: "SFTPGo URL",
    sftpgoToken: "SFTPGo Token / Credenciales",
    configured: "Configurado",
    leaveEmpty: "- dejar vacio para conservar",
    notConfigured: "No configurado",
    sftpgoLogsPath: "Ruta de logs SFTPGo",
    sftpgoPathMappings: "Mapeos de ruta SFTPGo (uno por linea)",
    // Samba
    sambaSection: "Samba",
    sambaDesc: "Importar descargas SMB activas de snapshots JSON de smbstatus.",
    sambaEnabled: "Activar ingestion de Samba",
    sambaStatusJson: "Ruta JSON de estado de Samba",
    sambaPathMappings: "Mapeos de ruta Samba (uno por linea)",
    // Unraid
    unraidSection: "Metricas del sistema Unraid",
    unraidDesc: "Usar snapshots del host para ancho de banda / total compartido y telemetria hardware.",
    unraidEnabled: "Activar integracion de metricas Unraid",
    unraidJsonPath: "Ruta JSON de metricas Unraid",
    useUnraidTotals: "Usar totales de Unraid para Total Compartido y Ancho de Banda",
    tariffPunta: "Tarifa Punta (EUR/kWh)",
    tariffLlano: "Tarifa Llano (EUR/kWh)",
    tariffValle: "Tarifa Valle (EUR/kWh)",
    tariffWeekend: "Fin de semana (EUR/kWh)",
    // Behavior
    behaviorSection: "Comportamiento",
    pollingFreq: "Frecuencia de sondeo (segundos)",
    timezone: "Zona horaria",
    uiLanguage: "Idioma de interfaz",
    langEs: "Espanol",
    langEn: "English",
    placeholderPath: "Ruta de marcador de posicion",
    historyRetention: "Retencion de historial (dias)",
    mediaRoots: "Rutas raiz de medios",
    posterNames: "Nombres de poster preferidos",
    // User aliases
    userAliases: "Alias de usuario",
    userAliasDesc: "Selecciona un usuario detectado y asigna el nombre a mostrar en Dashboard e Historial.",
    detectedUser: "Usuario detectado",
    aliasLabel: "Alias",
    aliasPlaceholder: "Nombre a mostrar",
    setAlias: "Aplicar alias",
    noUsersDetected: "Sin usuarios detectados",
    sources: "Fuentes",
    sessions: "Sesiones",
    currentAlias: "Alias actual",
    noAliases: "Sin alias configurados.",
    remove: "Eliminar",
    // Admin security
    adminSecurity: "Seguridad del administrador",
    adminSecurityDesc: "El usuario es fijo como admin. Cambia la contrasena aqui.",
    currentPassword: "Contrasena actual",
    newPassword: "Nueva contrasena",
    changingPassword: "Cambiando...",
    changePassword: "Cambiar contrasena de admin",
    passwordSuccess: "Contrasena de admin actualizada correctamente.",
    // Buttons
    saving: "Guardando...",
    saveSettings: "Guardar ajustes",
    resetChanges: "Descartar cambios",
  },
  en: {
    pageTitle: "Settings",
    pageSubtitle: "Configure providers, polling cadence, poster behavior, and retention.",
    lastUpdate: "Last update",
    notSavedYet: "Not saved yet",
    validationError: "Validation or save error",
    settingsUnavailable: "Settings unavailable",
    payloadEmpty: "Settings payload is empty.",
    retry: "Retry",
    savedSuccess: "Settings saved successfully.",
    providerConnections: "Provider Connections",
    providerDesc: "URLs, credentials and log source for Tautulli + SFTPGo.",
    tautulliUrl: "Tautulli URL",
    tautulliApiKey: "Tautulli API Key",
    sftpgoUrl: "SFTPGo URL",
    sftpgoToken: "SFTPGo Token / Credentials",
    configured: "Configured",
    leaveEmpty: "- leave empty to keep",
    notConfigured: "Not configured",
    sftpgoLogsPath: "SFTPGo Logs Path",
    sftpgoPathMappings: "SFTPGo Path Mappings (one per line)",
    sambaSection: "Samba",
    sambaDesc: "Import active SMB downloads from smbstatus JSON snapshots.",
    sambaEnabled: "Enable Samba ingestion",
    sambaStatusJson: "Samba Status JSON Path",
    sambaPathMappings: "Samba Path Mappings (one per line)",
    unraidSection: "Unraid System Metrics",
    unraidDesc: "Use host snapshots for bandwidth/total shared and hardware telemetry.",
    unraidEnabled: "Enable Unraid metrics integration",
    unraidJsonPath: "Unraid metrics JSON path",
    useUnraidTotals: "Use Unraid totals for Total Shared and Total Bandwidth",
    tariffPunta: "Tariff Punta (EUR/kWh)",
    tariffLlano: "Tariff Llano (EUR/kWh)",
    tariffValle: "Tariff Valle (EUR/kWh)",
    tariffWeekend: "Weekend (EUR/kWh)",
    behaviorSection: "Behavior",
    pollingFreq: "Polling Frequency (seconds)",
    timezone: "Timezone",
    uiLanguage: "UI Language",
    langEs: "Espanol",
    langEn: "English",
    placeholderPath: "Placeholder Path",
    historyRetention: "History Retention (days)",
    mediaRoots: "Media Root Paths",
    posterNames: "Preferred Poster Names",
    userAliases: "User Aliases",
    userAliasDesc: "Select a detected user and assign the display name to show across Dashboard and History.",
    detectedUser: "Detected user",
    aliasLabel: "Alias",
    aliasPlaceholder: "Display name",
    setAlias: "Set Alias",
    noUsersDetected: "No users detected yet",
    sources: "Sources",
    sessions: "Sessions",
    currentAlias: "Current alias",
    noAliases: "No aliases configured.",
    remove: "Remove",
    adminSecurity: "Admin Security",
    adminSecurityDesc: "User is fixed as admin. Change password here.",
    currentPassword: "Current password",
    newPassword: "New password",
    changingPassword: "Changing...",
    changePassword: "Change Admin Password",
    passwordSuccess: "Admin password updated successfully.",
    saving: "Saving...",
    saveSettings: "Save Settings",
    resetChanges: "Reset Changes",
  },
} as const;

type SettingsFormState = {
  tautulliUrl: string;
  tautulliApiKey: string;
  sftpgoUrl: string;
  sftpgoToken: string;
  sftpgoLogsPath: string;
  sftpgoPathMappings: string;
  sambaEnabled: boolean;
  sambaStatusJsonPath: string;
  sambaPathMappings: string;
  unraidMetricsEnabled: boolean;
  unraidMetricsJsonPath: string;
  useUnraidTotals: boolean;
  energyTariffPunta: string;
  energyTariffLlano: string;
  energyTariffValle: string;
  energyTariffWeekend: string;
  pollingFrequencySeconds: string;
  timezone: string;
  uiLanguage: "es" | "en";
  mediaRootPaths: string;
  preferredPosterNames: string;
  userAliases: Record<string, string>;
  placeholderPath: string;
  historyRetentionDays: string;
};

function parseListFromTextarea(text: string): string[] {
  return text
    .split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function mapSettingsToForm(settings: StreamFuseSettings): SettingsFormState {
  return {
    tautulliUrl: settings.tautulli_url,
    tautulliApiKey: "",
    sftpgoUrl: settings.sftpgo_url,
    sftpgoToken: "",
    sftpgoLogsPath: settings.sftpgo_logs_path ?? "",
    sftpgoPathMappings: settings.sftpgo_path_mappings.join("\n"),
    sambaEnabled: settings.samba_enabled,
    sambaStatusJsonPath: settings.samba_status_json_path ?? "",
    sambaPathMappings: settings.samba_path_mappings.join("\n"),
    unraidMetricsEnabled: settings.unraid_metrics_enabled,
    unraidMetricsJsonPath: settings.unraid_metrics_json_path ?? "",
    useUnraidTotals: settings.use_unraid_totals,
    energyTariffPunta: String(settings.energy_tariff_punta_eur_kwh),
    energyTariffLlano: String(settings.energy_tariff_llano_eur_kwh),
    energyTariffValle: String(settings.energy_tariff_valle_eur_kwh),
    energyTariffWeekend: String(settings.energy_tariff_weekend_eur_kwh),
    pollingFrequencySeconds: String(settings.polling_frequency_seconds),
    timezone: settings.timezone,
    uiLanguage: settings.ui_language,
    mediaRootPaths: settings.media_root_paths.join("\n"),
    preferredPosterNames: settings.preferred_poster_names.join("\n"),
    userAliases: { ...settings.user_aliases },
    placeholderPath: settings.placeholder_path,
    historyRetentionDays: String(settings.history_retention_days),
  };
}

function validateForm(form: SettingsFormState): string | null {
  if (!form.tautulliUrl.startsWith("http://") && !form.tautulliUrl.startsWith("https://")) {
    return "Tautulli URL must start with http:// or https://";
  }
  if (!form.sftpgoUrl.startsWith("http://") && !form.sftpgoUrl.startsWith("https://")) {
    return "SFTPGo URL must start with http:// or https://";
  }

  const polling = Number(form.pollingFrequencySeconds);
  if (!Number.isFinite(polling) || polling < 5) {
    return "Polling frequency must be 5 seconds or higher";
  }

  const retention = Number(form.historyRetentionDays);
  if (!Number.isFinite(retention) || retention < 1) {
    return "History retention must be 1 day or higher";
  }

  if (!form.timezone.trim()) {
    return "Timezone is required";
  }

  const tariffs = [form.energyTariffPunta, form.energyTariffLlano, form.energyTariffValle, form.energyTariffWeekend].map((item) => Number(item));
  if (tariffs.some((item) => !Number.isFinite(item) || item < 0)) {
    return "Energy tariffs must be valid numbers >= 0";
  }

  return null;
}

const inputClass =
  "w-full rounded-lg border border-white/15 bg-white/[0.03] px-3 py-2 text-sm text-fg outline-none transition placeholder:text-fg-muted/70 focus:border-primary/60 focus:ring-2 focus:ring-primary/30";
const selectClass =
  "w-full rounded-lg border border-white/15 bg-slate-900 px-3 py-2 text-sm text-white outline-none transition focus:border-primary/60 focus:ring-2 focus:ring-primary/30";
const selectOptionStyle = {
  backgroundColor: "#0b1930",
  color: "#e6f2ff",
};
const labelClass = "mb-1 block text-xs font-semibold uppercase tracking-[0.12em] text-fg-muted";

export function SettingsPage() {
  const [lang, setLang] = useState<UiLanguage>(getStoredLanguage());
  useEffect(() => {
    const handler = (e: Event) => setLang((e as CustomEvent<{ language: UiLanguage }>).detail.language);
    window.addEventListener("streamfuse:language-changed", handler);
    return () => window.removeEventListener("streamfuse:language-changed", handler);
  }, []);
  const tx = TEXT[lang];

  const [settings, setSettings] = useState<StreamFuseSettings | null>(null);
  const [form, setForm] = useState<SettingsFormState | null>(null);
  const [detectedUsers, setDetectedUsers] = useState<DetectedUserAliasOption[]>([]);
  const [selectedDetectedUser, setSelectedDetectedUser] = useState("");
  const [aliasDraft, setAliasDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [changingPassword, setChangingPassword] = useState(false);

  const loadDetectedUsers = async () => {
    const users = await apiGet<DetectedUserAliasOption[]>("/settings/detected-users");
    setDetectedUsers(users);
    setSelectedDetectedUser((current) => {
      if (current && users.some((item) => item.user_name === current)) {
        return current;
      }
      return users[0]?.user_name ?? "";
    });
  };

  const loadSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      const [data] = await Promise.all([
        apiGet<StreamFuseSettings>("/settings"),
        loadDetectedUsers(),
      ]);
      setSettings(data);
      setForm(mapSettingsToForm(data));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load settings");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadSettings();
  }, []);

  useEffect(() => {
    const onRefresh = () => {
      void loadSettings();
    };
    window.addEventListener("streamfuse:refresh", onRefresh);
    return () => window.removeEventListener("streamfuse:refresh", onRefresh);
  }, []);

  const updatedAtLabel = useMemo(() => {
    if (!settings?.updated_at) {
      return tx.notSavedYet;
    }
    return new Date(settings.updated_at).toLocaleString();
  }, [settings, tx]);

  const selectedDetectedUserMeta = useMemo(
    () => detectedUsers.find((item) => item.user_name === selectedDetectedUser) ?? null,
    [detectedUsers, selectedDetectedUser]
  );

  useEffect(() => {
    if (!form || !selectedDetectedUser) {
      setAliasDraft("");
      return;
    }
    setAliasDraft(form.userAliases[selectedDetectedUser] ?? "");
  }, [form, selectedDetectedUser]);

  const onApplyAliasDraft = () => {
    if (!form || !selectedDetectedUser) {
      return;
    }
    const trimmed = aliasDraft.trim();
    const nextAliases = { ...form.userAliases };
    if (!trimmed) {
      delete nextAliases[selectedDetectedUser];
    } else {
      nextAliases[selectedDetectedUser] = trimmed;
    }
    setForm({ ...form, userAliases: nextAliases });
  };

  const onDeleteAlias = (sourceUser: string) => {
    if (!form) {
      return;
    }
    const nextAliases = { ...form.userAliases };
    delete nextAliases[sourceUser];
    setForm({ ...form, userAliases: nextAliases });
  };

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!form) {
      return;
    }

    const validationError = validateForm(form);
    if (validationError) {
      setError(validationError);
      setSuccess(null);
      return;
    }

    const payload: StreamFuseSettingsUpdate = {
      tautulli_url: form.tautulliUrl.trim(),
      sftpgo_url: form.sftpgoUrl.trim(),
      sftpgo_logs_path: form.sftpgoLogsPath.trim(),
      sftpgo_path_mappings: parseListFromTextarea(form.sftpgoPathMappings),
      samba_enabled: form.sambaEnabled,
      samba_status_json_path: form.sambaStatusJsonPath.trim(),
      samba_path_mappings: parseListFromTextarea(form.sambaPathMappings),
      unraid_metrics_enabled: form.unraidMetricsEnabled,
      unraid_metrics_json_path: form.unraidMetricsJsonPath.trim(),
      use_unraid_totals: form.useUnraidTotals,
      energy_tariff_punta_eur_kwh: Number(form.energyTariffPunta),
      energy_tariff_llano_eur_kwh: Number(form.energyTariffLlano),
      energy_tariff_valle_eur_kwh: Number(form.energyTariffValle),
      energy_tariff_weekend_eur_kwh: Number(form.energyTariffWeekend),
      polling_frequency_seconds: Number(form.pollingFrequencySeconds),
      timezone: form.timezone.trim(),
      ui_language: form.uiLanguage,
      media_root_paths: parseListFromTextarea(form.mediaRootPaths),
      preferred_poster_names: parseListFromTextarea(form.preferredPosterNames),
      user_aliases: form.userAliases,
      placeholder_path: form.placeholderPath.trim(),
      history_retention_days: Number(form.historyRetentionDays),
    };

    if (form.tautulliApiKey.trim()) {
      payload.tautulli_api_key = form.tautulliApiKey.trim();
    }
    if (form.sftpgoToken.trim()) {
      payload.sftpgo_token = form.sftpgoToken.trim();
    }

    try {
      setSaving(true);
      setError(null);
      const updated = await apiPut<StreamFuseSettings, StreamFuseSettingsUpdate>("/settings", payload);
      setStoredLanguage(updated.ui_language);
      setSettings(updated);
      setForm(mapSettingsToForm(updated));
      await loadDetectedUsers();
      setSuccess(tx.savedSuccess);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save settings");
      setSuccess(null);
    } finally {
      setSaving(false);
    }
  };

  const onChangePassword = async () => {
    if (!currentPassword.trim() || !newPassword.trim()) {
      setError("Current and new password are required");
      setSuccess(null);
      return;
    }
    if (newPassword.trim().length < 8) {
      setError("New password must have at least 8 characters");
      setSuccess(null);
      return;
    }

    try {
      setChangingPassword(true);
      setError(null);
      await apiPost<{ ok: boolean }, ChangePasswordRequest>("/auth/change-password", {
        current_password: currentPassword.trim(),
        new_password: newPassword.trim(),
      });
      setCurrentPassword("");
      setNewPassword("");
      setSuccess(tx.passwordSuccess);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to change password");
      setSuccess(null);
    } finally {
      setChangingPassword(false);
    }
  };

  if (loading) {
    return <LoadingState title={tx.pageTitle} />;
  }

  if (error && !form) {
    return (
      <div className="space-y-4">
        <ErrorState title={tx.settingsUnavailable} description={error} />
        <Button variant="outline" onClick={() => void loadSettings()}>
          {tx.retry}
        </Button>
      </div>
    );
  }

  if (!form || !settings) {
    return <ErrorState title={tx.settingsUnavailable} description={tx.payloadEmpty} />;
  }

  const aliasEntries = Object.entries(form.userAliases).sort(([a], [b]) => a.localeCompare(b));

  return (
    <div className="space-y-6">
      <header className="space-y-2 min-h-[72px]">
        <h2 className="font-display text-3xl text-white">{tx.pageTitle}</h2>
        <p className="text-sm text-fg-muted">{tx.pageSubtitle}</p>
        <p className="text-xs uppercase tracking-[0.12em] text-fg-muted">{tx.lastUpdate}: {updatedAtLabel}</p>
      </header>

      {error ? <ErrorState title={tx.validationError} description={error} /> : null}
      {success ? (
        <div className="rounded-xl border border-emerald-400/30 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-200">{success}</div>
      ) : null}

      <form onSubmit={(event) => void onSubmit(event)} className="space-y-6">
        <section className="grid grid-cols-1 gap-4 rounded-2xl border border-white/10 bg-card p-5 md:grid-cols-2">
          <div className="md:col-span-2">
            <h3 className="font-display text-xl text-white">{tx.providerConnections}</h3>
            <p className="text-sm text-fg-muted">{tx.providerDesc}</p>
          </div>

          <div>
            <label className={labelClass} htmlFor="tautulli-url">{tx.tautulliUrl}</label>
            <input id="tautulli-url" className={inputClass} value={form.tautulliUrl} onChange={(event) => setForm({ ...form, tautulliUrl: event.target.value })} />
          </div>

          <div>
            <label className={labelClass} htmlFor="tautulli-api-key">{tx.tautulliApiKey}</label>
            <input
              id="tautulli-api-key"
              type="password"
              className={inputClass}
              placeholder={settings.tautulli_api_key_set ? `${tx.configured} (${settings.tautulli_api_key_masked ?? "hidden"}) ${tx.leaveEmpty}` : tx.notConfigured}
              value={form.tautulliApiKey}
              onChange={(event) => setForm({ ...form, tautulliApiKey: event.target.value })}
            />
          </div>

          <div>
            <label className={labelClass} htmlFor="sftpgo-url">{tx.sftpgoUrl}</label>
            <input id="sftpgo-url" className={inputClass} value={form.sftpgoUrl} onChange={(event) => setForm({ ...form, sftpgoUrl: event.target.value })} />
          </div>

          <div>
            <label className={labelClass} htmlFor="sftpgo-token">{tx.sftpgoToken}</label>
            <input
              id="sftpgo-token"
              type="password"
              className={inputClass}
              placeholder={settings.sftpgo_token_set ? `${tx.configured} (${settings.sftpgo_token_masked ?? "hidden"}) ${tx.leaveEmpty}` : tx.notConfigured}
              value={form.sftpgoToken}
              onChange={(event) => setForm({ ...form, sftpgoToken: event.target.value })}
            />
          </div>

          <div className="md:col-span-2">
            <label className={labelClass} htmlFor="sftpgo-logs-path">{tx.sftpgoLogsPath}</label>
            <input id="sftpgo-logs-path" className={inputClass} value={form.sftpgoLogsPath} onChange={(event) => setForm({ ...form, sftpgoLogsPath: event.target.value })} placeholder="/data/sftp-logs/transfers.jsonl" />
          </div>

          <div className="md:col-span-2">
            <label className={labelClass} htmlFor="sftpgo-path-mappings">{tx.sftpgoPathMappings}</label>
            <textarea id="sftpgo-path-mappings" rows={4} className={inputClass} value={form.sftpgoPathMappings} onChange={(event) => setForm({ ...form, sftpgoPathMappings: event.target.value })} placeholder="/multimedia/peliculas:/peliculas&#10;/multimedia/series:/series" />
          </div>
        </section>

        <section className="grid grid-cols-1 gap-4 rounded-2xl border border-white/10 bg-card p-5 md:grid-cols-2">
          <div className="md:col-span-2">
            <h3 className="font-display text-xl text-white">{tx.sambaSection}</h3>
            <p className="text-sm text-fg-muted">{tx.sambaDesc}</p>
          </div>

          <div className="md:col-span-2 flex items-center gap-3 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
            <input id="samba-enabled" type="checkbox" checked={form.sambaEnabled} onChange={(event) => setForm({ ...form, sambaEnabled: event.target.checked })} />
            <label htmlFor="samba-enabled" className="text-sm text-fg">{tx.sambaEnabled}</label>
          </div>

          <div className="md:col-span-2">
            <label className={labelClass} htmlFor="samba-status-json">{tx.sambaStatusJson}</label>
            <input id="samba-status-json" className={inputClass} value={form.sambaStatusJsonPath} onChange={(event) => setForm({ ...form, sambaStatusJsonPath: event.target.value })} placeholder="/data/samba-status.json" />
          </div>

          <div className="md:col-span-2">
            <label className={labelClass} htmlFor="samba-path-mappings">{tx.sambaPathMappings}</label>
            <textarea id="samba-path-mappings" rows={4} className={inputClass} value={form.sambaPathMappings} onChange={(event) => setForm({ ...form, sambaPathMappings: event.target.value })} placeholder="/multimedia/peliculas:/peliculas&#10;/multimedia/series:/series" />
          </div>
        </section>

        <section className="grid grid-cols-1 gap-4 rounded-2xl border border-white/10 bg-card p-5 md:grid-cols-2">
          <div className="md:col-span-2">
            <h3 className="font-display text-xl text-white">{tx.unraidSection}</h3>
            <p className="text-sm text-fg-muted">{tx.unraidDesc}</p>
          </div>

          <div className="md:col-span-2 flex items-center gap-3 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
            <input id="unraid-metrics-enabled" type="checkbox" checked={form.unraidMetricsEnabled} onChange={(event) => setForm({ ...form, unraidMetricsEnabled: event.target.checked })} />
            <label htmlFor="unraid-metrics-enabled" className="text-sm text-fg">{tx.unraidEnabled}</label>
          </div>

          <div className="md:col-span-2">
            <label className={labelClass} htmlFor="unraid-metrics-json-path">{tx.unraidJsonPath}</label>
            <input
              id="unraid-metrics-json-path"
              className={inputClass}
              value={form.unraidMetricsJsonPath}
              onChange={(event) => setForm({ ...form, unraidMetricsJsonPath: event.target.value })}
              placeholder="/data/unraid-metrics.json"
            />
          </div>

          <div className="md:col-span-2 flex items-center gap-3 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
            <input id="use-unraid-totals" type="checkbox" checked={form.useUnraidTotals} onChange={(event) => setForm({ ...form, useUnraidTotals: event.target.checked })} />
            <label htmlFor="use-unraid-totals" className="text-sm text-fg">{tx.useUnraidTotals}</label>
          </div>

          <div>
            <label className={labelClass} htmlFor="tariff-punta">{tx.tariffPunta}</label>
            <input id="tariff-punta" type="number" step="0.001" min={0} className={inputClass} value={form.energyTariffPunta} onChange={(event) => setForm({ ...form, energyTariffPunta: event.target.value })} />
          </div>

          <div>
            <label className={labelClass} htmlFor="tariff-llano">{tx.tariffLlano}</label>
            <input id="tariff-llano" type="number" step="0.001" min={0} className={inputClass} value={form.energyTariffLlano} onChange={(event) => setForm({ ...form, energyTariffLlano: event.target.value })} />
          </div>

          <div>
            <label className={labelClass} htmlFor="tariff-valle">{tx.tariffValle}</label>
            <input id="tariff-valle" type="number" step="0.001" min={0} className={inputClass} value={form.energyTariffValle} onChange={(event) => setForm({ ...form, energyTariffValle: event.target.value })} />
          </div>

          <div>
            <label className={labelClass} htmlFor="tariff-weekend">{tx.tariffWeekend}</label>
            <input id="tariff-weekend" type="number" step="0.001" min={0} className={inputClass} value={form.energyTariffWeekend} onChange={(event) => setForm({ ...form, energyTariffWeekend: event.target.value })} />
          </div>
        </section>

        <section className="grid grid-cols-1 gap-4 rounded-2xl border border-white/10 bg-card p-5 md:grid-cols-2">
          <div className="md:col-span-2">
            <h3 className="font-display text-xl text-white">{tx.behaviorSection}</h3>
          </div>

          <div>
            <label className={labelClass} htmlFor="polling-frequency">{tx.pollingFreq}</label>
            <input id="polling-frequency" type="number" min={5} className={inputClass} value={form.pollingFrequencySeconds} onChange={(event) => setForm({ ...form, pollingFrequencySeconds: event.target.value })} />
          </div>

          <div>
            <label className={labelClass} htmlFor="timezone">{tx.timezone}</label>
            <input id="timezone" className={inputClass} value={form.timezone} onChange={(event) => setForm({ ...form, timezone: event.target.value })} placeholder="Europe/Madrid" />
          </div>

          <div>
            <label className={labelClass} htmlFor="ui-language">{tx.uiLanguage}</label>
            <select
              id="ui-language"
              className={selectClass}
              value={form.uiLanguage}
              onChange={(event) => setForm({ ...form, uiLanguage: (event.target.value === "en" ? "en" : "es") })}
            >
              <option value="es" style={selectOptionStyle}>{tx.langEs}</option>
              <option value="en" style={selectOptionStyle}>{tx.langEn}</option>
            </select>
          </div>

          <div>
            <label className={labelClass} htmlFor="placeholder-path">{tx.placeholderPath}</label>
            <input id="placeholder-path" className={inputClass} value={form.placeholderPath} onChange={(event) => setForm({ ...form, placeholderPath: event.target.value })} />
          </div>

          <div>
            <label className={labelClass} htmlFor="history-retention">{tx.historyRetention}</label>
            <input id="history-retention" type="number" min={1} className={inputClass} value={form.historyRetentionDays} onChange={(event) => setForm({ ...form, historyRetentionDays: event.target.value })} />
          </div>

          <div>
            <label className={labelClass} htmlFor="media-roots">{tx.mediaRoots}</label>
            <textarea id="media-roots" rows={5} className={inputClass} value={form.mediaRootPaths} onChange={(event) => setForm({ ...form, mediaRootPaths: event.target.value })} placeholder="/media/movies&#10;/media/series" />
          </div>

          <div>
            <label className={labelClass} htmlFor="poster-names">{tx.posterNames}</label>
            <textarea id="poster-names" rows={5} className={inputClass} value={form.preferredPosterNames} onChange={(event) => setForm({ ...form, preferredPosterNames: event.target.value })} placeholder="poster.jpg&#10;cover.jpg&#10;folder.jpg" />
          </div>
        </section>

        <section className="rounded-2xl border border-white/10 bg-card p-5 space-y-4">
          <div>
            <h3 className="font-display text-xl text-white">{tx.userAliases}</h3>
            <p className="text-sm text-fg-muted">{tx.userAliasDesc}</p>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-[2fr_2fr_auto] md:items-end">
            <div>
              <label className={labelClass} htmlFor="detected-user">{tx.detectedUser}</label>
              <select
                id="detected-user"
                className={selectClass}
                value={selectedDetectedUser}
                onChange={(event) => setSelectedDetectedUser(event.target.value)}
              >
                {detectedUsers.length === 0 ? <option value="" style={selectOptionStyle}>{tx.noUsersDetected}</option> : null}
                {detectedUsers.map((user) => (
                  <option key={user.user_name} value={user.user_name} style={selectOptionStyle}>
                    {user.user_name} ({user.session_count})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className={labelClass} htmlFor="alias-input">{tx.aliasLabel}</label>
              <input
                id="alias-input"
                className={inputClass}
                value={aliasDraft}
                onChange={(event) => setAliasDraft(event.target.value)}
                placeholder={tx.aliasPlaceholder}
              />
            </div>

            <Button type="button" variant="outline" onClick={onApplyAliasDraft} disabled={!selectedDetectedUser}>
              {tx.setAlias}
            </Button>
          </div>

          {selectedDetectedUserMeta ? (
            <p className="text-xs text-fg-muted">
              {tx.sources}: {selectedDetectedUserMeta.sources.join(", ") || "n/a"}
              {" | "}
              {tx.sessions}: {selectedDetectedUserMeta.session_count}
              {selectedDetectedUserMeta.alias ? ` | ${tx.currentAlias}: ${selectedDetectedUserMeta.alias}` : ""}
            </p>
          ) : null}

          <div className="space-y-2">
            {aliasEntries.length === 0 ? <p className="text-sm text-fg-muted">{tx.noAliases}</p> : null}
            {aliasEntries.map(([source, alias]) => (
              <div key={source} className="grid grid-cols-1 gap-2 rounded-lg border border-white/10 bg-white/[0.02] p-3 md:grid-cols-[2fr_2fr_auto] md:items-center">
                <p className="text-sm text-fg">{source}</p>
                <input
                  className={inputClass}
                  value={alias}
                  onChange={(event) => setForm({ ...form, userAliases: { ...form.userAliases, [source]: event.target.value } })}
                />
                <Button type="button" variant="ghost" onClick={() => onDeleteAlias(source)}>
                  {tx.remove}
                </Button>
              </div>
            ))}
          </div>
        </section>

        <section className="grid grid-cols-1 gap-4 rounded-2xl border border-white/10 bg-card p-5 md:grid-cols-2">
          <div className="md:col-span-2">
            <h3 className="font-display text-xl text-white">{tx.adminSecurity}</h3>
            <p className="text-sm text-fg-muted">{tx.adminSecurityDesc}</p>
          </div>

          <div>
            <label className={labelClass} htmlFor="current-password">{tx.currentPassword}</label>
            <input
              id="current-password"
              type="password"
              className={inputClass}
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
            />
          </div>

          <div>
            <label className={labelClass} htmlFor="new-password">{tx.newPassword}</label>
            <input
              id="new-password"
              type="password"
              className={inputClass}
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
            />
          </div>

          <div className="md:col-span-2">
            <Button type="button" variant="outline" disabled={changingPassword} onClick={() => void onChangePassword()}>
              {changingPassword ? tx.changingPassword : tx.changePassword}
            </Button>
          </div>
        </section>

        <div className="flex items-center gap-3">
          <Button type="submit" disabled={saving}>{saving ? tx.saving : tx.saveSettings}</Button>
          <Button type="button" variant="outline" onClick={() => setForm(mapSettingsToForm(settings))}>{tx.resetChanges}</Button>
        </div>
      </form>
    </div>
  );
}
