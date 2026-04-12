import { useEffect, useMemo, useState } from "react";

import { MediaStatsResponse, OverviewStats, UserInsightsResponse, UsersStatsResponse } from "@/types/stats";

import { apiGet } from "@/shared/api/client";
import { StatCard } from "@/shared/ui/cards/StatCard";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";

import { ChartCard } from "@/features/stats/components/ChartCard";
import { DonutChart } from "@/features/stats/components/DonutChart";
import { GroupedBarChart } from "@/features/stats/components/GroupedBarChart";
import { HorizontalBars } from "@/features/stats/components/HorizontalBars";
import { TopMediaList } from "@/features/stats/components/TopMediaList";
import { VerticalBarChart } from "@/features/stats/components/VerticalBarChart";

function fmtInt(value: number): string {
  return value.toLocaleString();
}

function formatBps(value: number): string {
  const mbps = value / 1_000_000;
  if (mbps < 1000) return `${mbps.toFixed(1)} Mbps`;
  return `${(mbps / 1000).toFixed(2)} Gbps`;
}

function shortDate(value: string): string {
  const d = new Date(`${value}T00:00:00`);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString(undefined, { day: "2-digit", month: "short" });
}

function monthLabel(value: string): string {
  const [year, month] = value.split("-");
  const d = new Date(Number(year), Number(month) - 1, 1);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString(undefined, { month: "short", year: "numeric" });
}

function weekLabel(value: string): string {
  const m = /^(\d{4})-W(\d{2})$/.exec(value);
  if (!m) return value;
  return `Semana ${m[2]} (${m[1]})`;
}

function lastItems<T>(items: T[], count: number): T[] {
  if (items.length <= count) return items;
  return items.slice(items.length - count);
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
        apiGet<UsersStatsResponse>("/stats/users?limit=15"),
        apiGet<MediaStatsResponse>("/stats/media?limit=10"),
        apiGet<UserInsightsResponse>("/stats/users/insights?limit=30"),
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
    const onRefresh = () => void loadStats();
    window.addEventListener("streamfuse:refresh", onRefresh);
    return () => {
      window.removeEventListener("streamfuse:refresh", onRefresh);
    };
  }, []);

  const charts = useMemo(() => {
    if (!overview || !users || !media || !insights) return null;

    const sessionsByDay = lastItems(overview.sessions_by_day, 7).map((p) => ({
      label: shortDate(p.day),
      value: p.sessions,
    }));
    const sessionsByWeek = lastItems(overview.sessions_by_week, 4).map((p) => ({
      label: weekLabel(p.day),
      value: p.sessions,
    }));
    const sessionsByMonth = lastItems(overview.sessions_by_month, 12).map((p) => ({
      label: monthLabel(p.day),
      value: p.sessions,
    }));
    const sessionsByYear = overview.sessions_by_year.map((p) => ({
      label: p.day,
      value: p.sessions,
    }));

    const bandwidthByDay = lastItems(overview.bandwidth_by_day, 7).map((p) => ({
      label: shortDate(p.day),
      value: p.avg_bandwidth_bps,
    }));
    const bandwidthByWeek = lastItems(overview.bandwidth_by_week, 4).map((p) => ({
      label: weekLabel(p.day),
      value: p.avg_bandwidth_bps,
    }));
    const bandwidthByMonth = lastItems(overview.bandwidth_by_month, 12).map((p) => ({
      label: monthLabel(p.day),
      value: p.avg_bandwidth_bps,
    }));
    const bandwidthByYear = overview.bandwidth_by_year.map((p) => ({
      label: p.day,
      value: p.avg_bandwidth_bps,
    }));

    const peak24 = lastItems(overview.play_count_by_hour, 24).map((p) => ({
      label: `${String(p.hour).padStart(2, "0")}:00`,
      value: p.sessions,
    }));

    const mediaByUser = insights.items
      .slice()
      .sort((a, b) => b.total_sessions - a.total_sessions)
      .slice(0, 12)
      .map((item) => ({
        label: item.user_name,
        seriesA: item.movie_sessions,
        seriesB: item.episode_sessions,
      }));

    const concurrentBySource = overview.active_by_source.map((item) => ({
      label: item.source.toUpperCase(),
      value: item.sessions,
      hint: "concurrentes ahora",
    }));

    const sourceColors: Record<string, string> = {
      tautulli: "#22d3ee",
      sftpgo: "#34d399",
      samba: "#facc15",
    };

    const sourceSlices = overview.source_distribution.map((s) => ({
      label: s.source,
      value: s.sessions,
      color: sourceColors[s.source] ?? "#a78bfa",
    }));

    return {
      sessionsByDay,
      sessionsByWeek,
      sessionsByMonth,
      sessionsByYear,
      bandwidthByDay,
      bandwidthByWeek,
      bandwidthByMonth,
      bandwidthByYear,
      peak24,
      mediaByUser,
      concurrentBySource,
      sourceSlices,
      topUsers: users.items.map((u) => ({ label: u.user_name, value: u.sessions, hint: `${u.active_sessions} activos` })),
      topMovies: media.top_movies,
      topSeries: media.top_series,
      byHour: overview.play_count_by_hour.map((p) => ({ label: `${String(p.hour).padStart(2, "0")}:00`, value: p.sessions })),
    };
  }, [overview, users, media, insights]);

  return (
    <div className="min-h-[760px] space-y-6">
      <header className="min-h-[72px]">
        <h2 className="font-display text-3xl text-white">Stats</h2>
        <p className="text-sm text-fg-muted">Analitica detallada de sesiones, usuarios, medios y tendencias.</p>
      </header>

      {loading ? <LoadingState title="Loading statistics" /> : null}
      {!loading && error ? <ErrorState description={error} /> : null}
      {!loading && !error && !charts ? <EmptyState title="No stats yet" description="Ingest data to unlock analytics." /> : null}

      {!loading && !error && charts && overview ? (
        <>
          <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
            <StatCard label="Total Sessions" value={fmtInt(overview.total_sessions)} hint="Historico" />
            <StatCard label="Active Now" value={fmtInt(overview.active_sessions)} hint="En directo" />
            <StatCard label="Ended" value={fmtInt(overview.ended_sessions)} hint="Finalizadas" />
            <StatCard label="Stale" value={fmtInt(overview.stale_sessions)} hint="Recuperadas" />
            <StatCard label="Total Shared" value={overview.total_shared_human} hint="Acumulado" />
          </section>

          <section>
            <ChartCard title="Sessions by Day" subtitle="Ultimos 7 dias. Eje X: dia. Eje Y: numero de sesiones.">
              <VerticalBarChart points={charts.sessionsByDay} valueFormatter={(v) => `${Math.round(v)} ses.`} yAxisTitle="Sesiones" xAxisTitle="Dia" maxXTicks={7} />
            </ChartCard>
          </section>

          <section>
            <ChartCard title="Sessions by Week" subtitle="Ultimas 4 semanas ISO. Eje X: semana ISO. Eje Y: numero de sesiones.">
              <VerticalBarChart points={charts.sessionsByWeek} valueFormatter={(v) => `${Math.round(v)} ses.`} yAxisTitle="Sesiones" xAxisTitle="Semana" maxXTicks={4} />
            </ChartCard>
          </section>

          <section>
            <ChartCard title="Sessions by Month" subtitle="Ultimos 12 meses. Eje X: mes y ano. Eje Y: numero de sesiones.">
              <VerticalBarChart points={charts.sessionsByMonth} valueFormatter={(v) => `${Math.round(v)} ses.`} yAxisTitle="Sesiones" xAxisTitle="Mes" maxXTicks={12} />
            </ChartCard>
          </section>

          <section>
            <ChartCard title="Sessions by Year" subtitle="Historico completo. Eje X: ano. Eje Y: numero de sesiones.">
              <VerticalBarChart points={charts.sessionsByYear} valueFormatter={(v) => `${Math.round(v)} ses.`} yAxisTitle="Sesiones" xAxisTitle="Ano" maxXTicks={10} />
            </ChartCard>
          </section>

          <section>
            <ChartCard title="Bandwidth by Day" subtitle="Ultimos 7 dias. Eje X: dia. Eje Y: ancho de banda medio.">
              <VerticalBarChart points={charts.bandwidthByDay} valueFormatter={formatBps} yAxisTitle="Bandwidth" xAxisTitle="Dia" barClassName="from-emerald-400 to-cyan-300" maxXTicks={7} />
            </ChartCard>
          </section>

          <section>
            <ChartCard title="Bandwidth by Week" subtitle="Ultimas 4 semanas ISO. Eje X: semana ISO. Eje Y: ancho de banda medio.">
              <VerticalBarChart points={charts.bandwidthByWeek} valueFormatter={formatBps} yAxisTitle="Bandwidth" xAxisTitle="Semana" barClassName="from-emerald-400 to-cyan-300" maxXTicks={4} />
            </ChartCard>
          </section>

          <section>
            <ChartCard title="Bandwidth by Month" subtitle="Ultimos 12 meses. Eje X: mes y ano. Eje Y: ancho de banda medio.">
              <VerticalBarChart points={charts.bandwidthByMonth} valueFormatter={formatBps} yAxisTitle="Bandwidth" xAxisTitle="Mes" barClassName="from-emerald-400 to-cyan-300" maxXTicks={12} />
            </ChartCard>
          </section>

          <section>
            <ChartCard title="Bandwidth by Year" subtitle="Historico completo. Eje X: ano. Eje Y: ancho de banda medio.">
              <VerticalBarChart points={charts.bandwidthByYear} valueFormatter={formatBps} yAxisTitle="Bandwidth" xAxisTitle="Ano" barClassName="from-emerald-400 to-cyan-300" maxXTicks={10} />
            </ChartCard>
          </section>

          <section>
            <ChartCard title="Peak Viewing Hours" subtitle="Ultimas 24 horas. Eje X: hora local. Eje Y: sesiones iniciadas.">
              <VerticalBarChart points={charts.peak24} valueFormatter={(v) => `${Math.round(v)} ses.`} yAxisTitle="Sesiones" xAxisTitle="Hora" maxXTicks={24} />
            </ChartCard>
          </section>

          <section>
            <ChartCard title="Play Count by Hour" subtitle="Distribucion por hora local. Eje X: hora. Eje Y: sesiones.">
              <VerticalBarChart points={charts.byHour} valueFormatter={(v) => `${Math.round(v)} ses.`} yAxisTitle="Sesiones" xAxisTitle="Hora" maxXTicks={24} />
            </ChartCard>
          </section>

          <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            <ChartCard title="Concurrent Streams" subtitle="Sesiones concurrentes actuales por fuente.">
              <HorizontalBars items={charts.concurrentBySource} valueFormatter={fmtInt} />
            </ChartCard>
            <ChartCard title="Source Distribution" subtitle="Reparto total por proveedor" rightSlot={<span className="text-xs text-fg-muted">Donut</span>}>
              <DonutChart slices={charts.sourceSlices} />
            </ChartCard>
            <ChartCard title="Top Users" subtitle="Usuarios con mas sesiones">
              <HorizontalBars items={charts.topUsers} valueFormatter={fmtInt} />
            </ChartCard>
          </section>

          <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            <ChartCard title="Play Count by Media Type User" subtitle="Por usuario: 2 barras (peliculas y series)">
              <GroupedBarChart items={charts.mediaByUser} seriesALabel="Movies" seriesBLabel="Series" valueFormatter={fmtInt} yAxisTitle="Sesiones" xAxisTitle="Usuarios" />
            </ChartCard>

            <ChartCard title="Top Movies" subtitle="Ranking por usuarios unicos (no clickable)">
              <TopMediaList items={charts.topMovies} />
            </ChartCard>

            <ChartCard title="Top Series" subtitle="Ranking por usuarios unicos (no clickable)">
              <TopMediaList items={charts.topSeries} />
            </ChartCard>
          </section>
        </>
      ) : null}
    </div>
  );
}
