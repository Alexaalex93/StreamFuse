import { useEffect, useMemo, useState } from "react";

import { MediaStatsResponse, OverviewStats, UserInsightItem, UserInsightsResponse, UsersStatsResponse } from "@/types/stats";

import { apiGet } from "@/shared/api/client";
import { StatCard } from "@/shared/ui/cards/StatCard";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";

import { ChartCard } from "@/features/stats/components/ChartCard";
import { DonutChart } from "@/features/stats/components/DonutChart";
import { HorizontalBars } from "@/features/stats/components/HorizontalBars";
import { LineChart } from "@/features/stats/components/LineChart";

type UserMetric = "total_sessions" | "total_watch_hours" | "unique_movies_monthly" | "unique_series_monthly";

function formatBps(value: number): string {
  const mbps = value / 1_000_000;
  if (mbps < 1000) {
    return `${mbps.toFixed(1)} Mbps`;
  }
  return `${(mbps / 1000).toFixed(2)} Gbps`;
}

function shortDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function monthLabel(value: string): string {
  const [year, month] = value.split("-");
  if (!year || !month) {
    return value;
  }
  const date = new Date(Number(year), Number(month) - 1, 1);
  return date.toLocaleDateString(undefined, { month: "short", year: "2-digit" });
}

function fmtInt(value: number): string {
  return value.toLocaleString();
}

function toUserBars(items: UserInsightItem[], metric: UserMetric) {
  const sorted = [...items].sort((a, b) => Number((b as any)[metric] || 0) - Number((a as any)[metric] || 0));

  if (metric === "total_watch_hours") {
    return sorted.map((item) => ({
      label: item.user_name,
      value: item.total_watch_hours,
      hint: `${item.total_sessions} sessions`,
    }));
  }

  if (metric === "unique_movies_monthly") {
    return sorted.map((item) => ({
      label: item.user_name,
      value: item.unique_movies_monthly,
      hint: `${item.movie_watch_hours.toFixed(1)}h movies`,
    }));
  }

  if (metric === "unique_series_monthly") {
    return sorted.map((item) => ({
      label: item.user_name,
      value: item.unique_series_monthly,
      hint: `${item.episode_watch_hours.toFixed(1)}h series`,
    }));
  }

  return sorted.map((item) => ({
    label: item.user_name,
    value: item.total_sessions,
    hint: `${item.total_watch_hours.toFixed(1)}h watched`,
  }));
}

function metricMeta(metric: UserMetric) {
  if (metric === "total_watch_hours") {
    return {
      title: "Users by Watch Hours",
      subtitle: "Detailed ranking by total watch hours",
      format: (value: number) => `${value.toFixed(1)}h`,
    };
  }
  if (metric === "unique_movies_monthly") {
    return {
      title: "Users by Unique Movies (Monthly)",
      subtitle: "One play per user+movie+month",
      format: (value: number) => fmtInt(value),
    };
  }
  if (metric === "unique_series_monthly") {
    return {
      title: "Users by Unique Series (Monthly)",
      subtitle: "One play per user+series+month",
      format: (value: number) => fmtInt(value),
    };
  }
  return {
    title: "Users by Total Sessions",
    subtitle: "All raw sessions in selected range",
    format: (value: number) => fmtInt(value),
  };
}

export function StatsPage() {
  const [overview, setOverview] = useState<OverviewStats | null>(null);
  const [users, setUsers] = useState<UsersStatsResponse | null>(null);
  const [media, setMedia] = useState<MediaStatsResponse | null>(null);
  const [insights, setInsights] = useState<UserInsightsResponse | null>(null);
  const [selectedMetric, setSelectedMetric] = useState<UserMetric>("total_sessions");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStats = async () => {
    try {
      setLoading(true);
      setError(null);

      const [overviewData, usersData, mediaData, insightsData] = await Promise.all([
        apiGet<OverviewStats>("/stats/overview"),
        apiGet<UsersStatsResponse>("/stats/users?limit=8"),
        apiGet<MediaStatsResponse>("/stats/media?limit=8"),
        apiGet<UserInsightsResponse>("/stats/users/insights?limit=20"),
      ]);

      setOverview(overviewData);
      setUsers(usersData);
      setMedia(mediaData);
      setInsights(insightsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load stats");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadStats();
  }, []);

  useEffect(() => {
    const onRefresh = () => {
      void loadStats();
    };
    const onNewFilter = () => {
      setSelectedMetric("total_sessions");
    };
    window.addEventListener("streamfuse:refresh", onRefresh);
    window.addEventListener("streamfuse:new-filter", onNewFilter);
    return () => {
      window.removeEventListener("streamfuse:refresh", onRefresh);
      window.removeEventListener("streamfuse:new-filter", onNewFilter);
    };
  }, []);

  const charts = useMemo(() => {
    if (!overview || !users || !media || !insights) {
      return null;
    }

    const sessionsDay = overview.sessions_by_day.map((point) => ({ label: shortDate(point.day), value: point.sessions }));
    const sessionsMonth = overview.sessions_by_month.map((point) => ({ label: monthLabel(point.day), value: point.sessions }));
    const sessionsYear = overview.sessions_by_year.map((point) => ({ label: point.day, value: point.sessions }));

    const bandwidthDay = overview.bandwidth_by_day.map((point) => ({ label: shortDate(point.day), value: point.avg_bandwidth_bps }));
    const bandwidthMonth = overview.bandwidth_by_month.map((point) => ({ label: monthLabel(point.day), value: point.avg_bandwidth_bps }));
    const bandwidthYear = overview.bandwidth_by_year.map((point) => ({ label: point.day, value: point.avg_bandwidth_bps }));

    const sourceColors: Record<string, string> = { tautulli: "#22d3ee", sftpgo: "#34d399" };

    const sourceSlices = overview.source_distribution.map((slice) => ({
      label: slice.source,
      value: slice.sessions,
      color: sourceColors[slice.source] ?? "#a78bfa",
    }));

    const peakHours = insights.peak_hours.map((point) => ({ label: `${String(point.hour).padStart(2, "0")}:00`, value: point.sessions }));

    return {
      sessionsDay,
      sessionsMonth,
      sessionsYear,
      bandwidthDay,
      bandwidthMonth,
      bandwidthYear,
      sourceSlices,
      peakHours,
      topUsers: users.items.map((item) => ({ label: item.user_name, value: item.sessions, hint: `${item.active_sessions} active now` })),
      topMovies: media.top_movies.map((item) => ({ label: item.title, value: item.sessions, hint: `${item.unique_users} users` })),
      topSeries: media.top_series.map((item) => ({ label: item.title, value: item.sessions, hint: `${item.unique_users} users` })),
      dynamicUsers: toUserBars(insights.items, selectedMetric),
    };
  }, [overview, users, media, insights, selectedMetric]);

  const selectedMeta = metricMeta(selectedMetric);

  return (
    <div className="space-y-6 min-h-[760px]">
      <header className="min-h-[72px]">
        <h2 className="font-display text-3xl text-white">Stats</h2>
        <p className="text-sm text-fg-muted">Detailed analytics for sessions, users, media and trends.</p>
      </header>

      {loading ? <LoadingState title="Loading statistics" /> : null}
      {!loading && error ? <ErrorState description={error} /> : null}
      {!loading && !error && !charts ? <EmptyState title="No stats yet" description="Ingest data to unlock analytics." /> : null}

      {!loading && !error && charts && overview && insights ? (
        <>
          <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
            <StatCard label="Total Sessions" value={fmtInt(overview.total_sessions)} hint="Selected range" />
            <StatCard label="Active Now" value={fmtInt(overview.active_sessions)} hint="Live sessions" />
            <StatCard label="Ended" value={fmtInt(overview.ended_sessions)} hint="Completed sessions" />
            <StatCard label="Stale" value={fmtInt(overview.stale_sessions)} hint="Recovered inactive sessions" />
            <StatCard label="Total Shared" value={overview.total_shared_human} hint="Cumulative transferred" />
          </section>

          <section className="grid grid-cols-1 gap-4 xl:grid-cols-4">
            <StatCard
              label="Most Sessions"
              value={insights.leaders.most_sessions_user.user_name}
              hint={`${fmtInt(Number(insights.leaders.most_sessions_user.value))} sessions`}
              onClick={() => setSelectedMetric("total_sessions")}
              selected={selectedMetric === "total_sessions"}
            />
            <StatCard
              label="Most Watch Hours"
              value={insights.leaders.most_watch_hours_user.user_name}
              hint={`${Number(insights.leaders.most_watch_hours_user.value).toFixed(1)} h`}
              onClick={() => setSelectedMetric("total_watch_hours")}
              selected={selectedMetric === "total_watch_hours"}
            />
            <StatCard
              label="Most Movies"
              value={insights.leaders.most_movies_user.user_name}
              hint={`${fmtInt(Number(insights.leaders.most_movies_user.value))} unique/month`}
              onClick={() => setSelectedMetric("unique_movies_monthly")}
              selected={selectedMetric === "unique_movies_monthly"}
            />
            <StatCard
              label="Most Series"
              value={insights.leaders.most_series_user.user_name}
              hint={`${fmtInt(Number(insights.leaders.most_series_user.value))} unique/month`}
              onClick={() => setSelectedMetric("unique_series_monthly")}
              selected={selectedMetric === "unique_series_monthly"}
            />
          </section>

          <section>
            <ChartCard title={selectedMeta.title} subtitle={selectedMeta.subtitle}>
              <HorizontalBars items={charts.dynamicUsers} valueFormatter={selectedMeta.format} />
            </ChartCard>
          </section>

          <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            <ChartCard title="Sessions by Day" subtitle="Count of sessions per calendar day">
              <LineChart points={charts.sessionsDay} valueFormatter={(value) => `${Math.round(value)} sessions`} yAxisTitle="Sessions" xAxisTitle="Day" />
            </ChartCard>
            <ChartCard title="Sessions by Month" subtitle="Count of sessions grouped by month">
              <LineChart points={charts.sessionsMonth} valueFormatter={(value) => `${Math.round(value)} sessions`} yAxisTitle="Sessions" xAxisTitle="Month" />
            </ChartCard>
            <ChartCard title="Sessions by Year" subtitle="Count of sessions grouped by year">
              <LineChart points={charts.sessionsYear} valueFormatter={(value) => `${Math.round(value)} sessions`} yAxisTitle="Sessions" xAxisTitle="Year" />
            </ChartCard>
          </section>

          <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            <ChartCard title="Bandwidth by Day" subtitle="Average session bandwidth per day (Mbps/Gbps)">
              <LineChart points={charts.bandwidthDay} valueFormatter={formatBps} lineColorClass="stroke-emerald-300" yAxisTitle="Bandwidth" xAxisTitle="Day" />
            </ChartCard>
            <ChartCard title="Bandwidth by Month" subtitle="Average session bandwidth per month (Mbps/Gbps)">
              <LineChart points={charts.bandwidthMonth} valueFormatter={formatBps} lineColorClass="stroke-emerald-300" yAxisTitle="Bandwidth" xAxisTitle="Month" />
            </ChartCard>
            <ChartCard title="Bandwidth by Year" subtitle="Average session bandwidth per year (Mbps/Gbps)">
              <LineChart points={charts.bandwidthYear} valueFormatter={formatBps} lineColorClass="stroke-emerald-300" yAxisTitle="Bandwidth" xAxisTitle="Year" />
            </ChartCard>
          </section>

          <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            <ChartCard title="Peak Viewing Hours" subtitle={`Sessions started by hour (${insights.timezone})`}>
              <LineChart points={charts.peakHours} valueFormatter={(value) => `${Math.round(value)} sessions`} lineColorClass="stroke-cyan-300" yAxisTitle="Sessions" xAxisTitle="Hour" />
            </ChartCard>
            <ChartCard title="Source Distribution" subtitle="Session share by provider" rightSlot={<span className="text-xs text-fg-muted">Donut</span>}>
              <DonutChart slices={charts.sourceSlices} />
            </ChartCard>
            <ChartCard title="Top Users" subtitle="Most active viewers / transfer users">
              <HorizontalBars items={charts.topUsers} valueFormatter={fmtInt} />
            </ChartCard>
          </section>

          <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            <ChartCard title="Top Movies" subtitle="Most frequent movie sessions">
              <HorizontalBars items={charts.topMovies} valueFormatter={fmtInt} />
            </ChartCard>
            <ChartCard title="Top Series" subtitle="Most frequent episodic sessions">
              <HorizontalBars items={charts.topSeries} valueFormatter={fmtInt} />
            </ChartCard>
            <ChartCard title="Playback Rule" subtitle="Raw history vs unique monthly plays">
              <div className="space-y-2 break-words text-sm text-fg-muted">
                <p>History counts every session start/stop.</p>
                <p>Unique plays count once per user + title + month.</p>
              </div>
            </ChartCard>
          </section>
        </>
      ) : null}
    </div>
  );
}
