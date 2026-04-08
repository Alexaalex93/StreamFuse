from pathlib import Path

from app.parsers.mediainfo_parser import parse_mediainfo_for_media


def _fixtures_dir() -> Path:
    return (Path(__file__).resolve().parents[1] / "fixtures" / "mediainfo").resolve()


def test_parse_mediainfo_from_sibling_xml() -> None:
    fixtures = _fixtures_dir()
    media_file = fixtures / "with_xml" / "Episode.S01E01.mkv"

    summary = parse_mediainfo_for_media(str(media_file))

    assert summary is not None
    assert summary.title == "Pilot Episode"
    assert summary.duration_ms == 3_492_960
    assert summary.overall_bitrate_bps == 7_682_012
    assert summary.video_bitrate_bps == 6_249_140
    assert summary.resolution == "1920x960"
    assert summary.video_codec == "HEVC"
    assert summary.audio_codec == "E-AC-3"
    assert summary.audio_channels == 6


def test_parse_mediainfo_returns_none_when_missing() -> None:
    fixtures = _fixtures_dir()
    media_file = fixtures / "without_xml" / "Movie.mkv"
    assert parse_mediainfo_for_media(str(media_file)) is None