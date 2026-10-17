"""PostgreSQL Knowledge Document and Vector Chunk SQLAlchemy Models for Sherlog RAG."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Column, String, Text, DateTime, JSON, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship

from backend.app.db.base import Base


class KnowledgeDocumentModel(Base):
    """PostgreSQL database table model for knowledge base documents (runbooks, architecture, postmortems)."""

    __tablename__ = "knowledge_documents"

    id = Column(
        String(36),
        primary_key=True,
        index=True,
        doc="Unique UUID document identifier",
    )
    doc_id = Column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
        doc="Human-readable unique document identifier (e.g. runbook:database_pool_exhaustion)",
    )
    title = Column(
        String(256),
        nullable=False,
        doc="Human-readable title of the document or runbook",
    )
    doc_type = Column(
        String(64),
        nullable=False,
        default="runbook",
        index=True,
        doc="Document category (runbook, architecture, service_doc, historical_incident)",
    )
    service = Column(
        String(64),
        nullable=False,
        default="all",
        index=True,
        doc="Service associated with this knowledge item (orders, payments, api, or all)",
    )
    source = Column(
        String(256),
        nullable=False,
        doc="Relative path or URI of source documentation",
    )
    raw_content = Column(
        Text,
        nullable=False,
        doc="Full unchunked raw markdown or text document content",
    )
    extra_metadata = Column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
        doc="Arbitrary document metadata tags, authors, version",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Creation timestamp",
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        doc="Last modified timestamp",
    )

    chunks = relationship(
        "KnowledgeChunkModel",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="KnowledgeChunkModel.chunk_index",
    )


class KnowledgeChunkModel(Base):
    """PostgreSQL database table model for vector embedding chunks of knowledge documents."""

    __tablename__ = "knowledge_chunks"

    id = Column(
        String(36),
        primary_key=True,
        index=True,
        doc="Unique UUID chunk identifier",
    )
    document_id = Column(
        String(36),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key reference to parent KnowledgeDocumentModel",
    )
    doc_id = Column(
        String(128),
        nullable=False,
        index=True,
        doc="Parent document human-readable ID",
    )
    chunk_index = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Sequential zero-indexed chunk position in document",
    )
    title = Column(
        String(256),
        nullable=False,
        doc="Title of the chunk or section header",
    )
    source = Column(
        String(256),
        nullable=False,
        doc="Source documentation path reference",
    )
    service = Column(
        String(64),
        nullable=False,
        default="all",
        index=True,
        doc="Associated service",
    )
    content = Column(
        Text,
        nullable=False,
        doc="Text content of the chunk bounded for retrieval",
    )
    embedding = Column(
        JSON,
        nullable=False,
        default=list,
        doc="Dense vector embedding represented as JSON float array",
    )
    embedding_model = Column(
        String(128),
        nullable=False,
        default="BAAI/bge-small-en-v1.5",
        doc="Model ID used to produce embedding vector",
    )
    extra_metadata = Column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
        doc="Chunk metadata, tags, and section hierarchy",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Creation timestamp",
    )

    document = relationship("KnowledgeDocumentModel", back_populates="chunks")

    __table_args__ = (
        Index("idx_knowledge_chunks_doc_chunk", "doc_id", "chunk_index"),
        Index("idx_knowledge_chunks_service", "service"),
    )
