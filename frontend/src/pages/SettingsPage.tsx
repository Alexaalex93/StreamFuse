import { FormEvent, useEffect, useMemo, useState } from "react";

import { apiGet, apiPut } from "@/shared/api/client";
import { Button } from "@/shared/ui/button";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { DetectedUserAliasOption, StreamFuseSettings, StreamFuseSettingsUpdate } from "@/types/settings";

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
  pollingFrequencySeconds: string;
  timezone: string;
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
    pollingFrequencySeconds: String(settings.polling_frequency_seconds),
    timezone: settings.timezone,
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
  const [settings, setSettings] = useState<StreamFuseSettings | null>(null);
  const [form, setForm] = useState<SettingsFormState | null>(null);
  const [detectedUsers, setDetectedUsers] = useState<DetectedUserAliasOption[]>([]);
  const [selectedDetectedUser, setSelectedDetectedUser] = useState("");
  const [aliasDraft, setAliasDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

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
      return "Not saved yet";
    }
    return new Date(settings.updated_at).toLocaleString();
  }, [settings]);

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
      polling_frequency_seconds: Number(form.pollingFrequencySeconds),
      timezone: form.timezone.trim(),
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
      setSettings(updated);
      setForm(mapSettingsToForm(updated));
      await loadDetectedUsers();
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

  const aliasEntries = Object.entries(form.userAliases).sort(([a], [b]) => a.localeCompare(b));

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
            <input id="tautulli-url" className={inputClass} value={form.tautulliUrl} onChange={(event) => setForm({ ...form, tautulliUrl: event.target.value })} />
          </div>

          <div>
            <label className={labelClass} htmlFor="tautulli-api-key">Tautulli API Key</label>
            <input
              id="tautulli-api-key"
              type="password"
              className={inputClass}
              placeholder={settings.tautulli_api_key_set ? `Configured (${settings.tautulli_api_key_masked ?? "hidden"}) - leave empty to keep` : "Not configured"}
              value={form.tautulliApiKey}
              onChange={(event) => setForm({ ...form, tautulliApiKey: event.target.value })}
            />
          </div>

          <div>
            <label className={labelClass} htmlFor="sftpgo-url">SFTPGo URL</label>
            <input id="sftpgo-url" className={inputClass} value={form.sftpgoUrl} onChange={(event) => setForm({ ...form, sftpgoUrl: event.target.value })} />
          </div>

          <div>
            <label className={labelClass} htmlFor="sftpgo-token">SFTPGo Token / Credentials</label>
            <input
              id="sftpgo-token"
              type="password"
              className={inputClass}
              placeholder={settings.sftpgo_token_set ? `Configured (${settings.sftpgo_token_masked ?? "hidden"}) - leave empty to keep` : "Not configured"}
              value={form.sftpgoToken}
              onChange={(event) => setForm({ ...form, sftpgoToken: event.target.value })}
            />
          </div>

          <div className="md:col-span-2">
            <label className={labelClass} htmlFor="sftpgo-logs-path">SFTPGo Logs Path</label>
            <input id="sftpgo-logs-path" className={inputClass} value={form.sftpgoLogsPath} onChange={(event) => setForm({ ...form, sftpgoLogsPath: event.target.value })} placeholder="/srv/sftpgo/logs/transfers.json" />
          </div>

          <div className="md:col-span-2">
            <label className={labelClass} htmlFor="sftpgo-path-mappings">SFTPGo Path Mappings (one per line)</label>
            <textarea id="sftpgo-path-mappings" rows={4} className={inputClass} value={form.sftpgoPathMappings} onChange={(event) => setForm({ ...form, sftpgoPathMappings: event.target.value })} placeholder="/multimedia/peliculas:/peliculas&#10;/multimedia/series:/series" />
          </div>
        </section>

        <section className="grid grid-cols-1 gap-4 rounded-2xl border border-white/10 bg-card p-5 md:grid-cols-2">
          <div className="md:col-span-2">
            <h3 className="font-display text-xl text-white">Samba</h3>
            <p className="text-sm text-fg-muted">Import active SMB downloads from smbstatus JSON snapshots.</p>
          </div>

          <div className="md:col-span-2 flex items-center gap-3 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
            <input id="samba-enabled" type="checkbox" checked={form.sambaEnabled} onChange={(event) => setForm({ ...form, sambaEnabled: event.target.checked })} />
            <label htmlFor="samba-enabled" className="text-sm text-fg">Enable Samba ingestion</label>
          </div>

          <div className="md:col-span-2">
            <label className={labelClass} htmlFor="samba-status-json">Samba Status JSON Path</label>
            <input id="samba-status-json" className={inputClass} value={form.sambaStatusJsonPath} onChange={(event) => setForm({ ...form, sambaStatusJsonPath: event.target.value })} placeholder="/data/samba-status-sample.json" />
          </div>

          <div className="md:col-span-2">
            <label className={labelClass} htmlFor="samba-path-mappings">Samba Path Mappings (one per line)</label>
            <textarea id="samba-path-mappings" rows={4} className={inputClass} value={form.sambaPathMappings} onChange={(event) => setForm({ ...form, sambaPathMappings: event.target.value })} placeholder="/multimedia/peliculas:/peliculas&#10;/multimedia/series:/series" />
          </div>
        </section>

        <section className="grid grid-cols-1 gap-4 rounded-2xl border border-white/10 bg-card p-5 md:grid-cols-2">
          <div className="md:col-span-2">
            <h3 className="font-display text-xl text-white">Behavior</h3>
          </div>

          <div>
            <label className={labelClass} htmlFor="polling-frequency">Polling Frequency (seconds)</label>
            <input id="polling-frequency" type="number" min={5} className={inputClass} value={form.pollingFrequencySeconds} onChange={(event) => setForm({ ...form, pollingFrequencySeconds: event.target.value })} />
          </div>

          <div>
            <label className={labelClass} htmlFor="timezone">Timezone</label>
            <input id="timezone" className={inputClass} value={form.timezone} onChange={(event) => setForm({ ...form, timezone: event.target.value })} placeholder="Europe/Madrid" />
          </div>

          <div>
            <label className={labelClass} htmlFor="placeholder-path">Placeholder Path</label>
            <input id="placeholder-path" className={inputClass} value={form.placeholderPath} onChange={(event) => setForm({ ...form, placeholderPath: event.target.value })} />
          </div>

          <div>
            <label className={labelClass} htmlFor="history-retention">History Retention (days)</label>
            <input id="history-retention" type="number" min={1} className={inputClass} value={form.historyRetentionDays} onChange={(event) => setForm({ ...form, historyRetentionDays: event.target.value })} />
          </div>

          <div>
            <label className={labelClass} htmlFor="media-roots">Media Root Paths</label>
            <textarea id="media-roots" rows={5} className={inputClass} value={form.mediaRootPaths} onChange={(event) => setForm({ ...form, mediaRootPaths: event.target.value })} placeholder="/media/movies&#10;/media/series" />
          </div>

          <div>
            <label className={labelClass} htmlFor="poster-names">Preferred Poster Names</label>
            <textarea id="poster-names" rows={5} className={inputClass} value={form.preferredPosterNames} onChange={(event) => setForm({ ...form, preferredPosterNames: event.target.value })} placeholder="poster.jpg&#10;cover.jpg&#10;folder.jpg" />
          </div>
        </section>

        <section className="rounded-2xl border border-white/10 bg-card p-5 space-y-4">
          <div>
            <h3 className="font-display text-xl text-white">User Aliases</h3>
            <p className="text-sm text-fg-muted">Select a detected user and assign the display name to show across Dashboard and History.</p>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-[2fr_2fr_auto] md:items-end">
            <div>
              <label className={labelClass} htmlFor="detected-user">Detected user</label>
              <select
                id="detected-user"
                className={selectClass}
                value={selectedDetectedUser}
                onChange={(event) => setSelectedDetectedUser(event.target.value)}
              >
                {detectedUsers.length === 0 ? <option value="" style={selectOptionStyle}>No users detected yet</option> : null}
                {detectedUsers.map((user) => (
                  <option key={user.user_name} value={user.user_name} style={selectOptionStyle}>
                    {user.user_name} ({user.session_count})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className={labelClass} htmlFor="alias-input">Alias</label>
              <input
                id="alias-input"
                className={inputClass}
                value={aliasDraft}
                onChange={(event) => setAliasDraft(event.target.value)}
                placeholder="Display name"
              />
            </div>

            <Button type="button" variant="outline" onClick={onApplyAliasDraft} disabled={!selectedDetectedUser}>
              Set Alias
            </Button>
          </div>

          {selectedDetectedUserMeta ? (
            <p className="text-xs text-fg-muted">
              Sources: {selectedDetectedUserMeta.sources.join(", ") || "n/a"}
              {" | "}
              Sessions: {selectedDetectedUserMeta.session_count}
              {selectedDetectedUserMeta.alias ? ` | Current alias: ${selectedDetectedUserMeta.alias}` : ""}
            </p>
          ) : null}

          <div className="space-y-2">
            {aliasEntries.length === 0 ? <p className="text-sm text-fg-muted">No aliases configured.</p> : null}
            {aliasEntries.map(([source, alias]) => (
              <div key={source} className="grid grid-cols-1 gap-2 rounded-lg border border-white/10 bg-white/[0.02] p-3 md:grid-cols-[2fr_2fr_auto] md:items-center">
                <p className="text-sm text-fg">{source}</p>
                <input
                  className={inputClass}
                  value={alias}
                  onChange={(event) => setForm({ ...form, userAliases: { ...form.userAliases, [source]: event.target.value } })}
                />
                <Button type="button" variant="ghost" onClick={() => onDeleteAlias(source)}>
                  Remove
                </Button>
              </div>
            ))}
          </div>
        </section>

        <div className="flex items-center gap-3">
          <Button type="submit" disabled={saving}>{saving ? "Saving..." : "Save Settings"}</Button>
          <Button type="button" variant="outline" onClick={() => setForm(mapSettingsToForm(settings))}>Reset Changes</Button>
        </div>
      </form>
    </div>
  );
}
