import { useEffect, useMemo, useState } from "react";

import { MediaType, StreamSource } from "@/types/domain";
import { UnifiedSession } from "@/types/session";
import { OverviewStats } from "@/types/stats";

import { getBackendBase } from "@/shared/api/client";
import { relativeFromNow } from "@/shared/lib/date";
import { SourceBadge } from "@/shared/ui/badges/SourceBadge";
import { StatCard } from "@/shared/ui/cards/StatCard";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";

import { FilterPanel } from "@/features/sessions/components/FilterPanel";
import { MediaDetailsDrawer } from "@/features/sessions/components/MediaDetailsDrawer";
import { SessionCard } from "@/features/sessions/components/SessionCard";

function formatBandwidth(totalBps: number): string {
  const mbps = totalBps / 1_000_000;
  if (mbps < 1000) {
    return `${mbps.toFixed(1)} Mbps`;
  }
  return `${(mbps / 1000).toFixed(2)} Gbps`;
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

function dedupeSftpgoSessions(sessions: UnifiedSession[]): UnifiedSession[] {
  const byKey = new Map<string, UnifiedSession>();

  for (const session of sessions) {
    if (session.source !== "sftpgo") {
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

    const key = `sftpgo-${user}-${ip}-${filePath}`;
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

export function DashboardPage() {
  const [activeSessions, setActiveSessions] = useState<UnifiedSession[]>([]);
  const [recentSessions, setRecentSessions] = useState<UnifiedSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<UnifiedSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [totalSharedHuman, setTotalSharedHuman] = useState<string>("0 B");

  const [userQuery, setUserQuery] = useState("");
  const [sourceFilter, setSourceFilter] = useState<"all" | StreamSource>("all");
  const [mediaTypeFilter, setMediaTypeFilter] = useState<"all" | MediaType>("all");
  const fetchData = async () => {
    try {
      setError(null);
      const backend = getBackendBase();
      const activeQuery = buildQuery({
        user_name: userQuery || undefined,
        source: sourceFilter === "all" ? undefined : sourceFilter,
        media_type: mediaTypeFilter === "all" ? undefined : mediaTypeFilter,
        limit: "120",
      });

      const activeResponse = await fetch(`${backend}/api/sessions/active${activeQuery}`);
      if (!activeResponse.ok) {
        throw new Error(`Active sessions failed (${activeResponse.status})`);
      }
      const activeData = (await activeResponse.json()) as UnifiedSession[];

      const historyResponse = await fetch(`${backend}/api/sessions/history?limit=8`);
      const overviewResponse = await fetch(`${backend}/api/stats/overview`);
      if (!historyResponse.ok) {
        throw new Error(`History failed (${historyResponse.status})`);
      }
      if (!overviewResponse.ok) {
        throw new Error(`Stats overview failed (${overviewResponse.status})`);
      }
      const historyData = (await historyResponse.json()) as UnifiedSession[];
      const overviewData = (await overviewResponse.json()) as OverviewStats;

      const dedupedActive = dedupeSftpgoSessions(activeData);

      setActiveSessions(dedupedActive);
      setRecentSessions(historyData);
      setTotalSharedHuman(overviewData.total_shared_human || "0 B");
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

  const derived = useMemo(() => {
    const sessionsActive = activeSessions.length;
    const usersActive = new Set(activeSessions.map((session) => session.user_name)).size;
    const totalBandwidth = activeSessions.reduce((sum, session) => sum + (session.bandwidth_bps ?? 0), 0);
    const tautulliCount = activeSessions.filter((session) => session.source === "tautulli").length;
    const sftpgoCount = activeSessions.filter((session) => session.source === "sftpgo").length;

    return {
      sessionsActive,
      usersActive,
      totalBandwidth,
      tautulliCount,
      sftpgoCount,
    };
  }, [activeSessions]);

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
        <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-6">
          <StatCard label="Active Sessions" value={String(derived.sessionsActive)} hint="Live right now" />
          <StatCard label="Active Users" value={String(derived.usersActive)} hint="Unique users" />
          <StatCard label="Total Bandwidth" value={formatBandwidth(derived.totalBandwidth)} hint="Aggregated live" />
          <StatCard label="Tautulli Sessions" value={String(derived.tautulliCount)} hint="Playback sessions" />
          <StatCard label="SFTPGo Sessions" value={String(derived.sftpgoCount)} hint="Transfer sessions" />
          <StatCard label="Total Shared" value={totalSharedHuman} hint="Cumulative transferred" />
        </section>

        <FilterPanel
          userQuery={userQuery}
          source={sourceFilter}
          mediaType={mediaTypeFilter}
          onUserQueryChange={setUserQuery}
          onSourceChange={setSourceFilter}
          onMediaTypeChange={setMediaTypeFilter}
          onClear={() => {
            setUserQuery("");
            setSourceFilter("all");
            setMediaTypeFilter("all");
          }}
        />

        <section className="rounded-2xl border border-white/10 bg-card p-5 shadow-premium">
          <div className="mb-4 flex items-center justify-between gap-4">
            <div>
              <h2 className="font-display text-2xl text-white">Active Sessions Grid</h2>
              <p className="text-sm text-fg-muted">All current activity from Tautulli and SFTPGo, unified but source-safe.</p>
            </div>
            <p className="text-xs uppercase tracking-[0.14em] text-fg-muted">
              {lastUpdated ? `Refreshed ${relativeFromNow(lastUpdated.toISOString())}` : "Waiting..."}
            </p>
          </div>

          {loading ? <LoadingState title="Loading active sessions" /> : null}
          {!loading && error ? <ErrorState description={error} /> : null}
          {!loading && !error && activeSessions.length === 0 ? (
            <EmptyState title="No active sessions" description="Try clearing filters or wait for new activity." />
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
            <h2 className="font-display text-2xl text-white">Recent Activity</h2>
            <p className="text-sm text-fg-muted">Latest ended or stale sessions for rapid troubleshooting.</p>
          </div>

          {recentSessions.length === 0 ? (
            <EmptyState title="No recent activity" description="History will appear as sessions complete." />
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
                  <div className="grid w-[112px] justify-items-center gap-1">
                    <SourceBadge source={session.source} />
                    <span className="text-xs text-fg-muted">{relativeFromNow(session.updated_at)}</span>
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




