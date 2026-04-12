from __future__ import annotations

import calendar
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.persistence.repositories.app_setting_repository import AppSettingRepository
from app.services.settings_service import SettingsService


@dataclass(slots=True)
class SystemMetrics:
    enabled: bool
    source_available: bool
    sampled_at: datetime | None
    cpu_model: str | None
    gpu_model: str | None
    ram_total_bytes: int | None
    cpu_percent: float | None
    gpu_percent: float | None
    ram_used_bytes: int | None
    ram_free_bytes: int | None
    inbound_bps: float | None
    outbound_bps: float | None
    power_watts: float | None
    current_rate_eur_kwh: float | None
    current_cost_per_hour_eur: float | None
    estimated_month_cost_eur: float | None
    total_shared_bytes: int | None
    total_bandwidth_bps: float | None


class UnraidMetricsService:
    def __init__(self, db: Session, app_settings: Settings) -> None:
        self.db = db
        self.app_settings = app_settings
        self.settings_service = SettingsService(AppSettingRepository(db), app_settings)

    def get_metrics(self) -> SystemMetrics:
        cfg = self.settings_service.get_settings()
        if not cfg.unraid_metrics_enabled:
            return SystemMetrics(
                enabled=False,
                source_available=False,
                sampled_at=None,
                cpu_model=None,
                gpu_model=None,
                ram_total_bytes=None,
                cpu_percent=None,
                gpu_percent=None,
                ram_used_bytes=None,
                ram_free_bytes=None,
                inbound_bps=None,
                outbound_bps=None,
                power_watts=None,
                current_rate_eur_kwh=None,
                current_cost_per_hour_eur=None,
                estimated_month_cost_eur=None,
                total_shared_bytes=None,
                total_bandwidth_bps=None,
            )

        payload = self._read_json(cfg.unraid_metrics_json_path or "")
        if payload is None:
            return SystemMetrics(
                enabled=True,
                source_available=False,
                sampled_at=None,
                cpu_model=None,
                gpu_model=None,
                ram_total_bytes=None,
                cpu_percent=None,
                gpu_percent=None,
                ram_used_bytes=None,
                ram_free_bytes=None,
                inbound_bps=None,
                outbound_bps=None,
                power_watts=None,
                current_rate_eur_kwh=None,
                current_cost_per_hour_eur=None,
                estimated_month_cost_eur=None,
                total_shared_bytes=None,
                total_bandwidth_bps=None,
            )

        sampled_at = self._parse_datetime(self._pick(payload, ["timestamp", "updated_at", "sampled_at"]))

        cpu_model = self._pick(payload, ["cpu_model", "cpu.name", "system.cpu.model"]) or None
        gpu_model = self._pick(payload, ["gpu_model", "gpu.name", "system.gpu.model"]) or None

        ram_total = self._to_int(self._pick(payload, ["ram_total_bytes", "memory.total_bytes", "ram.total", "mem_total_bytes"]))
        ram_used = self._to_int(self._pick(payload, ["ram_used_bytes", "memory.used_bytes", "ram.used", "mem_used_bytes"]))
        ram_free = self._to_int(self._pick(payload, ["ram_free_bytes", "memory.free_bytes", "ram.free", "mem_free_bytes"]))
        if ram_free is None and ram_total is not None and ram_used is not None:
            ram_free = max(ram_total - ram_used, 0)

        cpu_percent = self._to_float(self._pick(payload, ["cpu_percent", "cpu.load_percent", "system.cpu.load", "cpu_load"]))
        gpu_percent = self._to_float(self._pick(payload, ["gpu_percent", "gpu.load_percent", "system.gpu.load", "gpu_load"]))

        inbound_bps = self._to_float(self._pick(payload, ["network.inbound_bps", "network.in_bps", "inbound_bps", "net_in_bps"]))
        outbound_bps = self._to_float(self._pick(payload, ["network.outbound_bps", "network.out_bps", "outbound_bps", "net_out_bps"]))

        power_watts = self._to_float(self._pick(payload, ["power_watts", "power.watts", "energy.power_watts", "nas_power_w"]))

        total_shared = self._to_int(self._pick(payload, ["total_shared_bytes", "traffic.total_shared_bytes", "dvm.total_shared_bytes"]))
        total_bandwidth = self._to_float(self._pick(payload, ["total_bandwidth_bps", "traffic.total_bandwidth_bps", "network.total_bandwidth_bps"]))

        timezone_name = cfg.timezone or "UTC"
        try:
            tz = ZoneInfo(timezone_name)
        except Exception:
            tz = ZoneInfo("UTC")

        now_local = datetime.now(tz)
        rate = self._select_tariff_rate(now_local, cfg)

        current_cost_per_hour = None
        if power_watts is not None and rate is not None:
            current_cost_per_hour = (power_watts / 1000.0) * rate

        estimated_month_cost = None
        if power_watts is not None:
            estimated_month_cost = self._estimate_month_cost(power_watts, now_local, cfg)

        return SystemMetrics(
            enabled=True,
            source_available=True,
            sampled_at=sampled_at,
            cpu_model=str(cpu_model).strip() if cpu_model else None,
            gpu_model=str(gpu_model).strip() if gpu_model else None,
            ram_total_bytes=ram_total,
            cpu_percent=cpu_percent,
            gpu_percent=gpu_percent,
            ram_used_bytes=ram_used,
            ram_free_bytes=ram_free,
            inbound_bps=inbound_bps,
            outbound_bps=outbound_bps,
            power_watts=power_watts,
            current_rate_eur_kwh=rate,
            current_cost_per_hour_eur=current_cost_per_hour,
            estimated_month_cost_eur=estimated_month_cost,
            total_shared_bytes=total_shared,
            total_bandwidth_bps=total_bandwidth,
        )

    @staticmethod
    def _read_json(path_value: str) -> dict | list | None:
        path = Path(path_value)
        if not path_value or not path.exists() or not path.is_file():
            return None
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
            return data if isinstance(data, (dict, list)) else None
        except Exception:
            return None

    @staticmethod
    def _walk(data: object):
        if isinstance(data, dict):
            for key, value in data.items():
                yield key, value
                yield from UnraidMetricsService._walk(value)
        elif isinstance(data, list):
            for item in data:
                yield from UnraidMetricsService._walk(item)

    def _pick(self, data: object, keys: list[str]) -> object | None:
        if isinstance(data, dict):
            for key in keys:
                if "." in key:
                    value = self._pick_dot(data, key)
                    if value is not None:
                        return value
                elif key in data:
                    return data[key]

        lookup = {str(key).lower(): value for key, value in self._walk(data)}
        for key in keys:
            simple = key.split(".")[-1].lower()
            if simple in lookup:
                return lookup[simple]
        return None

    @staticmethod
    def _pick_dot(data: dict, dotted_key: str) -> object | None:
        current: object = data
        for chunk in dotted_key.split("."):
            if not isinstance(current, dict) or chunk not in current:
                return None
            current = current[chunk]
        return current

    @staticmethod
    def _to_float(value: object) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.strip().replace(",", ".")
            try:
                return float(cleaned)
            except Exception:
                return None
        return None

    @staticmethod
    def _to_int(value: object) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(float(value.strip().replace(",", ".")))
            except Exception:
                return None
        return None

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str) and value.strip():
            text = value.strip().replace("Z", "+00:00")
            try:
                return datetime.fromisoformat(text)
            except Exception:
                return None
        return None

    @staticmethod
    def _select_tariff_rate(now_local: datetime, cfg) -> float | None:
        weekday = now_local.weekday()  # 0=mon ... 6=sun
        hour = now_local.hour

        if weekday >= 5:
            return float(cfg.energy_tariff_weekend_eur_kwh)

        if 0 <= hour < 8:
            return float(cfg.energy_tariff_valle_eur_kwh)
        if 8 <= hour < 10:
            return float(cfg.energy_tariff_llano_eur_kwh)
        if 10 <= hour < 14:
            return float(cfg.energy_tariff_punta_eur_kwh)
        if 14 <= hour < 18:
            return float(cfg.energy_tariff_llano_eur_kwh)
        if 18 <= hour < 22:
            return float(cfg.energy_tariff_punta_eur_kwh)
        return float(cfg.energy_tariff_llano_eur_kwh)

    def _estimate_month_cost(self, power_watts: float, now_local: datetime, cfg) -> float:
        days_in_month = calendar.monthrange(now_local.year, now_local.month)[1]
        start = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=days_in_month)

        hourly_cost_total = 0.0
        cursor = start
        while cursor < end:
            rate = self._select_tariff_rate(cursor, cfg) or 0.0
            hourly_cost_total += (power_watts / 1000.0) * rate
            cursor += timedelta(hours=1)

        return hourly_cost_total


def format_bytes(value: int | None) -> str | None:
    if value is None:
        return None
    number = float(value)
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    idx = 0
    while number >= 1024 and idx < len(units) - 1:
        number /= 1024
        idx += 1
    return f"{number:.1f} {units[idx]}"


def format_bps(value: float | None) -> str | None:
    if value is None:
        return None
    mbps = value / 1_000_000
    if mbps < 1000:
        return f"{mbps:.1f} Mbps"
    return f"{(mbps / 1000):.2f} Gbps"
