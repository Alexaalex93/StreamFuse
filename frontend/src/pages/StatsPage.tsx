import { useEffect, useMemo, useState } from "react";

import { MediaStatsResponse, OverviewStats, UserInsightsResponse, UsersStatsResponse } from "@/types/stats";

import { apiGet } from "@/shared/api/client";
import { StatCard } from "@/shared/ui/cards/StatCard";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";

import { ChartCard } from "@/features/stats/components/ChartCard";
import { DonutChart } from "@/features/stats/components/DonutChart";
import { HorizontalBars } from "@/features/stats/components/HorizontalBars";
import { LineChart } from "@/features/stats/components/LineChart";

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

export function StatsPage() {
  const [overview, setOverview] = useState<OverviewStats | null>(null);
  const [users, setUsers] = useState<UsersStatsResponse | null>(null);
  const [media, setMedia] = useState<MediaStatsResponse | null>(null);
  const [insights, setInsights] = useState<UserInsightsResponse | null>(null);
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
        apiGet<UserInsightsResponse>("/stats/users/insights?limit=10"),
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
    window.addEventListener("streamfuse:refresh", onRefresh);
    return () => window.removeEventListener("streamfuse:refresh", onRefresh);
  }, []);

  const charts = useMemo(() => {
    if (!overview || !users || !media || !insights) {
      return null;
    }

    const sessionsDay = overview.sessions_by_day.map((point) => ({
      label: shortDate(point.day),
      value: point.sessions,
    }));
    const sessionsMonth = overview.sessions_by_month.map((point) => ({
      label: monthLabel(point.day),
      value: point.sessions,
    }));
    const sessionsYear = overview.sessions_by_year.map((point) => ({
      label: point.day,
      value: point.sessions,
    }));

    const bandwidthDay = overview.bandwidth_by_day.map((point) => ({
      label: shortDate(point.day),
      value: point.avg_bandwidth_bps,
    }));
    const bandwidthMonth = overview.bandwidth_by_month.map((point) => ({
      label: monthLabel(point.day),
      value: point.avg_bandwidth_bps,
    }));
    const bandwidthYear = overview.bandwidth_by_year.map((point) => ({
      label: point.day,
      value: point.avg_bandwidth_bps,
    }));

    const sourceColors: Record<string, string> = {
      tautulli: "#22d3ee",
      sftpgo: "#34d399",
    };

    const sourceSlices = overview.source_distribution.map((slice) => ({
      label: slice.source,
      value: slice.sessions,
      color: sourceColors[slice.source] ?? "#a78bfa",
    }));

    const peakHours = insights.peak_hours.map((point) => ({
      label: `${String(point.hour).padStart(2, "0")}:00`,
      value: point.sessions,
    }));

    return {
      sessionsDay,
      sessionsMonth,
      sessionsYear,
      bandwidthDay,
      bandwidthMonth,
      bandwidthYear,
      sourceSlices,
      peakHours,
      topUsers: users.items.map((item) => ({
        label: item.user_name,
        value: item.sessions,
        hint: `${item.active_sessions} active now`,
      })),
      topUsersByHours: insights.items.map((item) => ({
        label: item.user_name,
        value: item.total_watch_hours,
        hint: `${item.unique_titles_monthly} unique plays`,
      })),
      topMoviesUsers: insights.items.map((item) => ({
        label: item.user_name,
        value: item.unique_movies_monthly,
        hint: `${item.movie_watch_hours.toFixed(1)}h movies`,
      })),
      topSeriesUsers: insights.items.map((item) => ({
        label: item.user_name,
        value: item.unique_series_monthly,
        hint: `${item.episode_watch_hours.toFixed(1)}h series`,
      })),
      topMovies: media.top_movies.map((item) => ({
        label: item.title,
        value: item.sessions,
        hint: `${item.unique_users} users`,
      })),
      topSeries: media.top_series.map((item) => ({
        label: item.title,
        value: item.sessions,
        hint: `${item.unique_users} users`,
      })),
    };
  }, [overview, users, media, insights]);

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
            <StatCard label="Most Sessions" value={insights.leaders.most_sessions_user.user_name} hint={`${fmtInt(Number(insights.leaders.most_sessions_user.value))} sessions`} />
            <StatCard label="Most Watch Hours" value={insights.leaders.most_watch_hours_user.user_name} hint={`${Number(insights.leaders.most_watch_hours_user.value).toFixed(1)} h`} />
            <StatCard label="Most Movies" value={insights.leaders.most_movies_user.user_name} hint={`${fmtInt(Number(insights.leaders.most_movies_user.value))} unique/month`} />
            <StatCard label="Most Series" value={insights.leaders.most_series_user.user_name} hint={`${fmtInt(Number(insights.leaders.most_series_user.value))} unique/month`} />
          </section>

          <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            <ChartCard title="Sessions by Day" subtitle="Volume trend">
              <LineChart points={charts.sessionsDay} valueFormatter={(value) => `${Math.round(value)} sessions`} />
            </ChartCard>
            <ChartCard title="Sessions by Month" subtitle="Long-term trend">
              <LineChart points={charts.sessionsMonth} valueFormatter={(value) => `${Math.round(value)} sessions`} />
            </ChartCard>
            <ChartCard title="Sessions by Year" subtitle="Annual trend">
              <LineChart points={charts.sessionsYear} valueFormatter={(value) => `${Math.round(value)} sessions`} />
            </ChartCard>
          </section>

          <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            <ChartCard title="Bandwidth by Day" subtitle="Average daily throughput">
              <LineChart points={charts.bandwidthDay} valueFormatter={formatBps} lineColorClass="stroke-emerald-300" />
            </ChartCard>
            <ChartCard title="Bandwidth by Month" subtitle="Average monthly throughput">
              <LineChart points={charts.bandwidthMonth} valueFormatter={formatBps} lineColorClass="stroke-emerald-300" />
            </ChartCard>
            <ChartCard title="Bandwidth by Year" subtitle="Average yearly throughput">
              <LineChart points={charts.bandwidthYear} valueFormatter={formatBps} lineColorClass="stroke-emerald-300" />
            </ChartCard>
          </section>

          <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            <ChartCard title="Peak Viewing Hours" subtitle={`Timezone: ${insights.timezone}`}>
              <LineChart points={charts.peakHours} valueFormatter={(value) => `${Math.round(value)} sessions`} lineColorClass="stroke-cyan-300" />
            </ChartCard>
            <ChartCard title="Users by Watch Hours" subtitle="Who watches the most (hours)">
              <HorizontalBars items={charts.topUsersByHours} valueFormatter={(value) => `${value.toFixed(1)}h`} />
            </ChartCard>
            <ChartCard title="Source Distribution" subtitle="Session share by provider" rightSlot={<span className="text-xs text-fg-muted">Donut</span>}>
              <DonutChart slices={charts.sourceSlices} />
            </ChartCard>
          </section>

          <section className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-4">
            <ChartCard title="Top Users" subtitle="Most active viewers / transfer users">
              <HorizontalBars items={charts.topUsers} valueFormatter={fmtInt} />
            </ChartCard>

            <ChartCard title="Top Movie Users" subtitle="Unique movie plays per month">
              <HorizontalBars items={charts.topMoviesUsers} valueFormatter={fmtInt} />
            </ChartCard>

            <ChartCard title="Top Series Users" subtitle="Unique series plays per month">
              <HorizontalBars items={charts.topSeriesUsers} valueFormatter={fmtInt} />
            </ChartCard>

            <ChartCard title="Top Movies" subtitle="Most frequent movie sessions">
              <HorizontalBars items={charts.topMovies} valueFormatter={fmtInt} />
            </ChartCard>
          </section>

          <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <ChartCard title="Top Series" subtitle="Most frequent episodic sessions">
              <HorizontalBars items={charts.topSeries} valueFormatter={fmtInt} />
            </ChartCard>
            <ChartCard title="Playback Rule" subtitle="How session count differs from unique plays">
              <div className="space-y-2 text-sm text-fg-muted">
                <p>History counts every session start/stop.</p>
                <p>Unique plays count once per user + title + month.</p>
                <p className="text-xs uppercase tracking-[0.12em] text-fg-muted">{insights.play_count_rule}</p>
              </div>
            </ChartCard>
          </section>
        </>
      ) : null}
    </div>
  );
}
