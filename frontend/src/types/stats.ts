export type DailyPoint = {
  day: string;
  sessions?: number;
  avg_bandwidth_bps?: number;
};

export type SourceCount = {
  source: "tautulli" | "sftpgo" | string;
  sessions: number;
};

export type OverviewStats = {
  total_sessions: number;
  active_sessions: number;
  ended_sessions: number;
  stale_sessions: number;
  sessions_by_day: Array<{ day: string; sessions: number }>;
  bandwidth_by_day: Array<{ day: string; avg_bandwidth_bps: number }>;
  source_distribution: SourceCount[];
  active_by_source: SourceCount[];
};

export type TopUser = {
  user_name: string;
  sessions: number;
  active_sessions: number;
  avg_bandwidth_bps: number | null;
  last_seen_at: string | null;
};

export type UsersStatsResponse = {
  items: TopUser[];
};

export type TopMediaItem = {
  title: string;
  media_type: string;
  sessions: number;
  unique_users: number;
  avg_bandwidth_bps: number | null;
};

export type MediaStatsResponse = {
  top_movies: TopMediaItem[];
  top_series: TopMediaItem[];
};
