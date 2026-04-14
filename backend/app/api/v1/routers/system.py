from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_db
from app.api.v1.schemas.system import (
    SystemEnergy,
    SystemIdentity,
    SystemLoad,
    SystemMetricsResponse,
    SystemNetwork,
    SystemTransfer,
)
from app.core.config import Settings
from app.persistence.models.unified_stream_session import UnifiedStreamSessionModel
from app.persistence.repositories.unified_stream_session_repository import (
    SessionQueryFilters,
    UnifiedStreamSessionRepository,
)
from app.services.nic_rate_monitor import get_nic_rates
from app.services.stats_service import StatsService
from app.services.unraid_metrics_service import UnraidMetricsService, format_bps, format_bytes

router = APIRouter(prefix="/system")


@router.get("/metrics", response_model=SystemMetricsResponse)
def get_system_metrics(
    db: Session = Depends(get_db),
    app_settings: Settings = Depends(get_app_settings),
) -> SystemMetricsResponse:
    service = UnraidMetricsService(db, app_settings)
    data = service.get_metrics()

    # Real NIC traffic (bytes delta / elapsed seconds via psutil).
    # First call returns (0.0, 0.0) while the baseline is established;
    # fall back to Unraid JSON values if available, then to 0.
    nic_out_bps, nic_in_bps = get_nic_rates()
    if nic_out_bps == 0.0 and data.outbound_bps:
        nic_out_bps = data.outbound_bps
    if nic_in_bps == 0.0 and data.inbound_bps:
        nic_in_bps = data.inbound_bps

    # Media-only bandwidth — sum of active StreamFuse session estimates.
    # Kept separately for the transfer block (excludes unrelated host traffic).
    session_repo = UnifiedStreamSessionRepository(db)
    active_rows = session_repo.list_active(SessionQueryFilters(limit=1000))
    media_outbound_bps = float(sum(row.bandwidth_bps or 0 for row in active_rows))

    # Total shared strictly from StreamFuse session history (Samba + SFTPGo + Tautulli/Plex).
    shared_rows = db.execute(
        select(
            UnifiedStreamSessionModel.source,
            UnifiedStreamSessionModel.status,
            UnifiedStreamSessionModel.raw_payload,
            UnifiedStreamSessionModel.file_path,
            UnifiedStreamSessionModel.started_at,
            UnifiedStreamSessionModel.ended_at,
            UnifiedStreamSessionModel.updated_at,
            UnifiedStreamSessionModel.bandwidth_bps,
            UnifiedStreamSessionModel.progress_percent,
            UnifiedStreamSessionModel.duration_ms,
        )
    ).all()
    total_shared_bytes = 0
    for row in shared_rows:
        shared_bytes = StatsService._extract_shared_bytes(row)
        if shared_bytes > 0:
            total_shared_bytes += int(shared_bytes)

    return SystemMetricsResponse(
        enabled=data.enabled,
        source_available=data.source_available,
        sampled_at=data.sampled_at,
        identity=SystemIdentity(
            cpu_model=data.cpu_model,
            gpu_model=data.gpu_model,
            ram_total_bytes=data.ram_total_bytes,
        ),
        load=SystemLoad(
            cpu_percent=data.cpu_percent,
            gpu_percent=data.gpu_percent,
            ram_used_bytes=data.ram_used_bytes,
            ram_free_bytes=data.ram_free_bytes,
        ),
        network=SystemNetwork(
            inbound_bps=nic_in_bps,
            outbound_bps=nic_out_bps,
        ),
        energy=SystemEnergy(
            power_watts=data.power_watts,
            current_rate_eur_kwh=data.current_rate_eur_kwh,
            current_cost_per_hour_eur=data.current_cost_per_hour_eur,
            estimated_month_cost_eur=data.estimated_month_cost_eur,
        ),
        transfer=SystemTransfer(
            total_shared_bytes=total_shared_bytes,
            total_shared_human=format_bytes(total_shared_bytes),
            total_bandwidth_bps=media_outbound_bps,
            total_bandwidth_human=format_bps(media_outbound_bps),
        ),
    )
