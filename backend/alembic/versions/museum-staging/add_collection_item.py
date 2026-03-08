"""Add collection_item table

Revision ID: a1b2c3d4e5f6
Revises: 703ea995db4b
Create Date: 2025-03-08

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "703ea995db4b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "collection_item",
        sa.Column(
            "inserted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "id",
            postgresql.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(),
            sa.ForeignKey("museum_sources.user.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("image_uri", sa.String(2048), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("audio_uri", sa.String(2048), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="museum_sources",
    )
    op.create_index(
        "ix_collection_item_user_id",
        "collection_item",
        ["user_id"],
        schema="museum_sources",
    )


def downgrade():
    op.drop_table("collection_item", schema="museum_sources")
