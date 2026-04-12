export type SystemMetricsResponse = {
  enabled: boolean;
  source_available: boolean;
  sampled_at: string | null;
  identity: {
    cpu_model: string | null;
    gpu_model: string | null;
    ram_total_bytes: number | null;
  };
  load: {
    cpu_percent: number | null;
    gpu_percent: number | null;
    ram_used_bytes: number | null;
    ram_free_bytes: number | null;
  };
  network: {
    inbound_bps: number | null;
    outbound_bps: number | null;
  };
  energy: {
    power_watts: number | null;
    current_rate_eur_kwh: number | null;
    current_cost_per_hour_eur: number | null;
    estimated_month_cost_eur: number | null;
  };
  transfer: {
    total_shared_bytes: number | null;
    total_shared_human: string | null;
    total_bandwidth_bps: number | null;
    total_bandwidth_human: string | null;
  };
};
