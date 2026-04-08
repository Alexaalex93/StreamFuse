from pathlib import Path

from app.core.config import Settings
from app.domain.enums import MediaType
from app.poster_resolver.resolver import PosterResolver


def _fixtures_dir() -> Path:
    return (Path(__file__).resolve().parents[1] / "fixtures" / "posters").resolve()


def test_movie_resolves_poster_jpg() -> None:
    fixtures = _fixtures_dir()
    movie_file = fixtures / "movie_with_poster" / "Dune.mkv"
    expected = fixtures / "movie_with_poster" / "poster.jpg"
    placeholder = fixtures / "placeholder.svg"

    settings = Settings(
        poster_placeholder_path=str(placeholder),
        poster_allowed_roots=str(fixtures),
    )
    resolver = PosterResolver(settings)

    assert resolver.resolve(str(movie_file), MediaType.MOVIE) == expected


def test_movie_resolves_folder_jpg_when_no_poster() -> None:
    fixtures = _fixtures_dir()
    movie_file = fixtures / "movie_with_folder" / "BladeRunner.mkv"
    expected = fixtures / "movie_with_folder" / "folder.jpg"
    placeholder = fixtures / "placeholder.svg"

    settings = Settings(
        poster_placeholder_path=str(placeholder),
        poster_allowed_roots=str(fixtures),
    )
    resolver = PosterResolver(settings)

    assert resolver.resolve(str(movie_file), MediaType.MOVIE) == expected


def test_series_resolves_from_series_root() -> None:
    fixtures = _fixtures_dir()
    episode = fixtures / "series_with_poster" / "Dark" / "Season 1" / "Dark.S01E02.mkv"
    expected = fixtures / "series_with_poster" / "Dark" / "poster.jpg"
    placeholder = fixtures / "placeholder.svg"

    settings = Settings(
        poster_placeholder_path=str(placeholder),
        poster_allowed_roots=str(fixtures),
    )
    resolver = PosterResolver(settings)

    assert resolver.resolve(str(episode), MediaType.EPISODE) == expected


def test_fallback_to_placeholder_when_no_poster() -> None:
    fixtures = _fixtures_dir()
    movie_file = fixtures / "no_poster" / "NoPoster.mkv"
    placeholder = fixtures / "placeholder.svg"

    settings = Settings(
        poster_placeholder_path=str(placeholder),
        poster_allowed_roots=str(fixtures),
    )
    resolver = PosterResolver(settings)

    assert resolver.resolve(str(movie_file), MediaType.MOVIE) == placeholder


def test_sanitization_blocks_outside_allowed_roots() -> None:
    fixtures = _fixtures_dir()
    outside_file = fixtures / "outside_root" / "movie.mkv"
    placeholder = fixtures / "placeholder.svg"
    allowed_root = fixtures / "movie_with_poster"

    settings = Settings(
        poster_placeholder_path=str(placeholder),
        poster_allowed_roots=str(allowed_root),
    )
    resolver = PosterResolver(settings)

    assert resolver.resolve(str(outside_file), MediaType.MOVIE) == placeholder


def test_resolver_returns_placeholder_on_invalid_input_path() -> None:
    fixtures = _fixtures_dir()
    placeholder = fixtures / "placeholder.svg"

    settings = Settings(
        poster_placeholder_path=str(placeholder),
        poster_allowed_roots=str(fixtures),
    )
    resolver = PosterResolver(settings)

    assert resolver.resolve("\0\0\0", MediaType.MOVIE) == placeholder