"""Create knowledge_documents and knowledge_chunks tables for Vector RAG.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-15
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create knowledge_documents and knowledge_chunks tables with graceful pgvector handling."""
    bind = op.get_bind()

    # Safely check whether vector extension is available in PostgreSQL before attempting creation
    if bind.dialect.name == "postgresql":
        try:
            has_ext = bind.execute(sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector';")).scalar()
            if has_ext:
                bind.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector;"))
        except Exception:
            pass

    # 1. Create knowledge_documents table
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.String(length=36), nullable=False, primary_key=True),
        sa.Column("doc_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("doc_type", sa.String(length=64), nullable=False, server_default="runbook"),
        sa.Column("service", sa.String(length=64), nullable=False, server_default="all"),
        sa.Column("source", sa.String(length=256), nullable=False),
        sa.Column("raw_content", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("doc_id", name="uq_knowledge_doc_id"),
    )

    op.create_index("ix_knowledge_documents_id", "knowledge_documents", ["id"], unique=False)
    op.create_index("ix_knowledge_documents_doc_id", "knowledge_documents", ["doc_id"], unique=True)
    op.create_index("ix_knowledge_documents_service", "knowledge_documents", ["service"], unique=False)
    op.create_index("ix_knowledge_documents_doc_type", "knowledge_documents", ["doc_type"], unique=False)

    # 2. Create knowledge_chunks table
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(length=36), nullable=False, primary_key=True),
        sa.Column(
            "document_id",
            sa.String(length=36),
            sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("doc_id", sa.String(length=128), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("source", sa.String(length=256), nullable=False),
        sa.Column("service", sa.String(length=64), nullable=False, server_default="all"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=False),
        sa.Column("embedding_model", sa.String(length=128), nullable=False, server_default="BAAI/bge-small-en-v1.5"),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_knowledge_chunks_id", "knowledge_chunks", ["id"], unique=False)
    op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"], unique=False)
    op.create_index("ix_knowledge_chunks_doc_id", "knowledge_chunks", ["doc_id"], unique=False)
    op.create_index("ix_knowledge_chunks_service", "knowledge_chunks", ["service"], unique=False)
    op.create_index("idx_knowledge_chunks_doc_chunk", "knowledge_chunks", ["doc_id", "chunk_index"], unique=False)


def downgrade() -> None:
    """Drop knowledge_chunks and knowledge_documents tables."""
    op.drop_index("idx_knowledge_chunks_doc_chunk", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_service", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_doc_id", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_document_id", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")

    op.drop_index("ix_knowledge_documents_doc_type", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_service", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_doc_id", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_id", table_name="knowledge_documents")
    op.drop_table("knowledge_documents")
