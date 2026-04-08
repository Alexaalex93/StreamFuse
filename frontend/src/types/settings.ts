export type StreamFuseSettings = {
  tautulli_url: string;
  tautulli_api_key_set: boolean;
  tautulli_api_key_masked: string | null;
  sftpgo_url: string;
  sftpgo_token_set: boolean;
  sftpgo_token_masked: string | null;
  sftpgo_logs_path: string | null;
  sftpgo_path_mappings: string[];
  polling_frequency_seconds: number;
  timezone: string;
  media_root_paths: string[];
  preferred_poster_names: string[];
  placeholder_path: string;
  history_retention_days: number;
  updated_at: string | null;
};

export type StreamFuseSettingsUpdate = {
  tautulli_url?: string;
  tautulli_api_key?: string;
  sftpgo_url?: string;
  sftpgo_token?: string;
  sftpgo_logs_path?: string | null;
  sftpgo_path_mappings?: string[];
  polling_frequency_seconds?: number;
  timezone?: string;
  media_root_paths?: string[];
  preferred_poster_names?: string[];
  placeholder_path?: string;
  history_retention_days?: number;
};
