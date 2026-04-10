import { FormEvent, useEffect, useMemo, useState } from "react";

import { apiGet, apiPut } from "@/shared/api/client";
import { Button } from "@/shared/ui/button";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { StreamFuseSettings, StreamFuseSettingsUpdate } from "@/types/settings";

type SettingsFormState = {
  tautulliUrl: string;
  tautulliApiKey: string;
  sftpgoUrl: string;
  sftpgoToken: string;
  sftpgoLogsPath: string;
  sftpgoPathMappings: string;
  pollingFrequencySeconds: string;
  timezone: string;
  mediaRootPaths: string;
  preferredPosterNames: string;
  userAliases: string;
  placeholderPath: string;
  historyRetentionDays: string;
};

function parseListFromTextarea(text: string): string[] {
  return text
    .split(/\r?\n|,/) 
    .map((item) => item.trim())
    .filter(Boolean);
}

function aliasesToTextarea(value: Record<string, string>): string {
  return Object.entries(value)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, alias]) => `${key}=${alias}`)
    .join("\n");
}

function parseAliasesFromTextarea(text: string): Record<string, string> {
  const result: Record<string, string> = {};
  const lines = text.split(/\r?\n/);

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) {
      continue;
    }

    const separator = line.includes("=") ? "=" : line.includes(":") ? ":" : null;
    if (!separator) {
      continue;
    }

    const [sourceRaw, ...rest] = line.split(separator);
    const source = sourceRaw.trim();
    const alias = rest.join(separator).trim();
    if (!source || !alias) {
      continue;
    }
    result[source] = alias;
  }

  return result;
}

function mapSettingsToForm(settings: StreamFuseSettings): SettingsFormState {
  return {
    tautulliUrl: settings.tautulli_url,
    tautulliApiKey: "",
    sftpgoUrl: settings.sftpgo_url,
    sftpgoToken: "",
    sftpgoLogsPath: settings.sftpgo_logs_path ?? "",
    sftpgoPathMappings: settings.sftpgo_path_mappings.join("\n"),
    pollingFrequencySeconds: String(settings.polling_frequency_seconds),
    timezone: settings.timezone,
    mediaRootPaths: settings.media_root_paths.join("\n"),
    preferredPosterNames: settings.preferred_poster_names.join("\n"),
    userAliases: aliasesToTextarea(settings.user_aliases),
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

  return null;
}

const inputClass =
  "w-full rounded-lg border border-white/15 bg-white/[0.03] px-3 py-2 text-sm text-fg outline-none transition placeholder:text-fg-muted/70 focus:border-primary/60 focus:ring-2 focus:ring-primary/30";
const labelClass = "mb-1 block text-xs font-semibold uppercase tracking-[0.12em] text-fg-muted";

export function SettingsPage() {
  const [settings, setSettings] = useState<StreamFuseSettings | null>(null);
  const [form, setForm] = useState<SettingsFormState | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const loadSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiGet<StreamFuseSettings>("/settings");
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
      return "Not saved yet";
    }
    return new Date(settings.updated_at).toLocaleString();
  }, [settings]);

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
      polling_frequency_seconds: Number(form.pollingFrequencySeconds),
      timezone: form.timezone.trim(),
      media_root_paths: parseListFromTextarea(form.mediaRootPaths),
      preferred_poster_names: parseListFromTextarea(form.preferredPosterNames),
      user_aliases: parseAliasesFromTextarea(form.userAliases),
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
      setSettings(updated);
      setForm(mapSettingsToForm(updated));
      setSuccess("Settings saved successfully.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save settings");
      setSuccess(null);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <LoadingState title="Loading settings" />;
  }

  if (error && !form) {
    return (
      <div className="space-y-4">
        <ErrorState title="Settings unavailable" description={error} />
        <Button variant="outline" onClick={() => void loadSettings()}>
          Retry
        </Button>
      </div>
    );
  }

  if (!form || !settings) {
    return <ErrorState title="Settings unavailable" description="Settings payload is empty." />;
  }

  return (
    <div className="space-y-6">
      <header className="space-y-2 min-h-[72px]">
        <h2 className="font-display text-3xl text-white">Settings</h2>
        <p className="text-sm text-fg-muted">Configure providers, polling cadence, poster behavior, and retention.</p>
        <p className="text-xs uppercase tracking-[0.12em] text-fg-muted">Last update: {updatedAtLabel}</p>
      </header>

      {error ? <ErrorState title="Validation or save error" description={error} /> : null}
      {success ? (
        <div className="rounded-xl border border-emerald-400/30 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-200">{success}</div>
      ) : null}

      <form onSubmit={(event) => void onSubmit(event)} className="space-y-6">
        <section className="grid grid-cols-1 gap-4 rounded-2xl border border-white/10 bg-card p-5 md:grid-cols-2">
          <div className="md:col-span-2">
            <h3 className="font-display text-xl text-white">Provider Connections</h3>
            <p className="text-sm text-fg-muted">URLs, credentials and log source for Tautulli + SFTPGo.</p>
          </div>

          <div>
            <label className={labelClass} htmlFor="tautulli-url">Tautulli URL</label>
            <input
              id="tautulli-url"
              className={inputClass}
              value={form.tautulliUrl}
              onChange={(event) => setForm({ ...form, tautulliUrl: event.target.value })}
            />
          </div>

          <div>
            <label className={labelClass} htmlFor="tautulli-api-key">Tautulli API Key</label>
            <input
              id="tautulli-api-key"
              type="password"
              className={inputClass}
              placeholder={
                settings.tautulli_api_key_set
                  ? `Configured (${settings.tautulli_api_key_masked ?? "hidden"}) - leave empty to keep`
                  : "Not configured"
              }
              value={form.tautulliApiKey}
              onChange={(event) => setForm({ ...form, tautulliApiKey: event.target.value })}
            />
          </div>

          <div>
            <label className={labelClass} htmlFor="sftpgo-url">SFTPGo URL</label>
            <input
              id="sftpgo-url"
              className={inputClass}
              value={form.sftpgoUrl}
              onChange={(event) => setForm({ ...form, sftpgoUrl: event.target.value })}
            />
          </div>

          <div>
            <label className={labelClass} htmlFor="sftpgo-token">SFTPGo Token / Credentials</label>
            <input
              id="sftpgo-token"
              type="password"
              className={inputClass}
              placeholder={
                settings.sftpgo_token_set
                  ? `Configured (${settings.sftpgo_token_masked ?? "hidden"}) - leave empty to keep`
                  : "Not configured"
              }
              value={form.sftpgoToken}
              onChange={(event) => setForm({ ...form, sftpgoToken: event.target.value })}
            />
          </div>

          <div className="md:col-span-2">
            <label className={labelClass} htmlFor="sftpgo-logs-path">SFTPGo Logs Path</label>
            <input
              id="sftpgo-logs-path"
              className={inputClass}
              value={form.sftpgoLogsPath}
              onChange={(event) => setForm({ ...form, sftpgoLogsPath: event.target.value })}
              placeholder="/srv/sftpgo/logs/transfers.json"
            />
          </div>

          <div className="md:col-span-2">
            <label className={labelClass} htmlFor="sftpgo-path-mappings">SFTPGo Path Mappings (one per line)</label>
            <textarea
              id="sftpgo-path-mappings"
              rows={4}
              className={inputClass}
              value={form.sftpgoPathMappings}
              onChange={(event) => setForm({ ...form, sftpgoPathMappings: event.target.value })}
              placeholder="/multimedia/peliculas:/peliculas&#10;/multimedia/series:/series"
            />
            <p className="mt-1 text-xs text-fg-muted">Format: source:target, source=target or source-&gt;target.</p>
          </div>
        </section>

        <section className="grid grid-cols-1 gap-4 rounded-2xl border border-white/10 bg-card p-5 md:grid-cols-2">
          <div className="md:col-span-2">
            <h3 className="font-display text-xl text-white">Behavior</h3>
            <p className="text-sm text-fg-muted">Polling frequency, timezone, poster strategy and retention.</p>
          </div>

          <div>
            <label className={labelClass} htmlFor="polling-frequency">Polling Frequency (seconds)</label>
            <input
              id="polling-frequency"
              type="number"
              min={5}
              className={inputClass}
              value={form.pollingFrequencySeconds}
              onChange={(event) => setForm({ ...form, pollingFrequencySeconds: event.target.value })}
            />
          </div>

          <div>
            <label className={labelClass} htmlFor="timezone">Timezone</label>
            <input
              id="timezone"
              className={inputClass}
              value={form.timezone}
              onChange={(event) => setForm({ ...form, timezone: event.target.value })}
              placeholder="Europe/Madrid"
            />
          </div>

          <div>
            <label className={labelClass} htmlFor="placeholder-path">Placeholder Path</label>
            <input
              id="placeholder-path"
              className={inputClass}
              value={form.placeholderPath}
              onChange={(event) => setForm({ ...form, placeholderPath: event.target.value })}
            />
          </div>

          <div>
            <label className={labelClass} htmlFor="history-retention">History Retention (days)</label>
            <input
              id="history-retention"
              type="number"
              min={1}
              className={inputClass}
              value={form.historyRetentionDays}
              onChange={(event) => setForm({ ...form, historyRetentionDays: event.target.value })}
            />
          </div>

          <div>
            <label className={labelClass} htmlFor="media-roots">Media Root Paths</label>
            <textarea
              id="media-roots"
              rows={5}
              className={inputClass}
              value={form.mediaRootPaths}
              onChange={(event) => setForm({ ...form, mediaRootPaths: event.target.value })}
              placeholder="/media/movies&#10;/media/series"
            />
          </div>

          <div>
            <label className={labelClass} htmlFor="poster-names">Preferred Poster Names</label>
            <textarea
              id="poster-names"
              rows={5}
              className={inputClass}
              value={form.preferredPosterNames}
              onChange={(event) => setForm({ ...form, preferredPosterNames: event.target.value })}
              placeholder="poster.jpg&#10;cover.jpg&#10;folder.jpg"
            />
          </div>
        </section>

        <section className="rounded-2xl border border-white/10 bg-card p-5">
          <h3 className="font-display text-xl text-white">User Aliases</h3>
          <p className="mb-3 text-sm text-fg-muted">Use one alias per line: <code className="text-fg">real_user=Display Name</code>.</p>
          <textarea
            rows={8}
            className={inputClass}
            value={form.userAliases}
            onChange={(event) => setForm({ ...form, userAliases: event.target.value })}
            placeholder="sil.g8=Sil\nalex_aalex93=Alex"
          />
        </section>

        <div className="flex items-center gap-3">
          <Button type="submit" disabled={saving}>
            {saving ? "Saving..." : "Save Settings"}
          </Button>
          <Button type="button" variant="outline" onClick={() => setForm(mapSettingsToForm(settings))}>
            Reset Changes
          </Button>
        </div>
      </form>
    </div>
  );
}
