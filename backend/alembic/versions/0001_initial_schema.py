"""initial schema: users and screenings

Revision ID: 0001
Revises:
Create Date: 2026-10-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# JSONB on Postgres, plain JSON elsewhere (matches app.db.models.JSONType).
JSONType = sa.JSON(none_as_null=True).with_variant(postgresql.JSONB(none_as_null=True), "postgresql")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("consent_version", sa.String(length=32), nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "screenings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("inputs", JSONType, nullable=False),
        sa.Column("lab_inputs", JSONType, nullable=True),
        sa.Column("tier1_probability", sa.Float(), nullable=False),
        sa.Column("tier1_flagged", sa.Boolean(), nullable=False),
        sa.Column("tier2_probability", sa.Float(), nullable=True),
        sa.Column("tier2_flagged", sa.Boolean(), nullable=True),
        sa.Column("recommendation", sa.String(length=32), nullable=False),
        sa.Column("factors", JSONType, nullable=False),
        sa.Column("report_text", sa.Text(), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False),
        sa.Column("tier2_model_version", sa.String(length=32), nullable=True),
        sa.Column("model_validated", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "tier1_probability >= 0 AND tier1_probability <= 1",
            name=op.f("ck_screenings_tier1_probability_range"),
        ),
        sa.CheckConstraint(
            "tier2_probability IS NULL OR (tier2_probability >= 0 AND tier2_probability <= 1)",
            name=op.f("ck_screenings_tier2_probability_range"),
        ),
        sa.CheckConstraint(
            "(tier2_probability IS NULL) = (tier2_flagged IS NULL)",
            name=op.f("ck_screenings_tier2_consistent"),
        ),
        sa.CheckConstraint(
            "recommendation IN ('low_risk', 'elevated_needs_labs', "
            "'elevated_confirmed', 'elevated_not_confirmed')",
            name=op.f("ck_screenings_recommendation_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name=op.f("fk_screenings_user_id_users"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_screenings")),
    )
    op.create_index("ix_screenings_user_created", "screenings", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_screenings_user_created", table_name="screenings")
    op.drop_table("screenings")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
