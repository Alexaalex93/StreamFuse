from __future__ import annotations

import logging
from pathlib import Path
from threading import Lock

from app.core.config import Settings
from app.domain.enums import MediaType
from app.parsers.media_parser import detect_media_type

logger = logging.getLogger(__name__)

_MOVIE_POSTER_PRIORITY = ["poster.jpg", "cover.jpg", "folder.jpg", "movie.jpg"]
_SERIES_POSTER_PRIORITY = ["poster.jpg", "cover.jpg", "folder.jpg", "series.jpg"]
_MOVIE_FANART_PRIORITY = ["fanart.jpg", "backdrop.jpg", "background.jpg"]
_SERIES_FANART_PRIORITY = ["fanart.jpg", "backdrop.jpg", "background.jpg"]
_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".svg"}


class PosterResolver:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.placeholder = Path(settings.poster_placeholder_path).resolve()
        self.allowed_roots = [
            Path(root.strip()).resolve()
            for root in settings.poster_allowed_roots.split(",")
            if root.strip()
        ]
        self._cache: dict[tuple[str, str, str], Path] = {}
        self._lock = Lock()

    def resolve(
        self,
        file_path: str | None,
        media_type: MediaType | str | None,
        *,
        variant: str = "poster",
    ) -> Path:
        if not file_path:
            return self.placeholder

        file = self._sanitize_file_path(file_path)
        if file is None:
            return self.placeholder

        inferred_media_type = self._normalize_media_type(media_type, file)
        safe_variant = variant if variant in {"poster", "fanart"} else "poster"
        cache_key = (inferred_media_type.value, str(file), safe_variant)

        with self._lock:
            cached = self._cache.get(cache_key)
        if cached and cached.exists():
            return cached

        if inferred_media_type == MediaType.EPISODE:
            resolved = self.resolve_series_image(file, variant=safe_variant)
        else:
            resolved = self.resolve_movie_image(file, variant=safe_variant)

        with self._lock:
            self._cache[cache_key] = resolved
        return resolved

    def resolve_movie_image(self, media_file: Path, *, variant: str) -> Path:
        directory = media_file.parent
        if not directory.exists():
            return self.placeholder

        priority = _MOVIE_FANART_PRIORITY if variant == "fanart" else _MOVIE_POSTER_PRIORITY
        for name in priority:
            candidate = directory / name
            if self._is_valid_image(candidate):
                return candidate

        for candidate in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
            if self._is_valid_image(candidate):
                return candidate

        return self.placeholder

    def resolve_series_image(self, media_file: Path, *, variant: str) -> Path:
        series_root = self._get_series_root(media_file)
        if series_root is None or not series_root.exists():
            return self.placeholder

        priority = _SERIES_FANART_PRIORITY if variant == "fanart" else _SERIES_POSTER_PRIORITY
        for name in priority:
            candidate = series_root / name
            if self._is_valid_image(candidate):
                return candidate

        return self.placeholder

    def _sanitize_file_path(self, raw_path: str) -> Path | None:
        try:
            path = Path(raw_path).resolve(strict=False)
        except (OSError, RuntimeError, ValueError):
            logger.warning("Invalid media path for poster resolution", extra={"path": raw_path})
            return None

        if self.allowed_roots and not any(self._is_within(path, root) for root in self.allowed_roots):
            logger.warning("Blocked media path outside allowed roots", extra={"path": str(path)})
            return None

        return path

    @staticmethod
    def _is_within(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False

    def _get_series_root(self, media_file: Path) -> Path | None:
        parent = media_file.parent
        if parent.name.lower().startswith("season "):
            return parent.parent

        return parent if parent.exists() else None

    @staticmethod
    def _is_valid_image(path: Path) -> bool:
        return path.is_file() and path.suffix.lower() in _IMAGE_EXTENSIONS

    @staticmethod
    def _normalize_media_type(media_type: MediaType | str | None, media_file: Path) -> MediaType:
        if isinstance(media_type, MediaType):
            return media_type

        if isinstance(media_type, str):
            try:
                return MediaType(media_type)
            except ValueError:
                pass

        return detect_media_type(str(media_file))
