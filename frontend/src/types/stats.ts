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
  total_shared_bytes: number;
  total_shared_human: string;
  sessions_by_day: Array<{ day: string; sessions: number }>;
  sessions_by_month: Array<{ day: string; sessions: number }>;
  sessions_by_year: Array<{ day: string; sessions: number }>;
  bandwidth_by_day: Array<{ day: string; avg_bandwidth_bps: number }>;
  bandwidth_by_month: Array<{ day: string; avg_bandwidth_bps: number }>;
  bandwidth_by_year: Array<{ day: string; avg_bandwidth_bps: number }>;
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

export type UserInsightItem = {
  user_name: string;
  total_sessions: number;
  movie_sessions: number;
  episode_sessions: number;
  total_watch_hours: number;
  movie_watch_hours: number;
  episode_watch_hours: number;
  unique_titles_monthly: number;
  unique_movies_monthly: number;
  unique_series_monthly: number;
  last_seen_at: string | null;
};

export type UserInsightsResponse = {
  items: UserInsightItem[];
  leaders: {
    most_sessions_user: { user_name: string; value: number };
    most_watch_hours_user: { user_name: string; value: number };
    most_movies_user: { user_name: string; value: number };
    most_series_user: { user_name: string; value: number };
  };
  peak_hours: Array<{ hour: number; sessions: number }>;
  timezone: string;
  play_count_rule: string;
};
