import { useEffect, useMemo, useState } from "react";

import { MediaStatsResponse, OverviewStats, UsersStatsResponse } from "@/types/stats";

import { apiGet } from "@/shared/api/client";
import { StatCard } from "@/shared/ui/cards/StatCard";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";

import { ChartCard } from "@/features/stats/components/ChartCard";
import { DonutChart } from "@/features/stats/components/DonutChart";
import { GroupedBarChart } from "@/features/stats/components/GroupedBarChart";
import { HorizontalBars } from "@/features/stats/components/HorizontalBars";
import { MultiLineChart } from "@/features/stats/components/MultiLineChart";
import { TopMediaList } from "@/features/stats/components/TopMediaList";
import { VerticalBarChart } from "@/features/stats/components/VerticalBarChart";

type DrillChartKey =
  | "sessions_day"
  | "sessions_week"
  | "sessions_month"
  | "sessions_year"
  | "bandwidth_day"
  | "bandwidth_week"
  | "bandwidth_month"
  | "bandwidth_year"
  | "shared_day"
  | "shared_week"
  | "shared_month"
  | "shared_year"
  | "shared_hour"
  | "peak_hours"
  | "play_count_hour";

type SeriesPoint = { label: string; value: number };
type DrillSeries = { userName: string; color: string; points: SeriesPoint[] };

const DRILL_USER_COLORS = ["#22d3ee", "#f97316", "#a78bfa", "#34d399", "#f43f5e", "#eab308", "#60a5fa", "#fb7185"];

function fmtInt(value: number): string {
  return value.toLocaleString();
}

function formatBps(value: number): string {
  const mbps = value / 1_000_000;
  if (mbps < 1000) return `${mbps.toFixed(1)} Mbps`;
  return `${(mbps / 1000).toFixed(2)} Gbps`;
}

function formatBytes(value: number): string {
  if (value <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB", "PB"];
  let amount = value;
  let idx = 0;
  while (amount >= 1024 && idx < units.length - 1) {
    amount /= 1024;
    idx += 1;
  }
  if (idx === 0) return `${Math.round(amount)} ${units[idx]}`;
  return `${amount.toFixed(1)} ${units[idx]}`;
}

function ymd(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function isoWeekKey(date: Date): string {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7));
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const week = Math.ceil((((d.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
  return `${d.getUTCFullYear()}-W${String(week).padStart(2, "0")}`;
}

function isoWeekLabel(key: string): string {
  const match = /^(\d{4})-W(\d{2})$/.exec(key);
  if (!match) return key;
  const year = Number(match[1]);
  const week = Number(match[2]);
  const jan4 = new Date(Date.UTC(year, 0, 4));
  const jan4Day = jan4.getUTCDay() || 7;
  const mondayWeek1 = new Date(jan4);
  mondayWeek1.setUTCDate(jan4.getUTCDate() - jan4Day + 1);
  const target = new Date(mondayWeek1);
  target.setUTCDate(mondayWeek1.getUTCDate() + (week - 1) * 7);
  const month = target.toLocaleDateString("es-ES", { month: "short" });
  return `S${week} ${month} ${year}`;
}

function monthKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

function monthLabel(key: string): string {
  const [year, month] = key.split("-");
  const d = new Date(Number(year), Number(month) - 1, 1);
  return d.toLocaleDateString("es-ES", { month: "short", year: "numeric" });
}

function weekdayLabel(date: Date): string {
  return date.toLocaleDateString("es-ES", { weekday: "long" });
}

function buildSessionsByDay(overview: OverviewStats, now: Date): SeriesPoint[] {
  const map = new Map(overview.sessions_by_day.map((p) => [p.day, p.sessions]));
  return Array.from({ length: 7 }, (_, idx) => {
    const d = new Date(now);
    d.setDate(now.getDate() - (6 - idx));
    const key = ymd(d);
    return { label: weekdayLabel(d), value: map.get(key) ?? 0 };
  });
}

function buildBandwidthByDay(overview: OverviewStats, now: Date): SeriesPoint[] {
  const map = new Map(overview.bandwidth_by_day.map((p) => [p.day, p.avg_bandwidth_bps]));
  return Array.from({ length: 7 }, (_, idx) => {
    const d = new Date(now);
    d.setDate(now.getDate() - (6 - idx));
    const key = ymd(d);
    return { label: weekdayLabel(d), value: map.get(key) ?? 0 };
  });
}

function buildSharedByDay(overview: OverviewStats, now: Date): SeriesPoint[] {
  const map = new Map(overview.shared_by_day.map((p) => [p.day, p.shared_bytes]));
  return Array.from({ length: 7 }, (_, idx) => {
    const d = new Date(now);
    d.setDate(now.getDate() - (6 - idx));
    const key = ymd(d);
    return { label: weekdayLabel(d), value: map.get(key) ?? 0 };
  });
}

function buildSessionsByWeek(overview: OverviewStats, now: Date): SeriesPoint[] {
  const map = new Map(overview.sessions_by_week.map((p) => [p.day, p.sessions]));
  return Array.from({ length: 4 }, (_, idx) => {
    const d = new Date(now);
    d.setDate(now.getDate() - (3 - idx) * 7);
    const key = isoWeekKey(d);
    return { label: isoWeekLabel(key), value: map.get(key) ?? 0 };
  });
}

function buildBandwidthByWeek(overview: OverviewStats, now: Date): SeriesPoint[] {
  const map = new Map(overview.bandwidth_by_week.map((p) => [p.day, p.avg_bandwidth_bps]));
  return Array.from({ length: 4 }, (_, idx) => {
    const d = new Date(now);
    d.setDate(now.getDate() - (3 - idx) * 7);
    const key = isoWeekKey(d);
    return { label: isoWeekLabel(key), value: map.get(key) ?? 0 };
  });
}

function buildSharedByWeek(overview: OverviewStats, now: Date): SeriesPoint[] {
  const map = new Map(overview.shared_by_week.map((p) => [p.day, p.shared_bytes]));
  return Array.from({ length: 4 }, (_, idx) => {
    const d = new Date(now);
    d.setDate(now.getDate() - (3 - idx) * 7);
    const key = isoWeekKey(d);
    return { label: isoWeekLabel(key), value: map.get(key) ?? 0 };
  });
}

function buildSessionsByMonth(overview: OverviewStats, now: Date): SeriesPoint[] {
  const map = new Map(overview.sessions_by_month.map((p) => [p.day, p.sessions]));
  return Array.from({ length: 12 }, (_, idx) => {
    const d = new Date(now.getFullYear(), now.getMonth() - (11 - idx), 1);
    const key = monthKey(d);
    return { label: monthLabel(key), value: map.get(key) ?? 0 };
  });
}

function buildBandwidthByMonth(overview: OverviewStats, now: Date): SeriesPoint[] {
  const map = new Map(overview.bandwidth_by_month.map((p) => [p.day, p.avg_bandwidth_bps]));
  return Array.from({ length: 12 }, (_, idx) => {
    const d = new Date(now.getFullYear(), now.getMonth() - (11 - idx), 1);
    const key = monthKey(d);
    return { label: monthLabel(key), value: map.get(key) ?? 0 };
  });
}

function buildSharedByMonth(overview: OverviewStats, now: Date): SeriesPoint[] {
  const map = new Map(overview.shared_by_month.map((p) => [p.day, p.shared_bytes]));
  return Array.from({ length: 12 }, (_, idx) => {
    const d = new Date(now.getFullYear(), now.getMonth() - (11 - idx), 1);
    const key = monthKey(d);
    return { label: monthLabel(key), value: map.get(key) ?? 0 };
  });
}

function buildSessionsByYear(overview: OverviewStats, now: Date): SeriesPoint[] {
  const map = new Map(overview.sessions_by_year.map((p) => [p.day, p.sessions]));
  const keys = Array.from(new Set([...overview.sessions_by_year.map((p) => p.day), String(now.getFullYear())])).sort();
  return keys.map((key) => ({ label: key, value: map.get(key) ?? 0 }));
}

function buildBandwidthByYear(overview: OverviewStats, now: Date): SeriesPoint[] {
  const map = new Map(overview.bandwidth_by_year.map((p) => [p.day, p.avg_bandwidth_bps]));
  const keys = Array.from(new Set([...overview.bandwidth_by_year.map((p) => p.day), String(now.getFullYear())])).sort();
  return keys.map((key) => ({ label: key, value: map.get(key) ?? 0 }));
}

function buildSharedByYear(overview: OverviewStats, now: Date): SeriesPoint[] {
  const map = new Map(overview.shared_by_year.map((p) => [p.day, p.shared_bytes]));
  const keys = Array.from(new Set([...overview.shared_by_year.map((p) => p.day), String(now.getFullYear())])).sort();
  return keys.map((key) => ({ label: key, value: map.get(key) ?? 0 }));
}

function buildHours(overview: OverviewStats): SeriesPoint[] {
  return Array.from({ length: 24 }, (_, hour) => {
    const found = overview.play_count_by_hour.find((p) => p.hour === hour);
    return { label: `${String(hour).padStart(2, "0")}h`, value: found?.sessions ?? 0 };
  });
}

function buildSharedByHour(overview: OverviewStats): SeriesPoint[] {
  return Array.from({ length: 24 }, (_, hour) => {
    const found = overview.shared_by_hour.find((p) => p.hour === hour);
    return { label: `${String(hour).padStart(2, "0")}h`, value: found?.shared_bytes ?? 0 };
  });
}

function pointsByKey(key: DrillChartKey, overview: OverviewStats, now: Date): SeriesPoint[] {
  switch (key) {
    case "sessions_day":
      return buildSessionsByDay(overview, now);
    case "sessions_week":
      return buildSessionsByWeek(overview, now);
    case "sessions_month":
      return buildSessionsByMonth(overview, now);
    case "sessions_year":
      return buildSessionsByYear(overview, now);
    case "bandwidth_day":
      return buildBandwidthByDay(overview, now);
    case "bandwidth_week":
      return buildBandwidthByWeek(overview, now);
    case "bandwidth_month":
      return buildBandwidthByMonth(overview, now);
    case "bandwidth_year":
      return buildBandwidthByYear(overview, now);
    case "shared_day":
      return buildSharedByDay(overview, now);
    case "shared_week":
      return buildSharedByWeek(overview, now);
    case "shared_month":
      return buildSharedByMonth(overview, now);
    case "shared_year":
      return buildSharedByYear(overview, now);
    case "shared_hour":
      return buildSharedByHour(overview);
    case "peak_hours":
      return buildHours(overview);
    case "play_count_hour":
      return buildHours(overview);
    default:
      return [];
  }
}

function drillTitleByKey(key: DrillChartKey): string {
  const titles: Record<DrillChartKey, string> = {
    sessions_day: "Sessions by Day",
    sessions_week: "Sessions by Week",
    sessions_month: "Sessions by Month",
    sessions_year: "Sessions by Year",
    bandwidth_day: "Bandwidth by Day",
    bandwidth_week: "Bandwidth by Week",
    bandwidth_month: "Bandwidth by Month",
    bandwidth_year: "Bandwidth by Year",
    shared_day: "Shared Content by Day",
    shared_week: "Shared Content by Week",
    shared_month: "Shared Content by Month",
    shared_year: "Shared Content by Year",
    shared_hour: "Shared Content by Hour",
    peak_hours: "Peak Viewing Hours",
    play_count_hour: "Play Count by Hour",
  };
  return titles[key];
}

export function StatsPage() {
  const [overview, setOverview] = useState<OverviewStats | null>(null);
  const [users, setUsers] = useState<UsersStatsResponse | null>(null);
  const [media, setMedia] = useState<MediaStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedChart, setSelectedChart] = useState<DrillChartKey | null>(null);
  const [drillSeries, setDrillSeries] = useState<DrillSeries[] | null>(null);
  const [drillLoading, setDrillLoading] = useState(false);
  const handleSelectChart = (key: DrillChartKey) => {
    setSelectedChart((current) => (current === key ? null : key));
  };

  const loadStats = async () => {
    try {
      setLoading(true);
      setError(null);
      const [overviewData, usersData, mediaData] = await Promise.all([
        apiGet<OverviewStats>("/stats/overview"),
        apiGet<UsersStatsResponse>("/stats/users?limit=15"),
        apiGet<MediaStatsResponse>("/stats/media?limit=10"),
      ]);
      setOverview(overviewData);
      setUsers(usersData);
      setMedia(mediaData);
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

  const drillUsers = useMemo(() => users?.items.map((u) => u.user_name).slice(0, 6) ?? [], [users]);

  useEffect(() => {
    const run = async () => {
      if (!selectedChart || drillUsers.length === 0) {
        setDrillSeries(null);
        return;
      }
      try {
        setDrillLoading(true);
        const now = new Date();
        const rows = await Promise.all(
          drillUsers.map(async (userName, index) => {
            const query = `?user_name=${encodeURIComponent(userName)}`;
            const data = await apiGet<OverviewStats>(`/stats/overview${query}`);
            return {
              userName,
              color: DRILL_USER_COLORS[index % DRILL_USER_COLORS.length],
              points: pointsByKey(selectedChart, data, now),
            } as DrillSeries;
          }),
        );
        setDrillSeries(rows);
      } catch {
        setDrillSeries(null);
      } finally {
        setDrillLoading(false);
      }
    };

    void run();
  }, [selectedChart, drillUsers]);

  useEffect(() => {
    if (!selectedChart) return;
    const target = document.getElementById(`drill-${selectedChart}`);
    if (!target) return;
    window.requestAnimationFrame(() => {
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, [selectedChart]);

  const charts = useMemo(() => {
    if (!overview || !users || !media) return null;

    const now = new Date();

    const sessionsByDay = buildSessionsByDay(overview, now);
    const sessionsByWeek = buildSessionsByWeek(overview, now);
    const sessionsByMonth = buildSessionsByMonth(overview, now);
    const sessionsByYear = buildSessionsByYear(overview, now);

    const bandwidthByDay = buildBandwidthByDay(overview, now);
    const bandwidthByWeek = buildBandwidthByWeek(overview, now);
    const bandwidthByMonth = buildBandwidthByMonth(overview, now);
    const bandwidthByYear = buildBandwidthByYear(overview, now);

    const sharedByDay = buildSharedByDay(overview, now);
    const sharedByWeek = buildSharedByWeek(overview, now);
    const sharedByMonth = buildSharedByMonth(overview, now);
    const sharedByYear = buildSharedByYear(overview, now);
    const sharedByHour = buildSharedByHour(overview);

    const hours = buildHours(overview);

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

    const mediaByUser = users.items
      .slice()
      .sort((a, b) => b.sessions - a.sessions)
      .slice(0, 12)
      .map((item) => ({
        label: item.user_name,
        seriesA: item.sessions,
        seriesB: item.active_sessions,
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
      sharedByDay,
      sharedByWeek,
      sharedByMonth,
      sharedByYear,
      sharedByHour,
      peak24: hours,
      byHour: hours,
      sourceSlices,
      mediaByUser,
      topUsers: users.items.map((u) => ({ label: u.user_name, value: u.sessions, hint: `${u.active_sessions} activos` })),
      topMovies: media.top_movies,
      topSeries: media.top_series,
    };
  }, [overview, users, media]);

  const drillIsBandwidth = selectedChart?.startsWith("bandwidth") ?? false;
  const drillIsShared = selectedChart?.startsWith("shared") ?? false;

  const renderDrillSection = (key: DrillChartKey) => {
    if (selectedChart !== key) return null;

    return (
      <section id={`drill-${key}`} className="animate-drilldown-in">
        <ChartCard
          title={`Comparativa por Usuario - ${drillTitleByKey(key)}`}
          subtitle="Comparación superpuesta por usuario para esta métrica"
        >
          {drillLoading ? (
            <LoadingState title="Loading user comparison" />
          ) : !drillSeries || drillSeries.length === 0 ? (
            <EmptyState title="No user series" description="No hay datos comparables para esta gráfica." />
          ) : (
            <MultiLineChart
              series={drillSeries.map((s) => ({ label: s.userName, color: s.color, points: s.points }))}
              valueFormatter={drillIsShared ? formatBytes : drillIsBandwidth ? formatBps : (v) => `${Math.round(v)} ses.`}
              yAxisTitle={drillIsShared ? "Compartido" : drillIsBandwidth ? "Bandwidth" : "Sesiones"}
              xAxisTitle="Periodo"
            />
          )}
        </ChartCard>
      </section>
    );
  };

  return (
    <div className="min-h-[760px] space-y-6">
      <header className="min-h-[72px]">
        <h2 className="font-display text-3xl text-white">Stats</h2>
        <p className="text-sm text-fg-muted">Analítica detallada de sesiones, usuarios, medios y tendencias.</p>
      </header>

      {loading ? <LoadingState title="Loading statistics" /> : null}
      {!loading && error ? <ErrorState description={error} /> : null}
      {!loading && !error && !charts ? <EmptyState title="No stats yet" description="Ingest data to unlock analytics." /> : null}

      {!loading && !error && charts && overview ? (
        <>
          <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
            <StatCard label="Total Sessions" value={fmtInt(overview.total_sessions)} hint="Histórico" />
            <StatCard label="Active Now" value={fmtInt(overview.active_sessions)} hint="En directo" />
            <StatCard label="Ended" value={fmtInt(overview.ended_sessions)} hint="Finalizadas" />
            <StatCard label="Stale" value={fmtInt(overview.stale_sessions)} hint="Recuperadas" />
            <StatCard label="Total Shared" value={overview.total_shared_human} hint="Acumulado" />
          </section>

          <section>
            <ChartCard title="Sessions by Day" subtitle="Últimos 7 días. Eje X: día de la semana. Eje Y: número de sesiones." onClick={() => handleSelectChart("sessions_day")} selected={selectedChart === "sessions_day"}>
              <VerticalBarChart points={charts.sessionsByDay} valueFormatter={(v) => `${Math.round(v)} ses.`} yAxisTitle="SESIONES" xAxisTitle="DÍA" maxXTicks={7} />
            </ChartCard>
          </section>
          {renderDrillSection("sessions_day")}

          <section>
            <ChartCard title="Sessions by Week" subtitle="Últimas 4 semanas ISO. Eje X: semana. Eje Y: número de sesiones." onClick={() => handleSelectChart("sessions_week")} selected={selectedChart === "sessions_week"}>
              <VerticalBarChart points={charts.sessionsByWeek} valueFormatter={(v) => `${Math.round(v)} ses.`} yAxisTitle="SESIONES" xAxisTitle="SEMANA" maxXTicks={4} />
            </ChartCard>
          </section>
          {renderDrillSection("sessions_week")}

          <section>
            <ChartCard title="Sessions by Month" subtitle="Últimos 12 meses. Eje X: mes. Eje Y: número de sesiones." onClick={() => handleSelectChart("sessions_month")} selected={selectedChart === "sessions_month"}>
              <VerticalBarChart points={charts.sessionsByMonth} valueFormatter={(v) => `${Math.round(v)} ses.`} yAxisTitle="SESIONES" xAxisTitle="MES" maxXTicks={12} />
            </ChartCard>
          </section>
          {renderDrillSection("sessions_month")}

          <section>
            <ChartCard title="Sessions by Year" subtitle="Histórico completo. Eje X: año. Eje Y: número de sesiones." onClick={() => handleSelectChart("sessions_year")} selected={selectedChart === "sessions_year"}>
              <VerticalBarChart points={charts.sessionsByYear} valueFormatter={(v) => `${Math.round(v)} ses.`} yAxisTitle="SESIONES" xAxisTitle="AÑO" maxXTicks={10} />
            </ChartCard>
          </section>
          {renderDrillSection("sessions_year")}

          <section>
            <ChartCard title="Bandwidth by Day" subtitle="Últimos 7 días. Eje X: día. Eje Y: ancho de banda medio." onClick={() => handleSelectChart("bandwidth_day")} selected={selectedChart === "bandwidth_day"}>
              <VerticalBarChart points={charts.bandwidthByDay} valueFormatter={formatBps} yAxisTitle="BANDWIDTH" xAxisTitle="DÍA" barColor="#34d399" maxXTicks={7} />
            </ChartCard>
          </section>
          {renderDrillSection("bandwidth_day")}

          <section>
            <ChartCard title="Bandwidth by Week" subtitle="Últimas 4 semanas ISO. Eje X: semana. Eje Y: ancho de banda medio." onClick={() => handleSelectChart("bandwidth_week")} selected={selectedChart === "bandwidth_week"}>
              <VerticalBarChart points={charts.bandwidthByWeek} valueFormatter={formatBps} yAxisTitle="BANDWIDTH" xAxisTitle="SEMANA" barColor="#34d399" maxXTicks={4} />
            </ChartCard>
          </section>
          {renderDrillSection("bandwidth_week")}

          <section>
            <ChartCard title="Bandwidth by Month" subtitle="Últimos 12 meses. Eje X: mes. Eje Y: ancho de banda medio." onClick={() => handleSelectChart("bandwidth_month")} selected={selectedChart === "bandwidth_month"}>
              <VerticalBarChart points={charts.bandwidthByMonth} valueFormatter={formatBps} yAxisTitle="BANDWIDTH" xAxisTitle="MES" barColor="#34d399" maxXTicks={12} />
            </ChartCard>
          </section>
          {renderDrillSection("bandwidth_month")}

          <section>
            <ChartCard title="Bandwidth by Year" subtitle="Histórico completo. Eje X: año. Eje Y: ancho de banda medio." onClick={() => handleSelectChart("bandwidth_year")} selected={selectedChart === "bandwidth_year"}>
              <VerticalBarChart points={charts.bandwidthByYear} valueFormatter={formatBps} yAxisTitle="BANDWIDTH" xAxisTitle="AÑO" barColor="#34d399" maxXTicks={10} />
            </ChartCard>
          </section>
          {renderDrillSection("bandwidth_year")}

          <section>
            <ChartCard title="Shared Content by Day" subtitle="Últimos 7 días. Eje X: día. Eje Y: bytes transferidos." onClick={() => handleSelectChart("shared_day")} selected={selectedChart === "shared_day"}>
              <VerticalBarChart points={charts.sharedByDay} valueFormatter={formatBytes} yAxisTitle="COMPARTIDO" xAxisTitle="DÍA" barColor="#f59e0b" maxXTicks={7} />
            </ChartCard>
          </section>
          {renderDrillSection("shared_day")}

          <section>
            <ChartCard title="Shared Content by Week" subtitle="Últimas 4 semanas ISO. Eje X: semana. Eje Y: bytes transferidos." onClick={() => handleSelectChart("shared_week")} selected={selectedChart === "shared_week"}>
              <VerticalBarChart points={charts.sharedByWeek} valueFormatter={formatBytes} yAxisTitle="COMPARTIDO" xAxisTitle="SEMANA" barColor="#f59e0b" maxXTicks={4} />
            </ChartCard>
          </section>
          {renderDrillSection("shared_week")}

          <section>
            <ChartCard title="Shared Content by Month" subtitle="Últimos 12 meses. Eje X: mes. Eje Y: bytes transferidos." onClick={() => handleSelectChart("shared_month")} selected={selectedChart === "shared_month"}>
              <VerticalBarChart points={charts.sharedByMonth} valueFormatter={formatBytes} yAxisTitle="COMPARTIDO" xAxisTitle="MES" barColor="#f59e0b" maxXTicks={12} />
            </ChartCard>
          </section>
          {renderDrillSection("shared_month")}

          <section>
            <ChartCard title="Shared Content by Year" subtitle="Histórico completo. Eje X: año. Eje Y: bytes transferidos." onClick={() => handleSelectChart("shared_year")} selected={selectedChart === "shared_year"}>
              <VerticalBarChart points={charts.sharedByYear} valueFormatter={formatBytes} yAxisTitle="COMPARTIDO" xAxisTitle="AÑO" barColor="#f59e0b" maxXTicks={10} />
            </ChartCard>
          </section>
          {renderDrillSection("shared_year")}

          <section>
            <ChartCard title="Shared Content by Hour" subtitle="Últimas 24 horas. Eje X: hora local. Eje Y: bytes transferidos." onClick={() => handleSelectChart("shared_hour")} selected={selectedChart === "shared_hour"}>
              <VerticalBarChart points={charts.sharedByHour} valueFormatter={formatBytes} yAxisTitle="COMPARTIDO" xAxisTitle="HORA" barColor="#f59e0b" maxXTicks={6} />
            </ChartCard>
          </section>
          {renderDrillSection("shared_hour")}

          <section>
            <ChartCard title="Peak Viewing Hours" subtitle="Últimas 24 horas. Eje X: hora local. Eje Y: sesiones iniciadas." onClick={() => handleSelectChart("peak_hours")} selected={selectedChart === "peak_hours"}>
              <VerticalBarChart points={charts.peak24} valueFormatter={(v) => `${Math.round(v)} ses.`} yAxisTitle="SESIONES" xAxisTitle="HORA" maxXTicks={6} />
            </ChartCard>
          </section>
          {renderDrillSection("peak_hours")}

          <section>
            <ChartCard title="Play Count by Hour" subtitle="Distribución por hora local. Eje X: hora. Eje Y: sesiones." onClick={() => handleSelectChart("play_count_hour")} selected={selectedChart === "play_count_hour"}>
              <VerticalBarChart points={charts.byHour} valueFormatter={(v) => `${Math.round(v)} ses.`} yAxisTitle="SESIONES" xAxisTitle="HORA" maxXTicks={6} />
            </ChartCard>
          </section>
          {renderDrillSection("play_count_hour")}

          <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            <ChartCard title="Source Distribution" subtitle="Reparto total por proveedor" rightSlot={<span className="text-xs text-fg-muted">Donut</span>}>
              <DonutChart slices={charts.sourceSlices} />
            </ChartCard>
            <ChartCard title="Top Users" subtitle="Usuarios con más sesiones">
              <HorizontalBars items={charts.topUsers} valueFormatter={fmtInt} />
            </ChartCard>
            <ChartCard title="Play Count by Media Type User" subtitle="Por usuario: sesiones y activos">
              <GroupedBarChart items={charts.mediaByUser} seriesALabel="Sesiones" seriesBLabel="Activos" valueFormatter={fmtInt} yAxisTitle="Sesiones" xAxisTitle="Usuarios" />
            </ChartCard>
          </section>

          <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <ChartCard title="Top Movies" subtitle="Ranking por usuarios únicos (no clickable)">
              <TopMediaList items={charts.topMovies} />
            </ChartCard>

            <ChartCard title="Top Series" subtitle="Ranking por usuarios únicos (no clickable)">
              <TopMediaList items={charts.topSeries} />
            </ChartCard>
          </section>
        </>
      ) : null}
    </div>
  );
}


