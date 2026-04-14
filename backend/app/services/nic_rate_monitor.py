"""
Real-time NIC rate monitor.

Computes outbound_bps / inbound_bps from psutil net_io_counters() deltas.
The state is kept at module level so it persists across HTTP requests within
the same process. On the very first call no previous sample exists yet, so
(0.0, 0.0) is returned and the baseline is stored; from the second call
onwards real rates are available.
"""
from __future__ import annotations

import time

try:
    import psutil as _psutil
    _PSUTIL_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PSUTIL_AVAILABLE = False

_prev_bytes_sent: int | None = None
_prev_bytes_recv: int | None = None
_prev_ts: float | None = None


def get_nic_rates() -> tuple[float, float]:
    """Return ``(outbound_bps, inbound_bps)`` from the host NIC counters.

    Returns ``(0.0, 0.0)`` on the first call (no baseline yet) or if psutil
    is unavailable / raises.
    """
    global _prev_bytes_sent, _prev_bytes_recv, _prev_ts

    if not _PSUTIL_AVAILABLE:
        return 0.0, 0.0

    try:
        counters = _psutil.net_io_counters()
        now = time.monotonic()

        if _prev_bytes_sent is None or _prev_ts is None:
            # First call — store baseline, return zeros.
            _prev_bytes_sent = counters.bytes_sent
            _prev_bytes_recv = counters.bytes_recv
            _prev_ts = now
            return 0.0, 0.0

        dt = now - _prev_ts
        if dt < 0.01:
            # Called too fast (sub-10 ms) — skip to avoid division noise.
            return 0.0, 0.0

        out_bps = (counters.bytes_sent - _prev_bytes_sent) / dt
        in_bps = (counters.bytes_recv - _prev_bytes_recv) / dt

        # Handle counter wrap-around or reset (e.g. interface restart).
        out_bps = max(0.0, out_bps)
        in_bps = max(0.0, in_bps)

        _prev_bytes_sent = counters.bytes_sent
        _prev_bytes_recv = counters.bytes_recv
        _prev_ts = now

        return out_bps, in_bps

    except Exception:
        return 0.0, 0.0
