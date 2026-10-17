"""Create investigations and investigation_checkpoints tables.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-15
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create investigations and investigation_checkpoints tables."""
    # 1. Create investigations table
    op.create_table(
        "investigations",
        sa.Column("id", sa.String(length=36), nullable=False, primary_key=True),
        sa.Column(
            "incident_id",
            sa.String(length=32),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="QUEUED"),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("hypotheses", sa.JSON(), nullable=False),
        sa.Column("evaluation", sa.JSON(), nullable=False),
        sa.Column("root_cause", sa.String(length=128), nullable=True),
        sa.Column("investigation_source", sa.String(length=32), nullable=False, server_default="llm"),
        sa.Column("tool_executions", sa.JSON(), nullable=False),
        sa.Column("budget_consumed", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_investigations_id", "investigations", ["id"], unique=False)
    op.create_index("ix_investigations_incident_id", "investigations", ["incident_id"], unique=False)
    op.create_index("ix_investigations_state", "investigations", ["state"], unique=False)
    op.create_index("idx_investigations_incident_state", "investigations", ["incident_id", "state"], unique=False)
    op.create_index("idx_investigations_started_at", "investigations", ["started_at"], unique=False)

    # 2. Create investigation_checkpoints table
    op.create_table(
        "investigation_checkpoints",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, primary_key=True),
        sa.Column(
            "investigation_id",
            sa.String(length=36),
            sa.ForeignKey("investigations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("incident_id", sa.String(length=32), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_checkpoints_inv_id", "investigation_checkpoints", ["investigation_id"], unique=False)
    op.create_index("ix_checkpoints_incident_id", "investigation_checkpoints", ["incident_id"], unique=False)
    op.create_index("idx_checkpoints_inv_step", "investigation_checkpoints", ["investigation_id", "step"], unique=False)


def downgrade() -> None:
    """Drop investigations and investigation_checkpoints tables."""
    op.drop_index("idx_checkpoints_inv_step", table_name="investigation_checkpoints")
    op.drop_index("ix_checkpoints_incident_id", table_name="investigation_checkpoints")
    op.drop_index("ix_checkpoints_inv_id", table_name="investigation_checkpoints")
    op.drop_table("investigation_checkpoints")

    op.drop_index("idx_investigations_started_at", table_name="investigations")
    op.drop_index("idx_investigations_incident_state", table_name="investigations")
    op.drop_index("ix_investigations_state", table_name="investigations")
    op.drop_index("ix_investigations_incident_id", table_name="investigations")
    op.drop_index("ix_investigations_id", table_name="investigations")
    op.drop_table("investigations")
