"""initial_streamfuse_schema

Revision ID: 20260408_0001
Revises:
Create Date: 2026-04-08 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260408_0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

stream_source_enum = sa.Enum("tautulli", "sftpgo", name="stream_source", native_enum=False)
session_status_enum = sa.Enum("active", "ended", "error", name="session_status", native_enum=False)
media_type_enum = sa.Enum(
    "movie",
    "episode",
    "live",
    "file_transfer",
    "other",
    name="media_type",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_name", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_user_name", "users", ["user_name"], unique=True)

    op.create_table(
        "media_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("title_clean", sa.String(length=512), nullable=False),
        sa.Column("media_type", media_type_enum, nullable=False),
        sa.Column("series_title", sa.String(length=512), nullable=True),
        sa.Column("season_number", sa.Integer(), nullable=True),
        sa.Column("episode_number", sa.Integer(), nullable=True),
        sa.Column("file_path", sa.String(length=1024), nullable=True),
        sa.Column("file_name", sa.String(length=512), nullable=True),
        sa.Column("poster_path", sa.String(length=1024), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_media_items_media_type", "media_items", ["media_type"], unique=False)
    op.create_index("ix_media_items_title", "media_items", ["title"], unique=False)
    op.create_index("ix_media_items_title_clean", "media_items", ["title_clean"], unique=False)

    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=128), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ingestion_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", stream_source_enum, nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("records_received", sa.Integer(), nullable=False),
        sa.Column("records_written", sa.Integer(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ingestion_logs_source", "ingestion_logs", ["source"], unique=False)

    op.create_table(
        "unified_stream_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", stream_source_enum, nullable=False),
        sa.Column("source_session_id", sa.String(length=255), nullable=False),
        sa.Column("status", session_status_enum, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("media_item_id", sa.Integer(), sa.ForeignKey("media_items.id"), nullable=True),
        sa.Column("user_name", sa.String(length=128), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("title_clean", sa.String(length=512), nullable=True),
        sa.Column("media_type", media_type_enum, nullable=False),
        sa.Column("series_title", sa.String(length=512), nullable=True),
        sa.Column("season_number", sa.Integer(), nullable=True),
        sa.Column("episode_number", sa.Integer(), nullable=True),
        sa.Column("file_path", sa.String(length=1024), nullable=True),
        sa.Column("file_name", sa.String(length=512), nullable=True),
        sa.Column("poster_path", sa.String(length=1024), nullable=True),
        sa.Column("bandwidth_bps", sa.BigInteger(), nullable=True),
        sa.Column("bandwidth_human", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("progress_percent", sa.Float(), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("client_name", sa.String(length=128), nullable=True),
        sa.Column("player_name", sa.String(length=128), nullable=True),
        sa.Column("transcode_decision", sa.String(length=64), nullable=True),
        sa.Column("resolution", sa.String(length=64), nullable=True),
        sa.Column("video_codec", sa.String(length=64), nullable=True),
        sa.Column("audio_codec", sa.String(length=64), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
    )
    op.create_index("ix_unified_stream_sessions_source", "unified_stream_sessions", ["source"], unique=False)
    op.create_index(
        "ix_unified_stream_sessions_source_session_id",
        "unified_stream_sessions",
        ["source_session_id"],
        unique=False,
    )
    op.create_index("ix_unified_stream_sessions_status", "unified_stream_sessions", ["status"], unique=False)
    op.create_index("ix_unified_stream_sessions_user_name", "unified_stream_sessions", ["user_name"], unique=False)
    op.create_index("ix_unified_stream_sessions_title_clean", "unified_stream_sessions", ["title_clean"], unique=False)
    op.create_index("ix_unified_stream_sessions_media_type", "unified_stream_sessions", ["media_type"], unique=False)
    op.create_index(
        "ix_unified_source_session",
        "unified_stream_sessions",
        ["source", "source_session_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_unified_source_session", table_name="unified_stream_sessions")
    op.drop_index("ix_unified_stream_sessions_media_type", table_name="unified_stream_sessions")
    op.drop_index("ix_unified_stream_sessions_title_clean", table_name="unified_stream_sessions")
    op.drop_index("ix_unified_stream_sessions_user_name", table_name="unified_stream_sessions")
    op.drop_index("ix_unified_stream_sessions_status", table_name="unified_stream_sessions")
    op.drop_index("ix_unified_stream_sessions_source_session_id", table_name="unified_stream_sessions")
    op.drop_index("ix_unified_stream_sessions_source", table_name="unified_stream_sessions")
    op.drop_table("unified_stream_sessions")

    op.drop_index("ix_ingestion_logs_source", table_name="ingestion_logs")
    op.drop_table("ingestion_logs")

    op.drop_table("app_settings")

    op.drop_index("ix_media_items_title_clean", table_name="media_items")
    op.drop_index("ix_media_items_title", table_name="media_items")
    op.drop_index("ix_media_items_media_type", table_name="media_items")
    op.drop_table("media_items")

    op.drop_index("ix_users_user_name", table_name="users")
    op.drop_table("users")
