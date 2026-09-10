"""Create the transactional exposure ledger."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260910_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("employee_id", sa.String(), nullable=False),
        sa.Column("trust_zone_id", sa.String(), nullable=False),
        sa.Column("initial_budget", sa.Integer(), nullable=False),
        sa.Column("remaining_budget", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_trust_zone_id", "sessions", ["trust_zone_id"])
    op.create_table(
        "exposure_claims",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("trust_zone_id", sa.String(), nullable=False),
        sa.Column("protected_entity_id", sa.String(), nullable=False),
        sa.Column("dimension", sa.String(), nullable=False),
        sa.Column("semantic_key", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("safe_representation", sa.String(), nullable=False),
        sa.Column("representation_hash", sa.String(), nullable=False),
        sa.Column("precision", sa.String(), nullable=False),
        sa.Column("base_weight", sa.Integer(), nullable=False),
        sa.Column("first_exposed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_exposed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trust_zone_id", "protected_entity_id", "semantic_key"),
    )
    op.create_index("ix_exposure_claims_trust_zone_id", "exposure_claims", ["trust_zone_id"])
    op.create_index(
        "ix_exposure_claims_protected_entity_id",
        "exposure_claims",
        ["protected_entity_id"],
    )
    op.create_table(
        "exposure_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("protected_entity_id", sa.String(), nullable=False),
        sa.Column("semantic_key", sa.String(), nullable=False),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("reason_code", sa.String(), nullable=False),
        sa.Column("risk_before", sa.Integer(), nullable=False),
        sa.Column("risk_after", sa.Integer(), nullable=False),
        sa.Column("disclosure_delta", sa.Integer(), nullable=False),
        sa.Column("budget_cost", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("exposure_events")
    op.drop_index("ix_exposure_claims_protected_entity_id", table_name="exposure_claims")
    op.drop_index("ix_exposure_claims_trust_zone_id", table_name="exposure_claims")
    op.drop_table("exposure_claims")
    op.drop_index("ix_sessions_trust_zone_id", table_name="sessions")
    op.drop_table("sessions")
