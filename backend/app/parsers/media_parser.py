from __future__ import annotations

import re
from pathlib import PurePath

from app.domain.enums import MediaType

_VIDEO_EXTENSIONS = {
    ".mkv",
    ".mp4",
    ".avi",
    ".mov",
    ".m4v",
    ".ts",
    ".wmv",
}

_TMDB_BLOCK_RE = re.compile(r"\{[^{}]*tmdbid[^{}]*\}", re.IGNORECASE)
_TMDB_ID_RE = re.compile(r"tmdbid\s*[:=#-]?\s*(\d+)", re.IGNORECASE)
_SEASON_DIR_RE = re.compile(r"^season[\s._-]*(\d{1,2})$", re.IGNORECASE)
_EPISODE_PATTERNS = [
    re.compile(r"[Ss](\d{1,2})[ ._-]*[Ee](\d{1,3})"),
    re.compile(r"(\d{1,2})[xX](\d{1,3})"),
    re.compile(r"(?:episode|episodio|ep|e)[ ._-]*(\d{1,3})", re.IGNORECASE),
]


def _normalize_tokens(text: str) -> str:
    cleaned = re.sub(r"[._]+", " ", text)
    cleaned = re.sub(r"\s*-\s*", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _filename_no_ext(filename: str) -> str:
    return PurePath(filename).stem


def extract_tmdb_id(text: str) -> int | None:
    match = _TMDB_ID_RE.search(text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def clean_movie_title(filename: str) -> str:
    stem = _filename_no_ext(filename)
    without_tmdb_block = _TMDB_BLOCK_RE.sub("", stem)
    without_inline_tmdb = _TMDB_ID_RE.sub("", without_tmdb_block)
    return _normalize_tokens(without_inline_tmdb)


def parse_series_context(path: str) -> dict[str, object]:
    normalized_path = path.replace("\\", "/")
    path_obj = PurePath(normalized_path)
    parts = [part for part in path_obj.parts if part not in {"/", "\\"}]

    filename = parts[-1] if parts else path
    title_clean = clean_movie_title(filename)

    season_number: int | None = None
    episode_number: int | None = None
    series_title: str | None = None
    is_episode = False

    season_index: int | None = None
    for index, part in enumerate(parts[:-1]):
        season_match = _SEASON_DIR_RE.match(part)
        if season_match:
            season_index = index
            season_number = int(season_match.group(1))
            if index > 0:
                series_title = clean_movie_title(parts[index - 1])
            is_episode = True
            break

    for pattern in _EPISODE_PATTERNS:
        match = pattern.search(title_clean)
        if not match:
            continue
        is_episode = True
        if pattern is _EPISODE_PATTERNS[0] or pattern is _EPISODE_PATTERNS[1]:
            if season_number is None:
                season_number = int(match.group(1))
            episode_number = int(match.group(2))
        else:
            episode_number = int(match.group(1))
        break

    if series_title is None and season_index is None and len(parts) >= 2 and is_episode:
        series_title = clean_movie_title(parts[-2])

    lowered_parts = [part.lower() for part in parts]
    if series_title is None and "series" in lowered_parts:
        series_idx = lowered_parts.index("series")
        if series_idx + 1 < len(parts):
            series_title = clean_movie_title(parts[series_idx + 1])
            is_episode = True

    return {
        "is_episode": is_episode,
        "series_title": series_title,
        "season_number": season_number,
        "episode_number": episode_number,
        "title_clean": title_clean,
    }


def detect_media_type(path: str) -> MediaType:
    normalized_path = path.replace("\\", "/").lower()
    if "/series/" in normalized_path:
        return MediaType.EPISODE
    if "/peliculas/" in normalized_path:
        return MediaType.MOVIE

    series = parse_series_context(path)
    if bool(series["is_episode"]):
        return MediaType.EPISODE

    extension = PurePath(path).suffix.lower()
    if extension in _VIDEO_EXTENSIONS:
        return MediaType.MOVIE

    return MediaType.OTHER


