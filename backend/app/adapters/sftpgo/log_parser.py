from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _read_tail_bytes(file_path: Path, n_lines: int, chunk: int = 8192) -> list[str]:
    """Return the last *n_lines* lines of *file_path* without loading the whole
    file into memory.  Uses backward seek so cost is O(result size), not O(file
    size).  Falls back to a full read only for files smaller than one chunk."""
    if n_lines <= 0:
        return []

    try:
        with open(file_path, "rb") as fh:
            fh.seek(0, 2)
            size = fh.tell()
            if size == 0:
                return []

            buf = b""
            pos = size
            collected: list[bytes] = []

            while pos > 0 and len(collected) < n_lines + 1:
                to_read = min(chunk, pos)
                pos -= to_read
                fh.seek(pos)
                data = fh.read(to_read)
                # Prepend previously-seen partial line
                data = data + buf
                parts = data.split(b"\n")
                # parts[0] might be the tail of an earlier line — save for next iter
                buf = parts[0]
                collected = parts[1:] + collected

            if buf:
                collected = [buf] + collected

        tail = collected[-n_lines:]
        return [line.decode("utf-8", errors="ignore") for line in tail]
    except OSError:
        return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_transfer_log_lines(lines: list[str]) -> list[dict]:
    parsed: list[dict] = []
    for line in lines:
        raw = line.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            parsed.append(data)
    return parsed


def parse_transfer_log_file(path: str | None, limit: int = 200) -> list[dict]:
    """Return up to *limit* of the most-recent log entries from a JSONL file.

    Reads only the tail of the file — no full load regardless of file size.
    """
    if not path:
        return []

    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return []

    lines = _read_tail_bytes(file_path, n_lines=max(limit, 1))
    return parse_transfer_log_lines(lines)


def trim_transfer_log_file(path: str | None, max_age_days: int = 7) -> int:
    """Remove log entries older than *max_age_days* from a JSONL file in-place.

    Returns the number of lines removed.  Safe to call concurrently with
    readers because it writes to a temp file and atomically renames it.

    Timestamp detection (field ``ts``):
    - Unix seconds  → value < 1e10
    - Unix milliseconds → value >= 1e10  (divided by 1000 automatically)
    Lines with no parseable timestamp are kept (unknown age → safe).
    """
    if not path:
        return 0

    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return 0

    cutoff = datetime.now(UTC).timestamp() - max_age_days * 86_400

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return 0

    original_lines = content.splitlines()
    kept: list[str] = []

    for line in original_lines:
        raw = line.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            kept.append(line)
            continue

        ts_raw = data.get("ts") or data.get("timestamp") or data.get("time")
        if ts_raw is None:
            kept.append(line)
            continue

        try:
            ts = float(ts_raw)
            if ts > 1e10:          # milliseconds → seconds
                ts /= 1000.0
            if ts >= cutoff:
                kept.append(line)
            # else: entry is older than max_age_days → drop
        except (TypeError, ValueError):
            kept.append(line)      # unparseable timestamp → keep

    removed = len(original_lines) - len(kept)
    if removed <= 0:
        return 0

    # Atomic write via temp file to avoid partial reads during rotation
    tmp = file_path.with_suffix(".tmp")
    try:
        tmp.write_text("\n".join(kept) + "\n", encoding="utf-8")
        tmp.replace(file_path)
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return 0

    return removed
