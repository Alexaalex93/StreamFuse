"""add_samba_stream_source

Revision ID: 20260410_0002
Revises: 20260408_0001
Create Date: 2026-04-10 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260410_0002"
down_revision: str | None = "20260408_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

old_stream_source_enum = sa.Enum("tautulli", "sftpgo", name="stream_source", native_enum=False)
new_stream_source_enum = sa.Enum("tautulli", "sftpgo", "samba", name="stream_source", native_enum=False)


def upgrade() -> None:
    with op.batch_alter_table("unified_stream_sessions", recreate="always") as batch_op:
        batch_op.alter_column(
            "source",
            existing_type=old_stream_source_enum,
            type_=new_stream_source_enum,
            existing_nullable=False,
        )

    with op.batch_alter_table("ingestion_logs", recreate="always") as batch_op:
        batch_op.alter_column(
            "source",
            existing_type=old_stream_source_enum,
            type_=new_stream_source_enum,
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("unified_stream_sessions", recreate="always") as batch_op:
        batch_op.alter_column(
            "source",
            existing_type=new_stream_source_enum,
            type_=old_stream_source_enum,
            existing_nullable=False,
        )

    with op.batch_alter_table("ingestion_logs", recreate="always") as batch_op:
        batch_op.alter_column(
            "source",
            existing_type=new_stream_source_enum,
            type_=old_stream_source_enum,
            existing_nullable=False,
        )
