from __future__ import annotations

import html
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from xml.etree import ElementTree

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MediaInfoSummary:
    title: str | None = None
    series_title: str | None = None
    episode_title: str | None = None
    season_number: int | None = None
    episode_number: int | None = None
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

    xml_summary: MediaInfoSummary | None = None
    xml_file = _find_mediainfo_xml(media_file)
    if xml_file is not None:
        xml_summary = _parse_mediainfo_xml(xml_file)

    nfo_summary: MediaInfoSummary | None = None
    nfo_file = _find_nfo_file(media_file)
    if nfo_file is not None:
        nfo_summary = _parse_nfo_xml(nfo_file)

    if xml_summary is None and nfo_summary is None:
        return None
    if xml_summary is None:
        return nfo_summary
    if nfo_summary is None:
        return xml_summary

    return _merge_summary(primary=xml_summary, fallback=nfo_summary)


def _parse_mediainfo_xml(xml_file: Path) -> MediaInfoSummary | None:
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

    return MediaInfoSummary(
        title=_first_non_empty(
            _find_text(general_track, "Movie"),
            _find_text(general_track, "Title"),
        ),
        duration_ms=_duration_to_ms(_find_text(general_track, "Duration")),
        overall_bitrate_bps=_to_bitrate_bps(_first_non_empty(_find_text(general_track, "OverallBitRate"), _find_text(general_track, "OverallBitRate/String"), _find_text(general_track, "BitRate"))),
        video_bitrate_bps=_to_bitrate_bps(_first_non_empty(_find_text(video_track, "BitRate"), _find_text(video_track, "BitRate_Nominal"), _find_text(video_track, "BitRate_Maximum"), _find_text(video_track, "BitRate/String"))),
        resolution=_format_resolution(width, height),
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


def _parse_nfo_xml(nfo_file: Path) -> MediaInfoSummary | None:
    try:
        root = ElementTree.parse(nfo_file).getroot()
    except (ElementTree.ParseError, OSError, RuntimeError):
        logger.warning("Failed to parse nfo xml", extra={"path": str(nfo_file)})
        fallback_title = _extract_title_from_raw_nfo(nfo_file)
        if fallback_title:
            return MediaInfoSummary(title=fallback_title)
        return None

    video = root.find(".//fileinfo/streamdetails/video")
    if video is None:
        video = root.find(".//streamdetails/video")

    audio = root.find(".//fileinfo/streamdetails/audio")
    if audio is None:
        audio = root.find(".//streamdetails/audio")

    width = _to_int(_find_text(video, "width"))
    height = _to_int(_find_text(video, "height"))

    runtime_minutes = _to_float(_first_non_empty(_find_text(root, "runtime"), _find_text(root, "duration")))
    duration_ms = int(runtime_minutes * 60_000) if runtime_minutes is not None else None

    overall_bitrate_bps = _to_bitrate_bps(
        _first_non_empty(
            _find_text(video, "bitrate"),
            _find_text(video, "bitrateinbits"),
            _find_text(root, "bitrate"),
            _find_text(root, "bitrateinbits"),
        )
    )

    return MediaInfoSummary(
        title=_sanitize_title_text(_first_non_empty(_find_text(root, "title"), _find_text(root, "originaltitle"))),
        duration_ms=duration_ms,
        overall_bitrate_bps=overall_bitrate_bps,
        video_bitrate_bps=overall_bitrate_bps,
        resolution=_format_resolution(width, height),
        video_codec=_first_non_empty(_find_text(video, "codec"), _find_text(video, "format")),
        audio_codec=_first_non_empty(_find_text(audio, "codec"), _find_text(audio, "format")),
        frame_rate=_to_float(_find_text(video, "framerate")),
        audio_channels=_to_int(_first_non_empty(_find_text(audio, "channels"), _find_text(audio, "channel"))),
    )


def _merge_summary(primary: MediaInfoSummary, fallback: MediaInfoSummary) -> MediaInfoSummary:
    return MediaInfoSummary(
        title=fallback.title or primary.title,
        series_title=fallback.series_title or primary.series_title,
        episode_title=fallback.episode_title or primary.episode_title,
        season_number=primary.season_number or fallback.season_number,
        episode_number=primary.episode_number or fallback.episode_number,
        duration_ms=primary.duration_ms or fallback.duration_ms,
        overall_bitrate_bps=primary.overall_bitrate_bps or fallback.overall_bitrate_bps,
        video_bitrate_bps=primary.video_bitrate_bps or fallback.video_bitrate_bps,
        resolution=primary.resolution or fallback.resolution,
        video_codec=primary.video_codec or fallback.video_codec,
        audio_codec=primary.audio_codec or fallback.audio_codec,
        frame_rate=primary.frame_rate or fallback.frame_rate,
        audio_channels=primary.audio_channels or fallback.audio_channels,
    )


def _find_mediainfo_xml(media_file: Path) -> Path | None:
    parent = media_file.parent
    candidates = [
        media_file.with_suffix(".mediainfo.xml"),
        parent / "mediainfo.xml",
        parent / f"{media_file.stem}.mediainfo.xml",
        parent / f"{media_file.stem}-mediainfo.xml",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _find_nfo_file(media_file: Path) -> Path | None:
    parent = media_file.parent
    candidates = [
        parent / "movie.nfo",
        parent / f"{media_file.stem}.nfo",
        parent / "tvshow.nfo",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _extract_title_from_raw_nfo(nfo_file: Path) -> str | None:
    try:
        raw = nfo_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    match = re.search(r"<title>\s*(.*?)\s*</title>", raw, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None

    value = html.unescape(match.group(1) or "")
    return _sanitize_title_text(value)


def _sanitize_title_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.replace("\ufffd", " ").replace("\u00c2", "")
    cleaned = " ".join(cleaned.split())
    return cleaned or None


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


def _find_text(node: ElementTree.Element | None, tag_name: str) -> str | None:
    if node is None:
        return None
    if tag_name in {"title", "originaltitle", "runtime", "duration", "bitrate"}:
        child = node.find(f"./{tag_name}")
    else:
        child = node.find(f"./{{*}}{tag_name}")
        if child is None:
            child = node.find(f"./{tag_name}")
    if child is None or child.text is None:
        return None
    value = child.text.strip()
    return value or None


def _to_int(value: str | None) -> int | None:
    number = _extract_number(value)
    if number is None:
        return None
    return int(number)


def _to_float(value: str | None) -> float | None:
    number = _extract_number(value)
    return number


def _to_bitrate_bps(value: str | None) -> int | None:
    if not value:
        return None

    number = _extract_number(value)
    if number is None:
        return None

    lower = value.lower()
    if "gb/s" in lower or "gbit" in lower:
        return int(number * 1_000_000_000)
    if "mb/s" in lower or "mbit" in lower:
        return int(number * 1_000_000)
    if "kb/s" in lower or "kbit" in lower:
        return int(number * 1_000)

    if number >= 1_000_000:
        return int(number)
    return int(number * 1_000)


def _duration_to_ms(value: str | None) -> int | None:
    if not value:
        return None

    lower = value.lower()
    if any(token in lower for token in ("h", "min", "ms", "s")):
        hours = _extract_named_number(lower, "h") or 0
        minutes = _extract_named_number(lower, "min") or 0
        seconds = _extract_named_number(lower, "s") or 0
        milliseconds = _extract_named_number(lower, "ms") or 0
        total_ms = int(hours * 3_600_000 + minutes * 60_000 + seconds * 1_000 + milliseconds)
        if total_ms > 0:
            return total_ms

    as_float = _extract_number(value)
    if as_float is None:
        return None

    if as_float > 10_000:
        return int(as_float)
    return int(as_float * 1000)


def _extract_named_number(text: str, unit: str) -> float | None:
    if unit == "s":
        pattern = r"(\d+(?:[\.,]\d+)?)\s*s(?![a-z])"
    elif unit == "ms":
        pattern = r"(\d+(?:[\.,]\d+)?)\s*ms"
    else:
        pattern = rf"(\d+(?:[\.,]\d+)?)\s*{re.escape(unit)}"

    match = re.search(pattern, text)
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", "."))
    except ValueError:
        return None


def _extract_number(value: str | None) -> float | None:
    if not value:
        return None

    cleaned = re.sub(r"(?<=\d)[\s_,](?=\d)", "", value)
    match = re.search(r"\d+(?:[\.,]\d+)?", cleaned)
    if not match:
        return None

    token = match.group(0).replace(",", ".")
    try:
        return float(token)
    except ValueError:
        return None


def _format_resolution(width: int | None, height: int | None) -> str | None:
    if height is None:
        return None
    if height >= 2160:
        return "4K"
    return f"{height}p"


def _first_non_empty(*values: str | None) -> str | None:
    for value in values:
        if value and value.strip():
            return value.strip()
    return None















def _normalize_match_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())
