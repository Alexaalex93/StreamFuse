from app.domain.enums import MediaType
from app.parsers.media_parser import (
    clean_movie_title,
    detect_media_type,
    extract_tmdb_id,
    parse_series_context,
)


def test_clean_movie_title_with_tmdb_block() -> None:
    filename = "The.Matrix.Resurrections {tmdbid 624860}.mkv"
    assert clean_movie_title(filename) == "The Matrix Resurrections"


def test_clean_movie_title_without_tmdb_block() -> None:
    filename = "Blade.Runner.2049.2017.mkv"
    assert clean_movie_title(filename) == "Blade Runner 2049 2017"


def test_extract_tmdb_id_variants() -> None:
    assert extract_tmdb_id("Movie {tmdbid 12345}.mkv") == 12345
    assert extract_tmdb_id("movie tmdbid:67890") == 67890
    assert extract_tmdb_id("movie without id") is None


def test_parse_series_context_standard_structure() -> None:
    parsed = parse_series_context("/The Expanse/Season 2/The.Expanse.S02E05.mkv")

    assert parsed["is_episode"] is True
    assert parsed["series_title"] == "The Expanse"
    assert parsed["season_number"] == 2
    assert parsed["episode_number"] == 5


def test_parse_series_context_episode_name_with_spanish_pattern() -> None:
    parsed = parse_series_context(r"C:\Series\Dark\Season 1\Episodio 03 - Something.mkv")

    assert parsed["is_episode"] is True
    assert parsed["series_title"] == "Dark"
    assert parsed["season_number"] == 1
    assert parsed["episode_number"] == 3


def test_parse_series_context_partial_structure_uses_filename_clean() -> None:
    parsed = parse_series_context("/Unknown/Folder/very.weird.file.name!!.mkv")

    assert parsed["is_episode"] is False
    assert parsed["series_title"] is None
    assert parsed["season_number"] is None
    assert parsed["episode_number"] is None
    assert parsed["title_clean"] == "very weird file name!!"


def test_parse_series_context_detects_episode_without_season_folder() -> None:
    parsed = parse_series_context("/Breaking.Bad/Breaking.Bad.S04E02.mkv")

    assert parsed["is_episode"] is True
    assert parsed["series_title"] == "Breaking Bad"
    assert parsed["season_number"] == 4
    assert parsed["episode_number"] == 2


def test_detect_media_type_episode_movie_other() -> None:
    assert detect_media_type("/Series/Season 1/Show.S01E01.mkv") == MediaType.EPISODE
    assert detect_media_type("/Movies/Interstellar {tmdbid 157336}.mkv") == MediaType.MOVIE
    assert detect_media_type("/misc/readme.txt") == MediaType.OTHER


def test_extract_tmdb_id_invalid_digits_returns_none() -> None:
    assert extract_tmdb_id("Movie {tmdbid abcde}.mkv") is None


def test_parse_series_context_with_partial_structure_keeps_title_clean() -> None:
    parsed = parse_series_context("/Library/Season X/very--odd__name...mp4")
    assert parsed["title_clean"] == "very odd name"