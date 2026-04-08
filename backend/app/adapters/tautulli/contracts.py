from typing import NotRequired, TypedDict


class TautulliRawSession(TypedDict, total=False):
    session_id: str
    user: str
    user_id: str | int
    user_thumb: str
    ip_address: str
    friendly_name: str

    title: str
    full_title: str
    grandparent_title: str
    parent_title: str
    media_type: str

    parent_media_index: int
    media_index: int
    file: str
    rating_key: str

    duration: int
    progress_percent: float
    view_offset: int

    bandwidth: int
    stream_bitrate: int
    quality_profile: str

    stream_video_full_resolution: str
    stream_video_codec: str
    stream_audio_codec: str

    player: str
    product: str
    platform: str

    started: int
    stopped: int

    transcode_decision: str
    transcode_container: str
    transcode_video_codec: str
    transcode_audio_codec: str


class TautulliRawHistoryItem(TautulliRawSession, total=False):
    date: int
    paused_counter: int
    watched_status: int


class TautulliApiResponse(TypedDict, total=False):
    response: NotRequired[dict]
