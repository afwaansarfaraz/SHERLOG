"""Create audit_logs table for persistent human approval/rejection audit trail.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-17
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create audit_logs table."""
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False, primary_key=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("investigation_id", sa.String(length=36), nullable=False),
        sa.Column(
            "incident_id",
            sa.String(length=32),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("proposal_id", sa.String(length=64), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("details", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_audit_logs_id", "audit_logs", ["id"], unique=False)
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"], unique=False)
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
    op.create_index("ix_audit_logs_incident_id", "audit_logs", ["incident_id"], unique=False)
    op.create_index("ix_audit_logs_investigation_id", "audit_logs", ["investigation_id"], unique=False)
    op.create_index("ix_audit_logs_proposal_id", "audit_logs", ["proposal_id"], unique=False)


def downgrade() -> None:
    """Drop audit_logs table."""
    op.drop_index("ix_audit_logs_proposal_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_investigation_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_incident_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_timestamp", table_name="audit_logs")
    op.drop_index("ix_audit_logs_id", table_name="audit_logs")
    op.drop_table("audit_logs")
