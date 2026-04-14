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

type SeriesPoint = { label: string; value: number };
type DrillSeries = { userName: string; color: string; points: SeriesPoint[] };

type ChartKind = "sessions" | "bandwidth" | "shared";
type ChartType = "bar" | "area";

type FullWidthChart = {
  key: DrillChartKey;
  kind: ChartKind;
  chartType: ChartType;
  title: string;
  subtitle: string;
  points: SeriesPoint[];
  yAxis: string;
  xAxis: string;
};

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

    sessionsByDay: "Sesiones por día",
    sessionsByDaySub: "Últimos 7 días. Eje X: día de la semana. Eje Y: número de sesiones.",
    sessionsByWeek: "Sesiones por semana",
    sessionsByWeekSub: "Últimas 4 semanas ISO. Eje X: semana. Eje Y: número de sesiones.",
    sessionsByMonth: "Sesiones por mes",
    sessionsByMonthSub: "Últimos 12 meses. Eje X: mes. Eje Y: número de sesiones.",
    sessionsByYear: "Sesiones por año",
    sessionsByYearSub: "Histórico completo. Eje X: año. Eje Y: número de sesiones.",

    bandwidthByDay: "Ancho de banda por día",
    bandwidthByDaySub: "Promedio por sesión en los últimos 7 días.",
    bandwidthByWeek: "Ancho de banda por semana",
    bandwidthByWeekSub: "Promedio por sesión en las últimas 4 semanas ISO.",
    bandwidthByMonth: "Ancho de banda por mes",
    bandwidthByMonthSub: "Promedio por sesión en los últimos 12 meses.",
    bandwidthByYear: "Ancho de banda por año",
    bandwidthByYearSub: "Promedio por sesión por año en todo el histórico.",

    sharedByDay: "Contenido compartido por día",
    sharedByDaySub: "Total compartido por día (últimos 7 días).",
    sharedByWeek: "Contenido compartido por semana",
    sharedByWeekSub: "Total compartido por semana (últimas 4 semanas ISO).",
    sharedByMonth: "Contenido compartido por mes",
    sharedByMonthSub: "Total compartido por mes (últimos 12 meses).",
    sharedByYear: "Contenido compartido por año",
    sharedByYearSub: "Total compartido por año (histórico completo).",
    sharedByHour: "Contenido compartido por hora",
    sharedByHourSub: "Últimas 24 horas. Eje X: hora local. Eje Y: bytes compartidos.",

    peakHours: "Horas punta de visualización",
    peakHoursSub: "Distribución por hora local. Eje X: hora. Eje Y: sesiones iniciadas.",

    sourceDistribution: "Distribución por fuente",
    sourceDistributionSub: "Reparto de sesiones por proveedor.",
    topUsers: "Usuarios principales",
    topUsersSub: "Usuarios más activos por número de sesiones.",
    playByWeekday: "Reproducciones por día de la semana",
    playByWeekdaySub: "Sesiones agregadas por día de la semana.",
    playByMedia: "Reproducciones por tipo de medio",
    playByMediaSub: "Comparativa entre series y películas.",
    playByPlatform: "Reproducciones por plataforma",
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

    drillLegend: "Leyenda",
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

    sessionsByDay: "Sessions by Day",
    sessionsByDaySub: "Last 7 days. X-axis: weekday. Y-axis: session count.",
    sessionsByWeek: "Sessions by Week",
    sessionsByWeekSub: "Last 4 ISO weeks. X-axis: week. Y-axis: session count.",
    sessionsByMonth: "Sessions by Month",
    sessionsByMonthSub: "Last 12 months. X-axis: month. Y-axis: session count.",
    sessionsByYear: "Sessions by Year",
    sessionsByYearSub: "Full history. X-axis: year. Y-axis: session count.",

    bandwidthByDay: "Bandwidth by Day",
    bandwidthByDaySub: "Average per session over the last 7 days.",
    bandwidthByWeek: "Bandwidth by Week",
    bandwidthByWeekSub: "Average per session over the last 4 ISO weeks.",
    bandwidthByMonth: "Bandwidth by Month",
    bandwidthByMonthSub: "Average per session over the last 12 months.",
    bandwidthByYear: "Bandwidth by Year",
    bandwidthByYearSub: "Average per session by year over full history.",

    sharedByDay: "Shared Content by Day",
    sharedByDaySub: "Total shared per day (last 7 days).",
    sharedByWeek: "Shared Content by Week",
    sharedByWeekSub: "Total shared per week (last 4 ISO weeks).",
    sharedByMonth: "Shared Content by Month",
    sharedByMonthSub: "Total shared per month (last 12 months).",
    sharedByYear: "Shared Content by Year",
    sharedByYearSub: "Total shared per year (full history).",
    sharedByHour: "Shared Content by Hour",
    sharedByHourSub: "Last 24 hours. X-axis: local hour. Y-axis: shared bytes.",

    peakHours: "Peak Viewing Hours",
    peakHoursSub: "Local-hour distribution. X-axis: hour. Y-axis: started sessions.",

    sourceDistribution: "Source Distribution",
    sourceDistributionSub: "Session share by provider.",
    topUsers: "Top Users",
    topUsersSub: "Most active users by session count.",
    playByWeekday: "Play Count by Weekday",
    playByWeekdaySub: "Aggregated sessions by weekday.",
    playByMedia: "Play Count by Media Type",
    playByMediaSub: "Comparison between series and movies.",
    playByPlatform: "Play Count by Platform",
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

    drillLegend: "Legend",
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
    case "sessions_day":
      return buildByDay(overview.sessions_by_day, now, locale, (row) => row.sessions);
    case "sessions_week":
      return buildByWeek(overview.sessions_by_week, now, locale, (row) => row.sessions);
    case "sessions_month":
      return buildByMonth(overview.sessions_by_month, now, locale, (row) => row.sessions);
    case "sessions_year":
      return buildByYear(overview.sessions_by_year, now, (row) => row.sessions);

    case "bandwidth_day":
      return buildByDay(overview.bandwidth_by_day, now, locale, (row) => row.avg_bandwidth_bps);
    case "bandwidth_week":
      return buildByWeek(overview.bandwidth_by_week, now, locale, (row) => row.avg_bandwidth_bps);
    case "bandwidth_month":
      return buildByMonth(overview.bandwidth_by_month, now, locale, (row) => row.avg_bandwidth_bps);
    case "bandwidth_year":
      return buildByYear(overview.bandwidth_by_year, now, (row) => row.avg_bandwidth_bps);

    case "shared_day":
      return buildByDay(overview.shared_by_day, now, locale, (row) => row.shared_bytes);
    case "shared_week":
      return buildByWeek(overview.shared_by_week, now, locale, (row) => row.shared_bytes);
    case "shared_month":
      return buildByMonth(overview.shared_by_month, now, locale, (row) => row.shared_bytes);
    case "shared_year":
      return buildByYear(overview.shared_by_year, now, (row) => row.shared_bytes);
    case "shared_hour":
      return buildSharedHours(overview.shared_by_hour);

    case "peak_hours":
      return buildHours(overview.play_count_by_hour);

    default:
      return [];
  }
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

  useEffect(() => {
    void loadStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const onRefresh = () => {
      void loadStats();
    };
    window.addEventListener("streamfuse:refresh", onRefresh);
    return () => window.removeEventListener("streamfuse:refresh", onRefresh);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language]);

  const drillUsers = useMemo(() => users?.items.map((item) => item.user_name).slice(0, 6) ?? [], [users]);

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
              points: pointsByKey(selectedChart, data, now, locale),
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
  }, [selectedChart, drillUsers, locale]);

  useEffect(() => {
    if (!selectedChart) return;
    const target = document.getElementById(`drill-${selectedChart}`);
    if (!target) return;
    window.requestAnimationFrame(() => {
      target.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  }, [selectedChart]);

  if (loading) {
    return <LoadingState title={t.loading} />;
  }

  if (error) {
    return <ErrorState title={t.loadError} description={error} />;
  }

  if (!overview || !users || !media) {
    return <EmptyState title={t.noStatsTitle} description={t.noStatsDesc} />;
  }

  const now = new Date();

  const fullWidthCharts: FullWidthChart[] = [
    {
      key: "sessions_day",
      kind: "sessions",
      chartType: "bar",
      title: t.sessionsByDay,
      subtitle: t.sessionsByDaySub,
      points: buildByDay(overview.sessions_by_day, now, locale, (row) => row.sessions),
      yAxis: t.ySessions,
      xAxis: t.xDay,
    },
    {
      key: "sessions_week",
      kind: "sessions",
      chartType: "area",
      title: t.sessionsByWeek,
      subtitle: t.sessionsByWeekSub,
      points: buildByWeek(overview.sessions_by_week, now, locale, (row) => row.sessions),
      yAxis: t.ySessions,
      xAxis: t.xWeek,
    },
    {
      key: "sessions_month",
      kind: "sessions",
      chartType: "area",
      title: t.sessionsByMonth,
      subtitle: t.sessionsByMonthSub,
      points: buildByMonth(overview.sessions_by_month, now, locale, (row) => row.sessions),
      yAxis: t.ySessions,
      xAxis: t.xMonth,
    },
    {
      key: "sessions_year",
      kind: "sessions",
      chartType: "bar",
      title: t.sessionsByYear,
      subtitle: t.sessionsByYearSub,
      points: buildByYear(overview.sessions_by_year, now, (row) => row.sessions),
      yAxis: t.ySessions,
      xAxis: t.xYear,
    },

    {
      key: "bandwidth_day",
      kind: "bandwidth",
      chartType: "area",
      title: t.bandwidthByDay,
      subtitle: t.bandwidthByDaySub,
      points: buildByDay(overview.bandwidth_by_day, now, locale, (row) => row.avg_bandwidth_bps),
      yAxis: t.yBandwidth,
      xAxis: t.xDay,
    },
    {
      key: "bandwidth_week",
      kind: "bandwidth",
      chartType: "area",
      title: t.bandwidthByWeek,
      subtitle: t.bandwidthByWeekSub,
      points: buildByWeek(overview.bandwidth_by_week, now, locale, (row) => row.avg_bandwidth_bps),
      yAxis: t.yBandwidth,
      xAxis: t.xWeek,
    },
    {
      key: "bandwidth_month",
      kind: "bandwidth",
      chartType: "area",
      title: t.bandwidthByMonth,
      subtitle: t.bandwidthByMonthSub,
      points: buildByMonth(overview.bandwidth_by_month, now, locale, (row) => row.avg_bandwidth_bps),
      yAxis: t.yBandwidth,
      xAxis: t.xMonth,
    },
    {
      key: "bandwidth_year",
      kind: "bandwidth",
      chartType: "area",
      title: t.bandwidthByYear,
      subtitle: t.bandwidthByYearSub,
      points: buildByYear(overview.bandwidth_by_year, now, (row) => row.avg_bandwidth_bps),
      yAxis: t.yBandwidth,
      xAxis: t.xYear,
    },

    {
      key: "shared_day",
      kind: "shared",
      chartType: "bar",
      title: t.sharedByDay,
      subtitle: t.sharedByDaySub,
      points: buildByDay(overview.shared_by_day, now, locale, (row) => row.shared_bytes),
      yAxis: t.yShared,
      xAxis: t.xDay,
    },
    {
      key: "shared_week",
      kind: "shared",
      chartType: "area",
      title: t.sharedByWeek,
      subtitle: t.sharedByWeekSub,
      points: buildByWeek(overview.shared_by_week, now, locale, (row) => row.shared_bytes),
      yAxis: t.yShared,
      xAxis: t.xWeek,
    },
    {
      key: "shared_month",
      kind: "shared",
      chartType: "area",
      title: t.sharedByMonth,
      subtitle: t.sharedByMonthSub,
      points: buildByMonth(overview.shared_by_month, now, locale, (row) => row.shared_bytes),
      yAxis: t.yShared,
      xAxis: t.xMonth,
    },
    {
      key: "shared_year",
      kind: "shared",
      chartType: "bar",
      title: t.sharedByYear,
      subtitle: t.sharedByYearSub,
      points: buildByYear(overview.shared_by_year, now, (row) => row.shared_bytes),
      yAxis: t.yShared,
      xAxis: t.xYear,
    },

    {
      key: "peak_hours",
      kind: "sessions",
      chartType: "bar",
      title: t.peakHours,
      subtitle: t.peakHoursSub,
      points: buildHours(overview.play_count_by_hour),
      yAxis: t.ySessions,
      xAxis: t.xHour,
    },
    {
      key: "shared_hour",
      kind: "shared",
      chartType: "bar",
      title: t.sharedByHour,
      subtitle: t.sharedByHourSub,
      points: buildSharedHours(overview.shared_by_hour),
      yAxis: t.yShared,
      xAxis: t.xHour,
    },
  ];

  const platformBars = overview.play_count_by_platform.map((item) => ({ label: item.label, value: item.sessions }));

  const userBars = users.items.slice(0, 8).map((item) => ({
    label: item.user_name,
    value: item.sessions,
    hint: `${item.active_sessions} ${t.activeWord}`,
  }));

  const weekdayBars = overview.play_count_by_weekday.map((item) => ({ label: item.label, value: item.sessions }));

  const mediaRows = [
    {
      label: t.seriesLabel,
      seriesA: overview.play_count_by_media_type.find((item) => item.label.toLowerCase() === "series")?.sessions ?? 0,
      seriesB: overview.play_count_by_media_type.find((item) => item.label.toLowerCase() === "movie")?.sessions ?? 0,
    },
  ];

  const donutSlices = overview.source_distribution.map((item, index) => ({
    label: item.source,
    value: item.sessions,
    color: DRILL_USER_COLORS[index % DRILL_USER_COLORS.length],
  }));

  const renderValue = (chart: FullWidthChart) => {
    if (chart.kind === "bandwidth") return formatBps;
    if (chart.kind === "shared") return formatBytes;
    return (value: number) => `${formatInt(Math.round(value))} ${t.sessionsShort}`;
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-4xl text-white">{t.pageTitle}</h1>
        <p className="text-fg-muted">{t.pageSubtitle}</p>
      </header>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-5">
        <StatCard label={t.totalSessions} value={formatInt(overview.total_sessions)} hint={t.historical} />
        <StatCard label={t.activeNow} value={formatInt(overview.active_sessions)} hint={t.liveNow} />
        <StatCard label={t.totalShared} value={overview.total_shared_human} hint={t.cumulative} />
        <StatCard label={t.uniqueUsers} value={formatInt(overview.unique_users)} hint={t.allTime} />
        <StatCard label={t.totalWatchHours} value={`${overview.total_watch_hours.toLocaleString()} h`} hint={t.allTime} />
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <ChartCard title={t.sourceDistribution} subtitle={t.sourceDistributionSub}>
          <DonutChart slices={donutSlices} />
        </ChartCard>

        <ChartCard title={t.topUsers} subtitle={t.topUsersSub}>
          <HorizontalBars items={userBars} valueFormatter={(value) => `${formatInt(value)} ${t.sessionsShort}`} />
        </ChartCard>

        <ChartCard title={t.playByPlatform} subtitle={t.playByPlatformSub}>
          <HorizontalBars items={platformBars} valueFormatter={(value) => `${formatInt(value)} ${t.sessionsShort}`} />
        </ChartCard>

        <ChartCard title={t.playByWeekday} subtitle={t.playByWeekdaySub}>
          <VerticalBarChart
            points={weekdayBars}
            valueFormatter={(value) => `${formatInt(Math.round(value))} ${t.sessionsShort}`}
            yAxisTitle={t.ySessions}
            xAxisTitle={t.xDay}
          />
        </ChartCard>

        <ChartCard title={t.playByMedia} subtitle={t.playByMediaSub}>
          <GroupedBarChart
            items={mediaRows}
            seriesALabel={t.seriesLabel}
            seriesBLabel={t.moviesLabel}
            valueFormatter={(value) => `${formatInt(Math.round(value))} ${t.sessionsShort}`}
            yAxisTitle={t.ySessions}
            xAxisTitle={t.xDay}
          />
        </ChartCard>

        <ChartCard title={t.topMovies} subtitle={t.topMoviesSub}>
          <TopMediaList items={media.top_movies} usersLabel={t.usersLower} />
        </ChartCard>

        <ChartCard title={t.topSeries} subtitle={t.topSeriesSub}>
          <TopMediaList items={media.top_series} usersLabel={t.usersLower} />
        </ChartCard>
      </section>

      <section className="space-y-4">
        {fullWidthCharts.map((chart) => {
          const isSelected = selectedChart === chart.key;
          return (
            <div key={chart.key} className="space-y-3">
              <ChartCard title={chart.title} subtitle={chart.subtitle} onClick={() => setSelectedChart(chart.key)} selected={isSelected}>
                {chart.chartType === "area" ? (
                  <AreaChart
                    points={chart.points}
                    valueFormatter={renderValue(chart)}
                    yAxisTitle={chart.yAxis}
                    xAxisTitle={chart.xAxis}
                  />
                ) : (
                  <VerticalBarChart
                    points={chart.points}
                    valueFormatter={renderValue(chart)}
                    yAxisTitle={chart.yAxis}
                    xAxisTitle={chart.xAxis}
                    maxXTicks={chart.key.includes("hour") ? 8 : 12}
                  />
                )}
              </ChartCard>

              <div
                id={`drill-${chart.key}`}
                className={`overflow-hidden transition-all duration-300 ease-out ${isSelected ? "max-h-[580px] opacity-100" : "max-h-0 opacity-0"}`}
              >
                {isSelected ? (
                  <ChartCard title={`${t.drillTitlePrefix}: ${chart.title}`} subtitle={t.drillSubtitle}>
                    {drillLoading ? (
                      <LoadingState title={t.loadingDrill} />
                    ) : drillSeries && drillSeries.length > 0 ? (
                      <MultiLineChart
                        series={drillSeries.map((series) => ({
                          label: series.userName,
                          color: series.color,
                          points: series.points,
                        }))}
                        valueFormatter={renderValue(chart)}
                        yAxisTitle={chart.yAxis}
                        xAxisTitle={chart.xAxis}
                      />
                    ) : (
                      <EmptyState title={t.noDrillTitle} description={t.noDrillDesc} />
                    )}
                  </ChartCard>
                ) : null}
              </div>
            </div>
          );
        })}
      </section>
    </div>
  );
}

