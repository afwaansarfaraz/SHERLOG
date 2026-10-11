"""Create incidents table and tracking sequence.

Revision ID: 0001
Revises: None
Create Date: 2026-10-09
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.schema import CreateSequence, DropSequence, Sequence as SASequence

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

incident_seq = SASequence("incident_id_seq", start=1)


def upgrade() -> None:
    """Create sequence, incidents table, and performance indexes."""
    # 1. Create global sequence for human-readable sequential IDs
    op.execute(CreateSequence(incident_seq))

    # 2. Create incidents table
    op.create_table(
        "incidents",
        sa.Column("id", sa.String(length=32), nullable=False, primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("service", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="OPEN"),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="alertmanager"),
        sa.Column("affected_endpoints", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("fingerprint", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )

    # 3. Create indexes for fast querying and deduplication
    op.create_index("ix_incidents_id", "incidents", ["id"], unique=False)
    op.create_index("ix_incidents_service", "incidents", ["service"], unique=False)
    op.create_index("ix_incidents_fingerprint", "incidents", ["fingerprint"], unique=False)
    op.create_index("idx_incidents_service_status", "incidents", ["service", "status"], unique=False)
    op.create_index(
        "idx_incidents_created_at_desc",
        "incidents",
        [sa.text("created_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    """Drop incidents table and tracking sequence."""
    op.drop_index("idx_incidents_created_at_desc", table_name="incidents")
    op.drop_index("idx_incidents_service_status", table_name="incidents")
    op.drop_index("ix_incidents_fingerprint", table_name="incidents")
    op.drop_index("ix_incidents_service", table_name="incidents")
    op.drop_index("ix_incidents_id", table_name="incidents")
    op.drop_table("incidents")
    op.execute(DropSequence(incident_seq))
