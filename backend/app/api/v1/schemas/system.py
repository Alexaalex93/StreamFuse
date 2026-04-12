from datetime import datetime

from pydantic import BaseModel


class SystemIdentity(BaseModel):
    cpu_model: str | None = None
    gpu_model: str | None = None
    ram_total_bytes: int | None = None


class SystemLoad(BaseModel):
    cpu_percent: float | None = None
    gpu_percent: float | None = None
    ram_used_bytes: int | None = None
    ram_free_bytes: int | None = None


class SystemNetwork(BaseModel):
    inbound_bps: float | None = None
    outbound_bps: float | None = None


class SystemEnergy(BaseModel):
    power_watts: float | None = None
    current_rate_eur_kwh: float | None = None
    current_cost_per_hour_eur: float | None = None
    estimated_month_cost_eur: float | None = None


class SystemTransfer(BaseModel):
    total_shared_bytes: int | None = None
    total_shared_human: str | None = None
    total_bandwidth_bps: float | None = None
    total_bandwidth_human: str | None = None


class SystemMetricsResponse(BaseModel):
    enabled: bool
    source_available: bool
    sampled_at: datetime | None = None
    identity: SystemIdentity
    load: SystemLoad
    network: SystemNetwork
    energy: SystemEnergy
    transfer: SystemTransfer
