from __future__ import annotations

import json
from pathlib import Path


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
    if not path:
        return []

    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return []

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    lines = content.splitlines()
    if limit > 0:
        lines = lines[-limit:]
    return parse_transfer_log_lines(lines)
