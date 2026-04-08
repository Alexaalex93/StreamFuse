from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from xml.etree import ElementTree

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MediaInfoSummary:
    title: str | None = None
    duration_ms: int | None = None
    overall_bitrate_bps: int | None = None
    video_bitrate_bps: int | None = None
    resolution: str | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    frame_rate: float | None = None
    audio_channels: int | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def parse_mediainfo_for_media(media_file_path: str | None) -> MediaInfoSummary | None:
    if not media_file_path:
        return None

    media_file = Path(media_file_path)
    xml_file = _find_mediainfo_xml(media_file)
    if xml_file is None:
        return None

    try:
        root = ElementTree.parse(xml_file).getroot()
    except (ElementTree.ParseError, OSError, RuntimeError):
        logger.warning("Failed to parse mediainfo xml", extra={"path": str(xml_file)})
        return None

    general_track = _find_track(root, "General")
    video_track = _find_track(root, "Video")
    audio_track = _find_default_audio_track(root)

    width = _to_int(_find_text(video_track, "Width"))
    height = _to_int(_find_text(video_track, "Height"))

    summary = MediaInfoSummary(
        title=_first_non_empty(
            _find_text(general_track, "Movie"),
            _find_text(general_track, "Title"),
        ),
        duration_ms=_seconds_text_to_ms(_find_text(general_track, "Duration")),
        overall_bitrate_bps=_to_int(_find_text(general_track, "OverallBitRate")),
        video_bitrate_bps=_to_int(_find_text(video_track, "BitRate")),
        resolution=f"{width}x{height}" if width and height else None,
        video_codec=_first_non_empty(
            _find_text(video_track, "Format"),
            _find_text(video_track, "CodecID"),
        ),
        audio_codec=_first_non_empty(
            _find_text(audio_track, "Format"),
            _find_text(audio_track, "CodecID"),
        ),
        frame_rate=_to_float(_find_text(video_track, "FrameRate")),
        audio_channels=_to_int(_find_text(audio_track, "Channels")),
    )
    return summary


def _find_mediainfo_xml(media_file: Path) -> Path | None:
    parent = media_file.parent
    candidates = [
        media_file.with_suffix(".mediainfo.xml"),
        parent / "mediainfo.xml",
        parent / f"{media_file.stem}.mediainfo.xml",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _find_track(root: ElementTree.Element, track_type: str) -> ElementTree.Element | None:
    for track in root.findall(".//{*}track"):
        if (track.get("type") or "").lower() == track_type.lower():
            return track
    return None


def _find_default_audio_track(root: ElementTree.Element) -> ElementTree.Element | None:
    first_audio: ElementTree.Element | None = None
    for track in root.findall(".//{*}track"):
        if (track.get("type") or "").lower() != "audio":
            continue
        if first_audio is None:
            first_audio = track
        default_text = (_find_text(track, "Default") or "").strip().lower()
        if default_text == "yes":
            return track
    return first_audio


def _find_text(track: ElementTree.Element | None, tag_name: str) -> str | None:
    if track is None:
        return None
    node = track.find(f"./{{*}}{tag_name}")
    if node is None or node.text is None:
        return None
    value = node.text.strip()
    return value or None


def _to_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _seconds_text_to_ms(value: str | None) -> int | None:
    as_float = _to_float(value)
    if as_float is None:
        return None
    return int(as_float * 1000)


def _first_non_empty(*values: str | None) -> str | None:
    for value in values:
        if value and value.strip():
            return value.strip()
    return None