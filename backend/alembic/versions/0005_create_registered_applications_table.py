"""Create registered_applications table for application onboarding and inventory.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-18
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create registered_applications table."""
    op.create_table(
        "registered_applications",
        sa.Column("id", sa.String(length=64), nullable=False, primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("service_name", sa.String(length=64), nullable=False),
        sa.Column("environment", sa.String(length=32), nullable=False, server_default="production"),
        sa.Column("integration_type", sa.String(length=32), nullable=False, server_default="opentelemetry"),
        sa.Column("endpoint_url", sa.String(length=256), nullable=True),
        sa.Column("telemetry_config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="REGISTERED"),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_unique_constraint(
        "uq_registered_applications_service_env",
        "registered_applications",
        ["service_name", "environment"],
    )
    op.create_index("ix_registered_applications_service_name", "registered_applications", ["service_name"], unique=False)
    op.create_index("ix_registered_applications_status", "registered_applications", ["status"], unique=False)


def downgrade() -> None:
    """Drop registered_applications table."""
    op.drop_index("ix_registered_applications_status", table_name="registered_applications")
    op.drop_index("ix_registered_applications_service_name", table_name="registered_applications")
    op.drop_constraint("uq_registered_applications_service_env", "registered_applications", type_="unique")
    op.drop_table("registered_applications")
