import { useEffect, useMemo, useRef, useState } from "react";

const DASH_TEXT = {
  es: {
    pageTitle: "Dashboard",
    pageSubtitle: "Monitorizacion en directo de sesiones activas y actividad reciente.",
    sysHealth: "Estado del Sistema",
    sysHealthSub: "Metricas en directo del snapshot de Unraid (CPU/GPU/RAM/Red/Energia).",
    sysDisabled: "Activa las metricas de Unraid en Ajustes para ver la telemetria del host.",
    sysWaiting: "Esperando el archivo JSON de metricas de Unraid.",
    cpu: "CPU",
    gpu: "GPU",
    ramUsed: "RAM Usada",
    outbound: "Saliente",
    networkOut: "Red saliente",
    powerMonth: "Potencia / Mes",
    networkRealtime: "Trafico de red (tiempo real)",
    activeSessions: "Sesiones activas",
    activeUsers: "Usuarios activos",
    tautulliSessions: "Sesiones Tautulli",
    sftpgoSessions: "Sesiones SFTPGo",
    sambaSessions: "Sesiones Samba",
    totalShared: "Total compartido",
    liveRightNow: "En directo ahora",
    uniqueUsers: "Usuarios unicos",
    playbackSessions: "Sesiones de reproduccion",
    transferSessions: "Sesiones de transferencia",
    smbSessions: "Sesiones SMB",
    cumulativeTransferred: "Transferido acumulado",
    activeGrid: "Sesiones activas",
    activeGridSub: "Actividad actual de Tautulli, SFTPGo y Samba, unificada.",
    refreshed: "Actualizado",
    waiting: "Esperando...",
    loadingSessions: "Cargando sesiones activas",
    noActiveSessions: "Sin sesiones activas",
    noActiveDesc: "Prueba a limpiar los filtros o espera nueva actividad.",
    recentActivity: "Actividad reciente",
    recentActivitySub: "Ultimas sesiones finalizadas para diagnostico rapido.",
    noRecentActivity: "Sin actividad reciente",
    noRecentDesc: "El historial aparecera cuando las sesiones finalicen.",
    outboundLabel: "Saliente",
    inboundLabel: "Entrante",
  },
  en: {
    pageTitle: "Dashboard",
    pageSubtitle: "Live monitoring of active sessions and recent activity.",
    sysHealth: "System Health",
    sysHealthSub: "Live metrics from Unraid snapshot (CPU/GPU/RAM/Network/Energy).",
    sysDisabled: "Enable Unraid metrics in Settings to show host telemetry.",
    sysWaiting: "Waiting for Unraid metrics JSON file.",
    cpu: "CPU",
    gpu: "GPU",
    ramUsed: "RAM Used",
    outbound: "Outbound",
    networkOut: "Network out",
    powerMonth: "Power / Month",
    networkRealtime: "Network traffic (real-time)",
    activeSessions: "Active Sessions",
    activeUsers: "Active Users",
    tautulliSessions: "Tautulli Sessions",
    sftpgoSessions: "SFTPGo Sessions",
    sambaSessions: "Samba Sessions",
    totalShared: "Total Shared",
    liveRightNow: "Live right now",
    uniqueUsers: "Unique users",
    playbackSessions: "Playback sessions",
    transferSessions: "Transfer sessions",
    smbSessions: "SMB sessions",
    cumulativeTransferred: "Cumulative transferred",
    activeGrid: "Active Sessions Grid",
    activeGridSub: "All current activity from Tautulli, SFTPGo and Samba, unified.",
    refreshed: "Refreshed",
    waiting: "Waiting...",
    loadingSessions: "Loading active sessions",
    noActiveSessions: "No active sessions",
    noActiveDesc: "Try clearing filters or wait for new activity.",
    recentActivity: "Recent Activity",
    recentActivitySub: "Latest ended or stale sessions for rapid troubleshooting.",
    noRecentActivity: "No recent activity",
    noRecentDesc: "History will appear as sessions complete.",
    outboundLabel: "Outbound",
    inboundLabel: "Inbound",
  },
} as const;

import { MediaType, StreamSource } from "@/types/domain";
import { UnifiedSession } from "@/types/session";
import { OverviewStats } from "@/types/stats";
import { SystemMetricsResponse } from "@/types/system";

import { apiGet, apiGetWithFallback } from "@/shared/api/client";
import { relativeFromNow } from "@/shared/lib/date";
import { getStoredLanguage, UiLanguage } from "@/shared/lib/i18n";
import { SourceBadge } from "@/shared/ui/badges/SourceBadge";
import { StatCard } from "@/shared/ui/cards/StatCard";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";

import { FilterPanel } from "@/features/sessions/components/FilterPanel";
import { MediaDetailsDrawer } from "@/features/sessions/components/MediaDetailsDrawer";
import { SessionCard } from "@/features/sessions/components/SessionCard";


function formatBytes(value: number | null | undefined): string {
  if (!value || value <= 0) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB", "TB", "PB"];
  let current = value;
  let idx = 0;
  while (current >= 1024 && idx < units.length - 1) {
    current /= 1024;
    idx += 1;
  }
  return idx === 0 ? `${Math.round(current)} ${units[idx]}` : `${current.toFixed(1)} ${units[idx]}`;
}

function formatMoney(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) {
    return "n/a";
  }
  return `${value.toFixed(2)} EUR`;
}

function formatPercent(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) {
    return "n/a";
  }
  return `${value.toFixed(1)}%`;
}

function formatTrafficRate(bps: number): string {
  if (!Number.isFinite(bps) || bps <= 0) {
    return "0 kbps";
  }
  const kbps = bps / 1000;
  if (kbps < 1000) {
    return `${kbps.toFixed(1)} kbps`;
  }
  return `${(kbps / 1000).toFixed(2)} Mbps`;
}

function smoothSeries(values: number[]): number[] {
  if (values.length < 3) {
    return values;
  }

  const weighted = values.map((value, index) => {
    const prev = values[index - 1] ?? value;
    const next = values[index + 1] ?? value;
    return prev * 0.2 + value * 0.6 + next * 0.2;
  });

  const out: number[] = [];
  let ema = weighted[0];
  const alpha = 0.35;
  for (const value of weighted) {
    ema = ema + alpha * (value - ema);
    out.push(ema);
  }
  return out;
}

function buildSmoothPath(values: number[], maxValue: number): string {
  if (values.length === 0) {
    return "";
  }
  if (values.length === 1) {
    return "M50,50";
  }

  const points = values.map((value, index) => ({
    x: (index / (values.length - 1)) * 100,
    y: 100 - (Math.max(0, value) / maxValue) * 100,
  }));

  let d = `M${points[0].x.toFixed(2)},${points[0].y.toFixed(2)}`;
  for (let i = 0; i < points.length - 1; i += 1) {
    const p0 = points[i - 1] ?? points[i];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2] ?? p2;

    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;

    d += ` C${cp1x.toFixed(2)},${cp1y.toFixed(2)} ${cp2x.toFixed(2)},${cp2y.toFixed(2)} ${p2.x.toFixed(2)},${p2.y.toFixed(2)}`;
  }

  return d;
}

function NetworkTrafficChart({
  inboundPoints,
  outboundPoints,
  inboundLegendBps,
  outboundLegendBps,
  maxDisplayBps,
  maxLabelBps,
  outboundLabel,
  inboundLabel,
}: {
  inboundPoints: number[];
  outboundPoints: number[];
  inboundLegendBps: number;
  outboundLegendBps: number;
  maxDisplayBps: number;
  maxLabelBps: number;
  outboundLabel: string;
  inboundLabel: string;
}) {
  const len = Math.max(inboundPoints.length, outboundPoints.length);
  if (len < 2) {
    return <div className="h-28 w-full rounded-xl border border-white/10 bg-white/[0.02]" />;
  }

  const inSeriesRaw =
    inboundPoints.length === len ? inboundPoints : [...Array(len - inboundPoints.length).fill(0), ...inboundPoints];
  const outSeriesRaw =
    outboundPoints.length === len ? outboundPoints : [...Array(len - outboundPoints.length).fill(0), ...outboundPoints];

  const inSeries = smoothSeries(inSeriesRaw);
  const outSeries = smoothSeries(outSeriesRaw);
  const liveSeriesPeak = Math.max(1, ...inSeriesRaw, ...outSeriesRaw) * 1.06;
  const maxValue = Math.max(1, maxDisplayBps, liveSeriesPeak);

  const outboundPath = buildSmoothPath(outSeries, maxValue);

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
      <div className="mb-2 flex flex-wrap items-center gap-5 text-xs">
        <span className="text-amber-400">↑ {outboundLabel} {formatTrafficRate(outboundLegendBps)}</span>
        {inboundLegendBps > 0 ? <span className="text-cyan-400">↓ {inboundLabel} {formatTrafficRate(inboundLegendBps)}</span> : null}
      </div>
      <div className="relative">
        <span className="absolute right-0 top-0 text-[11px] text-fg-muted">{formatTrafficRate(maxLabelBps)}</span>
        <svg viewBox="0 0 100 100" className="h-28 w-full" preserveAspectRatio="none">
          <g className="stroke-white/15" strokeWidth="0.35">
            <line x1="0" y1="20" x2="100" y2="20" />
            <line x1="0" y1="40" x2="100" y2="40" />
            <line x1="0" y1="60" x2="100" y2="60" />
            <line x1="0" y1="80" x2="100" y2="80" />
          </g>
          {inboundPoints.length >= 2 ? (
            <path
              d={buildSmoothPath(smoothSeries(inboundPoints.length === len ? inboundPoints : [...Array(len - inboundPoints.length).fill(0), ...inboundPoints]), maxValue)}
              className="fill-none stroke-cyan-400"
              strokeWidth="0.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray="2 1.5"
              vectorEffect="non-scaling-stroke"
            />
          ) : null}
          <path
            d={outboundPath}
            className="fill-none stroke-amber-400"
            strokeWidth="1"
            strokeLinecap="round"
            strokeLinejoin="round"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
      </div>
      <div className="mt-1 flex items-center justify-start text-[11px] text-fg-muted">
        <span>0 kbps</span>
      </div>
    </div>
  );
}

function buildQuery(params: Record<string, string | undefined>): string {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value && value.trim().length > 0) {
      query.set(key, value);
    }
  });
  const text = query.toString();
  return text ? `?${text}` : "";
}

function normalizeIpAddress(ip: string | null): string {
  if (!ip) {
    return "";
  }

  const trimmed = ip.trim();
  const bracket = /^\[(.*)](?::\d+)?$/.exec(trimmed);
  if (bracket) {
    return bracket[1];
  }

  const parts = trimmed.split(":");
  if (parts.length === 2 && /^\d+$/.test(parts[1])) {
    return parts[0];
  }

  return trimmed;
}

function dedupeTransferSessions(sessions: UnifiedSession[]): UnifiedSession[] {
  const byKey = new Map<string, UnifiedSession>();

  for (const session of sessions) {
    if (session.source !== "sftpgo" && session.source !== "samba") {
      byKey.set(`${session.source}-${session.source_session_id}`, session);
      continue;
    }

    const filePath = (session.file_path || "").trim().toLowerCase();
    const ip = normalizeIpAddress(session.ip_address).toLowerCase();
    const user = (session.user_name || "").trim().toLowerCase();

    if (!filePath || !ip || !user) {
      byKey.set(`${session.source}-${session.source_session_id}`, session);
      continue;
    }

    const key = `${session.source}-${user}-${ip}-${filePath}`;
    const existing = byKey.get(key);
    if (!existing) {
      byKey.set(key, session);
      continue;
    }

    const existingTs = Date.parse(existing.updated_at || "") || 0;
    const currentTs = Date.parse(session.updated_at || "") || 0;

    if (currentTs > existingTs) {
      byKey.set(key, session);
      continue;
    }

    if (currentTs === existingTs && (session.bandwidth_bps || 0) > (existing.bandwidth_bps || 0)) {
      byKey.set(key, session);
    }
  }

  return Array.from(byKey.values());
}

function buildStableSessionKey(session: UnifiedSession): string {
  if (session.source === "sftpgo" || session.source === "samba") {
    const filePath = (session.file_path || "").trim().toLowerCase();
    const ip = normalizeIpAddress(session.ip_address).toLowerCase();
    const user = (session.user_name || "").trim().toLowerCase();
    if (filePath && ip && user) {
      return `${session.source}-${user}-${ip}-${filePath}`;
    }
  }

  return `${session.source}-${session.source_session_id}`;
}

export function DashboardPage() {
  const [lang, setLang] = useState<UiLanguage>(getStoredLanguage());
  useEffect(() => {
    const handler = (e: Event) => setLang((e as CustomEvent<{ language: UiLanguage }>).detail.language);
    window.addEventListener("streamfuse:language-changed", handler);
    return () => window.removeEventListener("streamfuse:language-changed", handler);
  }, []);
  const tx = DASH_TEXT[lang];

  const [activeSessions, setActiveSessions] = useState<UnifiedSession[]>([]);
  const [recentSessions, setRecentSessions] = useState<UnifiedSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<UnifiedSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [totalSharedBytes, setTotalSharedBytes] = useState<number>(0);
  const [systemMetrics, setSystemMetrics] = useState<SystemMetricsResponse | null>(null);
  const [inboundSeries, setInboundSeries] = useState<number[]>([]);
  const [outboundSeries, setOutboundSeries] = useState<number[]>([]);
  const [targetInboundBps, setTargetInboundBps] = useState<number>(0);
  const [targetOutboundBps, setTargetOutboundBps] = useState<number>(0);
  const [displayInboundBps, setDisplayInboundBps] = useState<number>(0);
  const [displayOutboundBps, setDisplayOutboundBps] = useState<number>(0);
  const [chartMaxBps, setChartMaxBps] = useState<number>(1);
  const [maxLabelBps, setMaxLabelBps] = useState<number>(1);

  const [userQuery, setUserQuery] = useState("");
  const [sourceFilter, setSourceFilter] = useState<"all" | StreamSource>("all");
  const [mediaTypeFilter, setMediaTypeFilter] = useState<"all" | MediaType>("all");

  const orderBySessionRef = useRef<Map<string, number>>(new Map());
  const liveInboundRef = useRef<number>(0);
  const liveOutboundRef = useRef<number>(0);
  const nextOrderIndexRef = useRef(0);

  const orderActiveSessionsStable = (sessions: UnifiedSession[]): UnifiedSession[] => {
    for (const session of sessions) {
      const sessionKey = buildStableSessionKey(session);
      if (!orderBySessionRef.current.has(sessionKey)) {
        orderBySessionRef.current.set(sessionKey, nextOrderIndexRef.current);
        nextOrderIndexRef.current += 1;
      }
    }

    return [...sessions].sort((a, b) => {
      const keyA = buildStableSessionKey(a);
      const keyB = buildStableSessionKey(b);
      const orderA = orderBySessionRef.current.get(keyA) ?? Number.MAX_SAFE_INTEGER;
      const orderB = orderBySessionRef.current.get(keyB) ?? Number.MAX_SAFE_INTEGER;
      if (orderA !== orderB) {
        return orderA - orderB;
      }

      return keyA.localeCompare(keyB);
    });
  };

  const clearFilters = () => {
    setUserQuery("");
    setSourceFilter("all");
    setMediaTypeFilter("all");
  };

  const fetchData = async () => {
    try {
      setError(null);
      const activeQuery = buildQuery({
        user_name: userQuery || undefined,
        source: sourceFilter === "all" ? undefined : sourceFilter,
        media_type: mediaTypeFilter === "all" ? undefined : mediaTypeFilter,
        limit: "120",
      });

      const activeData = await apiGetWithFallback<UnifiedSession[]>([`/sessions/active${activeQuery}`, `/api/sessions/active${activeQuery}`]);
      const historyData = await apiGetWithFallback<UnifiedSession[]>(["/sessions/history?limit=8", "/api/sessions/history?limit=8"]);
      const overviewData = await apiGetWithFallback<OverviewStats>(["/stats/overview", "/api/stats/overview"]);

      let systemData: SystemMetricsResponse | null = null;
      try {
        systemData = await apiGet<SystemMetricsResponse>("/system/metrics");
      } catch {
        systemData = null;
      }

      const dedupedActive = dedupeTransferSessions(activeData);
      const stableActive = orderActiveSessionsStable(dedupedActive);

      setActiveSessions(stableActive);
      setRecentSessions(historyData);
      setSystemMetrics(systemData);
      const overviewSharedBytes = overviewData.total_shared_bytes ?? 0;
      const unraidSharedBytes = systemData?.transfer?.total_shared_bytes ?? 0;
      const bestSharedBytes = Math.max(overviewSharedBytes, unraidSharedBytes);
      setTotalSharedBytes((prev) => Math.max(prev, bestSharedBytes));
      const inBps = systemData?.network?.inbound_bps ?? 0;
      const outBps = systemData?.network?.outbound_bps ?? 0;
      setTargetInboundBps(inBps);
      setTargetOutboundBps(outBps);
      setDisplayInboundBps(inBps);
      setDisplayOutboundBps(outBps);
      setMaxLabelBps(Math.max(1, inBps, outBps) * 1.12);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    void fetchData();
  }, [userQuery, sourceFilter, mediaTypeFilter]);

  useEffect(() => {
    const id = window.setInterval(() => {
      void fetchData();
    }, 1000);

    return () => {
      window.clearInterval(id);
    };
  }, [userQuery, sourceFilter, mediaTypeFilter]);

  useEffect(() => {
    const onRefresh = () => {
      void fetchData();
    };
    const onNewFilter = () => {
      clearFilters();
    };

    window.addEventListener("streamfuse:refresh", onRefresh);
    window.addEventListener("streamfuse:new-filter", onNewFilter);
    return () => {
      window.removeEventListener("streamfuse:refresh", onRefresh);
      window.removeEventListener("streamfuse:new-filter", onNewFilter);
    };
  }, [userQuery, sourceFilter, mediaTypeFilter]);

  useEffect(() => {
    const id = window.setInterval(() => {
      setInboundSeries((prev) => {
        const series = prev.length ? prev : [targetInboundBps];
        const last = series[series.length - 1] ?? targetInboundBps;
        const next = last + (targetInboundBps - last) * 0.09;
        liveInboundRef.current = next;
        return [...series.slice(-299), next];
      });
      setOutboundSeries((prev) => {
        const series = prev.length ? prev : [targetOutboundBps];
        const last = series[series.length - 1] ?? targetOutboundBps;
        const next = last + (targetOutboundBps - last) * 0.09;
        liveOutboundRef.current = next;
        return [...series.slice(-299), next];
      });
      setChartMaxBps((prev) => {
        const livePeak = Math.max(1, liveInboundRef.current, liveOutboundRef.current) * 1.1;
        if (livePeak > prev * 0.98) {
          return livePeak;
        }
        return prev + (livePeak - prev) * 0.03;
      });
    }, 60);

    return () => {
      window.clearInterval(id);
    };
  }, [targetInboundBps, targetOutboundBps]);
  const derived = useMemo(() => {
    const sessionsActive = activeSessions.length;
    const usersActive = new Set(activeSessions.map((session) => session.user_name)).size;
    const sessionsBandwidth = activeSessions.reduce((sum, session) => sum + (session.bandwidth_bps ?? 0), 0);
    const totalBandwidth = Math.round(systemMetrics?.transfer?.total_bandwidth_bps ?? sessionsBandwidth);
    const tautulliCount = activeSessions.filter((session) => session.source === "tautulli").length;
    const sftpgoCount = activeSessions.filter((session) => session.source === "sftpgo").length;
    const sambaCount = activeSessions.filter((session) => session.source === "samba").length;

    return {
      sessionsActive,
      usersActive,
      totalBandwidth,
      tautulliCount,
      sftpgoCount,
      sambaCount,
    };
    }, [activeSessions, systemMetrics]);

  const relatedSessions = useMemo(() => {
    if (!selectedSession) {
      return [];
    }

    const pool = [...activeSessions, ...recentSessions];
    return pool.filter((candidate) => {
      if (candidate.id === selectedSession.id) {
        return false;
      }
      return (
        candidate.user_name === selectedSession.user_name ||
        (!!candidate.title_clean && candidate.title_clean === selectedSession.title_clean)
      );
    });
  }, [selectedSession, activeSessions, recentSessions]);

  return (
    <>
      <div className="space-y-6 min-h-[760px]">
        <header className="min-h-[72px]">
          <h2 className="font-display text-3xl text-white">{tx.pageTitle}</h2>
          <p className="text-sm text-fg-muted">{tx.pageSubtitle}</p>
        </header>

        <section className="rounded-2xl border border-white/10 bg-card p-5 shadow-premium">
          <div className="mb-4">
            <h2 className="font-display text-2xl text-white">{tx.sysHealth}</h2>
            <p className="text-sm text-fg-muted">{tx.sysHealthSub}</p>
          </div>

          {!systemMetrics?.enabled ? (
            <p className="text-sm text-fg-muted">{tx.sysDisabled}</p>
          ) : !systemMetrics?.source_available ? (
            <p className="text-sm text-fg-muted">{tx.sysWaiting}</p>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
                <StatCard label={tx.cpu} value={formatPercent(systemMetrics.load.cpu_percent)} hint={systemMetrics.identity.cpu_model || "n/a"} />
                <StatCard label={tx.gpu} value={formatPercent(systemMetrics.load.gpu_percent)} hint={systemMetrics.identity.gpu_model || "n/a"} />
                <StatCard label={tx.ramUsed} value={formatBytes(systemMetrics.load.ram_used_bytes)} hint={`Free ${formatBytes(systemMetrics.load.ram_free_bytes)}`} />
                <StatCard label={tx.outbound} value={formatTrafficRate(systemMetrics.network.outbound_bps ?? 0)} hint={tx.networkOut} />
                <StatCard label={tx.powerMonth} value={`${(systemMetrics.energy.power_watts ?? 0).toFixed(0)} W`} hint={formatMoney(systemMetrics.energy.estimated_month_cost_eur)} />
              </div>

              <div>
                <p className="mb-2 text-xs uppercase tracking-[0.12em] text-fg-muted">{tx.networkRealtime}</p>
                <NetworkTrafficChart inboundPoints={inboundSeries} outboundPoints={outboundSeries} inboundLegendBps={displayInboundBps} outboundLegendBps={displayOutboundBps} maxDisplayBps={chartMaxBps} maxLabelBps={maxLabelBps} outboundLabel={tx.outboundLabel} inboundLabel={tx.inboundLabel} />
              </div>
            </div>
          )}
        </section>
        <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-6">
          <StatCard label={tx.activeSessions} value={String(derived.sessionsActive)} hint={tx.liveRightNow} />
          <StatCard label={tx.activeUsers} value={String(derived.usersActive)} hint={tx.uniqueUsers} />
          <StatCard label={tx.tautulliSessions} value={String(derived.tautulliCount)} hint={tx.playbackSessions} />
          <StatCard label={tx.sftpgoSessions} value={String(derived.sftpgoCount)} hint={tx.transferSessions} />
          <StatCard label={tx.sambaSessions} value={String(derived.sambaCount)} hint={tx.smbSessions} />
          <StatCard label={tx.totalShared} value={formatBytes(totalSharedBytes)} hint={tx.cumulativeTransferred} />
        </section>

        <FilterPanel
          userQuery={userQuery}
          source={sourceFilter}
          mediaType={mediaTypeFilter}
          onUserQueryChange={setUserQuery}
          onSourceChange={setSourceFilter}
          onMediaTypeChange={setMediaTypeFilter}
          onClear={clearFilters}
        />

        <section className="rounded-2xl border border-white/10 bg-card p-5 shadow-premium">
          <div className="mb-4 flex items-center justify-between gap-4">
            <div>
              <h2 className="font-display text-2xl text-white">{tx.activeGrid}</h2>
              <p className="text-sm text-fg-muted">{tx.activeGridSub}</p>
            </div>
            <p className="text-xs uppercase tracking-[0.14em] text-fg-muted">
              {lastUpdated ? `${tx.refreshed} ${relativeFromNow(lastUpdated.toISOString())}` : tx.waiting}
            </p>
          </div>

          {loading ? <LoadingState title={tx.loadingSessions} /> : null}
          {!loading && error ? <ErrorState description={error} /> : null}
          {!loading && !error && activeSessions.length === 0 ? (
            <EmptyState title={tx.noActiveSessions} description={tx.noActiveDesc} />
          ) : null}

          {!loading && !error && activeSessions.length > 0 ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {activeSessions.map((session) => (
                <SessionCard
                  key={`${session.source}-${session.source_session_id}`}
                  session={session}
                  onOpen={setSelectedSession}
                />
              ))}
            </div>
          ) : null}
        </section>

        <section className="rounded-2xl border border-white/10 bg-card p-5 shadow-premium">
          <div className="mb-4">
            <h2 className="font-display text-2xl text-white">{tx.recentActivity}</h2>
            <p className="text-sm text-fg-muted">{tx.recentActivitySub}</p>
          </div>

          {recentSessions.length === 0 ? (
            <EmptyState title={tx.noRecentActivity} description={tx.noRecentDesc} />
          ) : (
            <div className="space-y-2">
              {recentSessions.map((session) => (
                <button
                  type="button"
                  key={`recent-${session.source}-${session.source_session_id}`}
                  onClick={() => setSelectedSession(session)}
                  className="flex w-full items-center justify-between rounded-xl border border-white/10 bg-white/[0.02] px-3 py-2 text-left transition hover:bg-white/[0.04]"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium text-white">{session.title || session.file_name || "Untitled"}</p>
                    <p className="text-xs text-fg-muted">
                      {session.user_name} - {session.ip_address || "n/a"}
                    </p>
                  </div>
                  <div className="grid w-[124px] justify-items-center gap-1">
                    <SourceBadge source={session.source} />
                    <span className="text-xs text-fg-muted text-center">{relativeFromNow(session.updated_at)}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </section>
      </div>

      <MediaDetailsDrawer
        open={selectedSession !== null}
        session={selectedSession}
        relatedSessions={relatedSessions}
        onClose={() => setSelectedSession(null)}
      />
    </>
  );
}





























