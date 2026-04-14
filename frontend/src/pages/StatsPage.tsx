import { useEffect, useMemo, useState } from "react";

import { MediaStatsResponse, OverviewStats, UsersStatsResponse } from "@/types/stats";

import { apiGet } from "@/shared/api/client";
import { getStoredLanguage, normalizeLanguage, UiLanguage } from "@/shared/lib/i18n";
import { StatCard } from "@/shared/ui/cards/StatCard";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";

import { AreaChart } from "@/features/stats/components/AreaChart";
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
  | "peak_hours";

type SessionPeriod = "day" | "week" | "month" | "year";
type BandwidthPeriod = "day" | "week" | "month" | "year";
type SharedPeriod = "day" | "week" | "month" | "year" | "hour";

type SeriesPoint = { label: string; value: number };
type DrillSeries = { userName: string; color: string; points: SeriesPoint[] };

const DRILL_USER_COLORS = ["#22d3ee", "#f97316", "#a78bfa", "#34d399", "#f43f5e", "#eab308", "#60a5fa", "#fb7185"];

const TEXT = {
  es: {
    pageTitle: "Estadísticas",
    pageSubtitle: "Analítica detallada de sesiones, usuarios, medios y tendencias.",
    loading: "Cargando estadísticas",
    loadError: "No se pudieron cargar las estadísticas",
    noStatsTitle: "Sin estadísticas todavía",
    noStatsDesc: "Ingiere datos para desbloquear la analítica.",

    totalSessions: "Sesiones totales",
    activeNow: "Activas ahora",
    totalShared: "Total compartido",
    uniqueUsers: "Usuarios únicos",
    totalWatchHours: "Horas totales",
    historical: "Histórico",
    liveNow: "En directo",
    cumulative: "Acumulado",
    allTime: "Histórico",

    sessionsShort: "ses.",
    usersWord: "usuarios",
    activeWord: "activos",

    ySessions: "SESIONES",
    yBandwidth: "ANCHO DE BANDA",
    yShared: "COMPARTIDO",

    xDay: "DÍA",
    xWeek: "SEMANA",
    xMonth: "MES",
    xYear: "AÑO",
    xHour: "HORA",

    sectionDistributions: "Distribuciones",
    sectionUsersContent: "Usuarios y contenido",
    sectionTrends: "Tendencias",

    periodDay: "Diario",
    periodWeek: "Semanal",
    periodMonth: "Mensual",
    periodYear: "Anual",
    period24h: "24 h",

    trendSessions: "Sesiones",
    trendBandwidth: "Ancho de banda",
    trendShared: "Contenido compartido",

    sessionsByDaySub: "Últimos 7 días. Eje X: día de la semana. Eje Y: número de sesiones.",
    sessionsByWeekSub: "Últimas 4 semanas ISO. Eje X: semana. Eje Y: número de sesiones.",
    sessionsByMonthSub: "Últimos 12 meses. Eje X: mes. Eje Y: número de sesiones.",
    sessionsByYearSub: "Histórico completo. Eje X: año. Eje Y: número de sesiones.",

    bandwidthByDaySub: "Promedio por sesión en los últimos 7 días.",
    bandwidthByWeekSub: "Promedio por sesión en las últimas 4 semanas ISO.",
    bandwidthByMonthSub: "Promedio por sesión en los últimos 12 meses.",
    bandwidthByYearSub: "Promedio por sesión por año en todo el histórico.",

    sharedByDaySub: "Total compartido por día (últimos 7 días).",
    sharedByWeekSub: "Total compartido por semana (últimas 4 semanas ISO).",
    sharedByMonthSub: "Total compartido por mes (últimos 12 meses).",
    sharedByYearSub: "Total compartido por año (histórico completo).",
    sharedByHourSub: "Últimas 24 horas. Eje X: hora local. Eje Y: bytes compartidos.",

    peakHours: "Horas punta de visualización",
    peakHoursSub: "Distribución por hora local. Eje X: hora. Eje Y: sesiones iniciadas.",

    sourceDistribution: "Distribución por fuente",
    sourceDistributionSub: "Reparto de sesiones por proveedor.",
    topUsers: "Usuarios principales",
    topUsersSub: "Usuarios más activos por número de sesiones.",
    topUsersBw: "Usuarios por ancho de banda",
    topUsersBwSub: "Usuarios con mayor ancho de banda promedio por sesión.",
    playByWeekday: "Reproducciones por día",
    playByWeekdaySub: "Sesiones agregadas por día de la semana.",
    playByMedia: "Tipo de medio",
    playByMediaSub: "Comparativa entre series y películas.",
    playByPlatform: "Plataformas",
    playByPlatformSub: "Top plataformas por número de sesiones.",

    topMovies: "Top películas",
    topMoviesSub: "Ranking por usuarios únicos.",
    topSeries: "Top series",
    topSeriesSub: "Ranking por usuarios únicos.",

    seriesLabel: "Series",
    moviesLabel: "Películas",
    usersLower: "usuarios",

    drillTitlePrefix: "Comparativa por usuario",
    drillSubtitle: "Desglose superpuesto por usuario para esta métrica.",
    loadingDrill: "Cargando comparativa por usuario",
    noDrillTitle: "Sin datos por usuario",
    noDrillDesc: "No hay datos comparables para esta gráfica.",

    lastSeen: "Última actividad",
    now: "ahora",
  },
  en: {
    pageTitle: "Stats",
    pageSubtitle: "Detailed analytics for sessions, users, media, and trends.",
    loading: "Loading statistics",
    loadError: "Unable to load statistics",
    noStatsTitle: "No stats yet",
    noStatsDesc: "Ingest data to unlock analytics.",

    totalSessions: "Total Sessions",
    activeNow: "Active Now",
    totalShared: "Total Shared",
    uniqueUsers: "Unique Users",
    totalWatchHours: "Total Hours",
    historical: "Historical",
    liveNow: "Live now",
    cumulative: "Cumulative",
    allTime: "All time",

    sessionsShort: "ses.",
    usersWord: "users",
    activeWord: "active",

    ySessions: "SESSIONS",
    yBandwidth: "BANDWIDTH",
    yShared: "SHARED",

    xDay: "DAY",
    xWeek: "WEEK",
    xMonth: "MONTH",
    xYear: "YEAR",
    xHour: "HOUR",

    sectionDistributions: "Distributions",
    sectionUsersContent: "Users & Content",
    sectionTrends: "Trends",

    periodDay: "Daily",
    periodWeek: "Weekly",
    periodMonth: "Monthly",
    periodYear: "Yearly",
    period24h: "24 h",

    trendSessions: "Sessions",
    trendBandwidth: "Bandwidth",
    trendShared: "Shared Content",

    sessionsByDaySub: "Last 7 days. X-axis: weekday. Y-axis: session count.",
    sessionsByWeekSub: "Last 4 ISO weeks. X-axis: week. Y-axis: session count.",
    sessionsByMonthSub: "Last 12 months. X-axis: month. Y-axis: session count.",
    sessionsByYearSub: "Full history. X-axis: year. Y-axis: session count.",

    bandwidthByDaySub: "Average per session over the last 7 days.",
    bandwidthByWeekSub: "Average per session over the last 4 ISO weeks.",
    bandwidthByMonthSub: "Average per session over the last 12 months.",
    bandwidthByYearSub: "Average per session by year over full history.",

    sharedByDaySub: "Total shared per day (last 7 days).",
    sharedByWeekSub: "Total shared per week (last 4 ISO weeks).",
    sharedByMonthSub: "Total shared per month (last 12 months).",
    sharedByYearSub: "Total shared per year (full history).",
    sharedByHourSub: "Last 24 hours. X-axis: local hour. Y-axis: shared bytes.",

    peakHours: "Peak Viewing Hours",
    peakHoursSub: "Local-hour distribution. X-axis: hour. Y-axis: started sessions.",

    sourceDistribution: "Source Distribution",
    sourceDistributionSub: "Session share by provider.",
    topUsers: "Top Users",
    topUsersSub: "Most active users by session count.",
    topUsersBw: "Users by Bandwidth",
    topUsersBwSub: "Users with highest average bandwidth per session.",
    playByWeekday: "Plays by Weekday",
    playByWeekdaySub: "Aggregated sessions by weekday.",
    playByMedia: "Media Type",
    playByMediaSub: "Comparison between series and movies.",
    playByPlatform: "Platforms",
    playByPlatformSub: "Top platforms by session count.",

    topMovies: "Top Movies",
    topMoviesSub: "Ranking by unique viewers.",
    topSeries: "Top Series",
    topSeriesSub: "Ranking by unique viewers.",

    seriesLabel: "Series",
    moviesLabel: "Movies",
    usersLower: "users",

    drillTitlePrefix: "Per-user comparison",
    drillSubtitle: "Overlay by user for this metric.",
    loadingDrill: "Loading user comparison",
    noDrillTitle: "No per-user data",
    noDrillDesc: "No comparable data for this chart.",

    lastSeen: "Last seen",
    now: "now",
  },
} as const;

function formatInt(value: number): string {
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
  let unitIndex = 0;
  while (amount >= 1024 && unitIndex < units.length - 1) {
    amount /= 1024;
    unitIndex += 1;
  }
  if (unitIndex === 0) return `${Math.round(amount)} ${units[unitIndex]}`;
  return `${amount.toFixed(1)} ${units[unitIndex]}`;
}

function ymd(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function isoWeekKey(date: Date): string {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7));
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const week = Math.ceil((((d.getTime() - yearStart.getTime()) / 86_400_000) + 1) / 7);
  return `${d.getUTCFullYear()}-W${String(week).padStart(2, "0")}`;
}

function isoWeekLabel(key: string, locale: string): string {
  const match = /^(\d{4})-W(\d{2})$/.exec(key);
  if (!match) return key;
  const year = Number(match[1]);
  const week = Number(match[2]);
  const jan4 = new Date(Date.UTC(year, 0, 4));
  const jan4Day = jan4.getUTCDay() || 7;
  const week1Monday = new Date(jan4);
  week1Monday.setUTCDate(jan4.getUTCDate() - jan4Day + 1);
  const targetMonday = new Date(week1Monday);
  targetMonday.setUTCDate(week1Monday.getUTCDate() + (week - 1) * 7);
  const month = targetMonday.toLocaleDateString(locale, { month: "short" });
  return `W${week} ${month} ${year}`;
}

function monthLabel(key: string, locale: string): string {
  const [year, month] = key.split("-");
  const date = new Date(Number(year), Number(month) - 1, 1);
  return date.toLocaleDateString(locale, { month: "short", year: "numeric" });
}

function weekdayLabel(date: Date, locale: string): string {
  return date.toLocaleDateString(locale, { weekday: "long" });
}

function buildByDay<T extends { day: string }>(rows: T[], now: Date, locale: string, pick: (row: T) => number): SeriesPoint[] {
  const map = new Map(rows.map((row) => [row.day, pick(row)]));
  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(now);
    date.setDate(now.getDate() - (6 - index));
    const key = ymd(date);
    return { label: weekdayLabel(date, locale), value: map.get(key) ?? 0 };
  });
}

function buildByWeek<T extends { day: string }>(rows: T[], now: Date, locale: string, pick: (row: T) => number): SeriesPoint[] {
  const map = new Map(rows.map((row) => [row.day, pick(row)]));
  return Array.from({ length: 4 }, (_, index) => {
    const date = new Date(now);
    date.setDate(now.getDate() - (3 - index) * 7);
    const key = isoWeekKey(date);
    return { label: isoWeekLabel(key, locale), value: map.get(key) ?? 0 };
  });
}

function buildByMonth<T extends { day: string }>(rows: T[], now: Date, locale: string, pick: (row: T) => number): SeriesPoint[] {
  const map = new Map(rows.map((row) => [row.day, pick(row)]));
  return Array.from({ length: 12 }, (_, index) => {
    const date = new Date(now.getFullYear(), now.getMonth() - (11 - index), 1);
    const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
    return { label: monthLabel(key, locale), value: map.get(key) ?? 0 };
  });
}

function buildByYear<T extends { day: string }>(rows: T[], now: Date, pick: (row: T) => number): SeriesPoint[] {
  const map = new Map(rows.map((row) => [row.day, pick(row)]));
  const keys = Array.from(new Set([...rows.map((row) => row.day), String(now.getFullYear())])).sort();
  return keys.map((key) => ({ label: key, value: map.get(key) ?? 0 }));
}

function buildHours(rows: Array<{ hour: number; sessions: number }>): SeriesPoint[] {
  return Array.from({ length: 24 }, (_, hour) => {
    const row = rows.find((item) => item.hour === hour);
    return { label: `${String(hour).padStart(2, "0")}:00`, value: row?.sessions ?? 0 };
  });
}

function buildSharedHours(rows: Array<{ hour: number; shared_bytes: number }>): SeriesPoint[] {
  return Array.from({ length: 24 }, (_, hour) => {
    const row = rows.find((item) => item.hour === hour);
    return { label: `${String(hour).padStart(2, "0")}:00`, value: row?.shared_bytes ?? 0 };
  });
}

function pointsByKey(key: DrillChartKey, overview: OverviewStats, now: Date, locale: string): SeriesPoint[] {
  switch (key) {
    case "sessions_day":   return buildByDay(overview.sessions_by_day, now, locale, (r) => r.sessions);
    case "sessions_week":  return buildByWeek(overview.sessions_by_week, now, locale, (r) => r.sessions);
    case "sessions_month": return buildByMonth(overview.sessions_by_month, now, locale, (r) => r.sessions);
    case "sessions_year":  return buildByYear(overview.sessions_by_year, now, (r) => r.sessions);
    case "bandwidth_day":   return buildByDay(overview.bandwidth_by_day, now, locale, (r) => r.avg_bandwidth_bps);
    case "bandwidth_week":  return buildByWeek(overview.bandwidth_by_week, now, locale, (r) => r.avg_bandwidth_bps);
    case "bandwidth_month": return buildByMonth(overview.bandwidth_by_month, now, locale, (r) => r.avg_bandwidth_bps);
    case "bandwidth_year":  return buildByYear(overview.bandwidth_by_year, now, (r) => r.avg_bandwidth_bps);
    case "shared_day":   return buildByDay(overview.shared_by_day, now, locale, (r) => r.shared_bytes);
    case "shared_week":  return buildByWeek(overview.shared_by_week, now, locale, (r) => r.shared_bytes);
    case "shared_month": return buildByMonth(overview.shared_by_month, now, locale, (r) => r.shared_bytes);
    case "shared_year":  return buildByYear(overview.shared_by_year, now, (r) => r.shared_bytes);
    case "shared_hour":  return buildSharedHours(overview.shared_by_hour);
    case "peak_hours":   return buildHours(overview.play_count_by_hour);
    default: return [];
  }
}

function SectionDivider({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 pt-2">
      <span className="whitespace-nowrap text-[11px] font-semibold uppercase tracking-[0.12em] text-fg-muted">
        {label}
      </span>
      <div className="flex-1 border-t border-white/10" />
    </div>
  );
}

export function StatsPage() {
  const [overview, setOverview] = useState<OverviewStats | null>(null);
  const [users, setUsers] = useState<UsersStatsResponse | null>(null);
  const [media, setMedia] = useState<MediaStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [language, setLanguage] = useState<UiLanguage>(getStoredLanguage());
  const [selectedChart, setSelectedChart] = useState<DrillChartKey | null>(null);
  const [drillSeries, setDrillSeries] = useState<DrillSeries[] | null>(null);
  const [drillLoading, setDrillLoading] = useState(false);

  const [sessionsPeriod, setSessionsPeriod] = useState<SessionPeriod>("week");
  const [bandwidthPeriod, setBandwidthPeriod] = useState<BandwidthPeriod>("week");
  const [sharedPeriod, setSharedPeriod] = useState<SharedPeriod>("week");

  const t = TEXT[language];
  const locale = language === "en" ? "en-US" : "es-ES";

  useEffect(() => {
    const onLanguageChanged = (event: Event) => {
      const detail = (event as CustomEvent<{ language?: string }>).detail;
      setLanguage(normalizeLanguage(detail?.language));
    };
    window.addEventListener("streamfuse:language-changed", onLanguageChanged);
    return () => window.removeEventListener("streamfuse:language-changed", onLanguageChanged);
  }, []);

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
    } catch {
      setError(t.loadError);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void loadStats(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const onRefresh = () => { void loadStats(); };
    window.addEventListener("streamfuse:refresh", onRefresh);
    return () => window.removeEventListener("streamfuse:refresh", onRefresh);
  }, [language]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSessionsPeriod = (p: SessionPeriod) => {
    setSessionsPeriod(p);
    if (selectedChart?.startsWith("sessions_")) setSelectedChart(`sessions_${p}` as DrillChartKey);
  };

  const handleBandwidthPeriod = (p: BandwidthPeriod) => {
    setBandwidthPeriod(p);
    if (selectedChart?.startsWith("bandwidth_")) setSelectedChart(`bandwidth_${p}` as DrillChartKey);
  };

  const handleSharedPeriod = (p: SharedPeriod) => {
    setSharedPeriod(p);
    if (selectedChart?.startsWith("shared_")) setSelectedChart(`shared_${p}` as DrillChartKey);
  };

  const drillUsers = useMemo(() => users?.items.map((item) => item.user_name).slice(0, 6) ?? [], [users]);

  useEffect(() => {
    const run = async () => {
      if (!selectedChart || drillUsers.length === 0) { setDrillSeries(null); return; }
      try {
        setDrillLoading(true);
        const now = new Date();
        const rows = await Promise.all(
          drillUsers.map(async (userName, index) => {
            const query = `?user_name=${encodeURIComponent(userName)}`;
            const data = await apiGet<OverviewStats>(`/stats/overview${query}`);
            return { userName, color: DRILL_USER_COLORS[index % DRILL_USER_COLORS.length], points: pointsByKey(selectedChart, data, now, locale) } as DrillSeries;
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
  }, [selectedChart, drillUsers, locale]);

  useEffect(() => {
    if (!selectedChart) return;
    const target = document.getElementById(`drill-${selectedChart}`);
    if (!target) return;
    window.requestAnimationFrame(() => { target.scrollIntoView({ behavior: "smooth", block: "nearest" }); });
  }, [selectedChart]);

  if (loading) return <LoadingState title={t.loading} />;
  if (error) return <ErrorState title={t.loadError} description={error} />;
  if (!overview || !users || !media) return <EmptyState title={t.noStatsTitle} description={t.noStatsDesc} />;

  const now = new Date();

  // --- Derived data ---
  const platformBars = overview.play_count_by_platform.map((item) => ({ label: item.label, value: item.sessions }));
  const userBars = users.items.slice(0, 8).map((item) => ({ label: item.user_name, value: item.sessions, hint: `${item.active_sessions} ${t.activeWord}` }));
  const userBwBars = users.items
    .filter((item) => item.avg_bandwidth_bps != null && item.avg_bandwidth_bps > 0)
    .sort((a, b) => (b.avg_bandwidth_bps ?? 0) - (a.avg_bandwidth_bps ?? 0))
    .slice(0, 8)
    .map((item) => ({ label: item.user_name, value: item.avg_bandwidth_bps ?? 0 }));
  const weekdayBars = overview.play_count_by_weekday.map((item) => ({ label: item.label, value: item.sessions }));
  const mediaRows = [{
    label: t.seriesLabel,
    seriesA: overview.play_count_by_media_type.find((item) => item.label.toLowerCase() === "series")?.sessions ?? 0,
    seriesB: overview.play_count_by_media_type.find((item) => item.label.toLowerCase() === "movie")?.sessions ?? 0,
  }];
  const donutSlices = overview.source_distribution.map((item, index) => ({ label: item.source, value: item.sessions, color: DRILL_USER_COLORS[index % DRILL_USER_COLORS.length] }));

  // --- Trend chart helpers ---
  const sessionsChartKey = `sessions_${sessionsPeriod}` as DrillChartKey;
  const bandwidthChartKey = `bandwidth_${bandwidthPeriod}` as DrillChartKey;
  const sharedChartKey = `shared_${sharedPeriod}` as DrillChartKey;

  const sessionsPoints = pointsByKey(sessionsChartKey, overview, now, locale);
  const bandwidthPoints = pointsByKey(bandwidthChartKey, overview, now, locale);
  const sharedPoints = pointsByKey(sharedChartKey, overview, now, locale);
  const peakHoursPoints = buildHours(overview.play_count_by_hour);

  const sessionsChartIsArea = sessionsPeriod === "week" || sessionsPeriod === "month";
  const bandwidthChartIsArea = true;
  const sharedChartIsArea = sharedPeriod === "week" || sharedPeriod === "month";

  const sessionsSubtitles: Record<SessionPeriod, string> = {
    day: t.sessionsByDaySub, week: t.sessionsByWeekSub, month: t.sessionsByMonthSub, year: t.sessionsByYearSub,
  };
  const bandwidthSubtitles: Record<BandwidthPeriod, string> = {
    day: t.bandwidthByDaySub, week: t.bandwidthByWeekSub, month: t.bandwidthByMonthSub, year: t.bandwidthByYearSub,
  };
  const sharedSubtitles: Record<SharedPeriod, string> = {
    day: t.sharedByDaySub, week: t.sharedByWeekSub, month: t.sharedByMonthSub, year: t.sharedByYearSub, hour: t.sharedByHourSub,
  };
  const xAxisLabel: Record<string, string> = {
    day: t.xDay, week: t.xWeek, month: t.xMonth, year: t.xYear, hour: t.xHour,
  };
  const formatSessions = (value: number) => `${formatInt(Math.round(value))} ${t.sessionsShort}`;

  function PeriodTabs<T extends string>({
    periods,
    labels,
    selected,
    onChange,
  }: {
    periods: T[];
    labels: Record<T, string>;
    selected: T;
    onChange: (p: T) => void;
  }) {
    return (
      <div className="flex gap-0.5 rounded-lg bg-white/5 p-0.5" onClick={(e) => e.stopPropagation()}>
        {periods.map((p) => (
          <button
            key={p}
            onClick={(e) => { e.stopPropagation(); onChange(p); }}
            className={`rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors ${selected === p ? "bg-cyan-500/20 text-cyan-300" : "text-fg-muted hover:text-fg"}`}
          >
            {labels[p]}
          </button>
        ))}
      </div>
    );
  }

  function DrillPanel({ chartKey, valueFormatter, yAxis, xAxis }: {
    chartKey: DrillChartKey;
    valueFormatter: (v: number) => string;
    yAxis: string;
    xAxis: string;
  }) {
    const isSelected = selectedChart === chartKey;
    return (
      <div
        id={`drill-${chartKey}`}
        className={`overflow-hidden transition-all duration-300 ease-out ${isSelected ? "max-h-[580px] opacity-100" : "max-h-0 opacity-0"}`}
      >
        {isSelected ? (
          <ChartCard title={`${t.drillTitlePrefix}`} subtitle={t.drillSubtitle}>
            {drillLoading ? (
              <LoadingState title={t.loadingDrill} />
            ) : drillSeries && drillSeries.length > 0 ? (
              <MultiLineChart
                series={drillSeries.map((s) => ({ label: s.userName, color: s.color, points: s.points }))}
                valueFormatter={valueFormatter}
                yAxisTitle={yAxis}
                xAxisTitle={xAxis}
              />
            ) : (
              <EmptyState title={t.noDrillTitle} description={t.noDrillDesc} />
            )}
          </ChartCard>
        ) : null}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-4xl text-white">{t.pageTitle}</h1>
        <p className="text-fg-muted">{t.pageSubtitle}</p>
      </header>

      {/* KPI cards */}
      <section className="grid grid-cols-1 gap-4 md:grid-cols-5">
        <StatCard label={t.totalSessions} value={formatInt(overview.total_sessions)} hint={t.historical} />
        <StatCard label={t.activeNow} value={formatInt(overview.active_sessions)} hint={t.liveNow} />
        <StatCard label={t.totalShared} value={overview.total_shared_human} hint={t.cumulative} />
        <StatCard label={t.uniqueUsers} value={formatInt(overview.unique_users)} hint={t.allTime} />
        <StatCard label={t.totalWatchHours} value={`${overview.total_watch_hours.toLocaleString()} h`} hint={t.allTime} />
      </section>

      {/* ── Distribuciones ─────────────────────────────────────────── */}
      <SectionDivider label={t.sectionDistributions} />

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <ChartCard title={t.sourceDistribution} subtitle={t.sourceDistributionSub}>
          <DonutChart slices={donutSlices} />
        </ChartCard>
        <ChartCard title={t.playByMedia} subtitle={t.playByMediaSub}>
          <GroupedBarChart
            items={mediaRows}
            seriesALabel={t.seriesLabel}
            seriesBLabel={t.moviesLabel}
            valueFormatter={formatSessions}
            yAxisTitle={t.ySessions}
            xAxisTitle={t.xDay}
          />
        </ChartCard>
        <ChartCard title={t.playByPlatform} subtitle={t.playByPlatformSub}>
          <HorizontalBars items={platformBars} valueFormatter={formatSessions} />
        </ChartCard>
      </section>

      <ChartCard title={t.peakHours} subtitle={t.peakHoursSub} onClick={() => setSelectedChart((prev) => prev === "peak_hours" ? null : "peak_hours")} selected={selectedChart === "peak_hours"}>
        <VerticalBarChart points={peakHoursPoints} valueFormatter={formatSessions} yAxisTitle={t.ySessions} xAxisTitle={t.xHour} maxXTicks={8} />
      </ChartCard>
      <DrillPanel chartKey="peak_hours" valueFormatter={formatSessions} yAxis={t.ySessions} xAxis={t.xHour} />

      {/* ── Usuarios y contenido ───────────────────────────────────── */}
      <SectionDivider label={t.sectionUsersContent} />

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <ChartCard title={t.topUsers} subtitle={t.topUsersSub}>
          <HorizontalBars items={userBars} valueFormatter={formatSessions} />
        </ChartCard>
        <ChartCard title={t.topUsersBw} subtitle={t.topUsersBwSub}>
          <HorizontalBars items={userBwBars} valueFormatter={formatBps} />
        </ChartCard>
        <ChartCard title={t.playByWeekday} subtitle={t.playByWeekdaySub}>
          <VerticalBarChart points={weekdayBars} valueFormatter={formatSessions} yAxisTitle={t.ySessions} xAxisTitle={t.xDay} />
        </ChartCard>
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ChartCard title={t.topMovies} subtitle={t.topMoviesSub}>
          <TopMediaList items={media.top_movies} usersLabel={t.usersLower} />
        </ChartCard>
        <ChartCard title={t.topSeries} subtitle={t.topSeriesSub}>
          <TopMediaList items={media.top_series} usersLabel={t.usersLower} />
        </ChartCard>
      </section>

      {/* ── Tendencias ─────────────────────────────────────────────── */}
      <SectionDivider label={t.sectionTrends} />

      {/* Sessions */}
      <div className="space-y-3">
        <ChartCard
          title={t.trendSessions}
          subtitle={sessionsSubtitles[sessionsPeriod]}
          onClick={() => setSelectedChart((prev) => prev === sessionsChartKey ? null : sessionsChartKey)}
          selected={selectedChart === sessionsChartKey}
          rightSlot={
            <PeriodTabs
              periods={["day", "week", "month", "year"] as SessionPeriod[]}
              labels={{ day: t.periodDay, week: t.periodWeek, month: t.periodMonth, year: t.periodYear }}
              selected={sessionsPeriod}
              onChange={handleSessionsPeriod}
            />
          }
        >
          {sessionsChartIsArea ? (
            <AreaChart points={sessionsPoints} valueFormatter={formatSessions} yAxisTitle={t.ySessions} xAxisTitle={xAxisLabel[sessionsPeriod]} />
          ) : (
            <VerticalBarChart points={sessionsPoints} valueFormatter={formatSessions} yAxisTitle={t.ySessions} xAxisTitle={xAxisLabel[sessionsPeriod]} />
          )}
        </ChartCard>
        <DrillPanel chartKey={sessionsChartKey} valueFormatter={formatSessions} yAxis={t.ySessions} xAxis={xAxisLabel[sessionsPeriod]} />
      </div>

      {/* Bandwidth */}
      <div className="space-y-3">
        <ChartCard
          title={t.trendBandwidth}
          subtitle={bandwidthSubtitles[bandwidthPeriod]}
          onClick={() => setSelectedChart((prev) => prev === bandwidthChartKey ? null : bandwidthChartKey)}
          selected={selectedChart === bandwidthChartKey}
          rightSlot={
            <PeriodTabs
              periods={["day", "week", "month", "year"] as BandwidthPeriod[]}
              labels={{ day: t.periodDay, week: t.periodWeek, month: t.periodMonth, year: t.periodYear }}
              selected={bandwidthPeriod}
              onChange={handleBandwidthPeriod}
            />
          }
        >
          {bandwidthChartIsArea ? (
            <AreaChart points={bandwidthPoints} valueFormatter={formatBps} yAxisTitle={t.yBandwidth} xAxisTitle={xAxisLabel[bandwidthPeriod]} />
          ) : (
            <VerticalBarChart points={bandwidthPoints} valueFormatter={formatBps} yAxisTitle={t.yBandwidth} xAxisTitle={xAxisLabel[bandwidthPeriod]} />
          )}
        </ChartCard>
        <DrillPanel chartKey={bandwidthChartKey} valueFormatter={formatBps} yAxis={t.yBandwidth} xAxis={xAxisLabel[bandwidthPeriod]} />
      </div>

      {/* Shared */}
      <div className="space-y-3">
        <ChartCard
          title={t.trendShared}
          subtitle={sharedSubtitles[sharedPeriod]}
          onClick={() => setSelectedChart((prev) => prev === sharedChartKey ? null : sharedChartKey)}
          selected={selectedChart === sharedChartKey}
          rightSlot={
            <PeriodTabs
              periods={["day", "week", "month", "year", "hour"] as SharedPeriod[]}
              labels={{ day: t.periodDay, week: t.periodWeek, month: t.periodMonth, year: t.periodYear, hour: t.period24h }}
              selected={sharedPeriod}
              onChange={handleSharedPeriod}
            />
          }
        >
          {sharedChartIsArea ? (
            <AreaChart points={sharedPoints} valueFormatter={formatBytes} yAxisTitle={t.yShared} xAxisTitle={xAxisLabel[sharedPeriod]} />
          ) : (
            <VerticalBarChart points={sharedPoints} valueFormatter={formatBytes} yAxisTitle={t.yShared} xAxisTitle={xAxisLabel[sharedPeriod]} maxXTicks={sharedPeriod === "hour" ? 8 : 12} />
          )}
        </ChartCard>
        <DrillPanel chartKey={sharedChartKey} valueFormatter={formatBytes} yAxis={t.yShared} xAxis={xAxisLabel[sharedPeriod]} />
      </div>
    </div>
  );
}
