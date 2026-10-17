"""Knowledge base ingestion and chunking module for Sherlog Vector RAG.

Reads operational runbooks, architecture documentation, and historical postmortems,
chunks them into bounded semantic segments, computes vector embeddings, and persists
them into PostgreSQL.
"""

from datetime import datetime, timezone
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy.orm import Session

from backend.app.db.models.knowledge import KnowledgeChunkModel, KnowledgeDocumentModel
from backend.app.investigation.embeddings import EmbeddingProvider, get_embedding_provider

logger = logging.getLogger(__name__)


class DocumentChunk:
    """Represents a discrete text chunk with associated document metadata."""

    def __init__(
        self,
        doc_id: str,
        chunk_index: int,
        title: str,
        content: str,
        source: str,
        service: str = "all",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.doc_id = doc_id
        self.chunk_index = chunk_index
        self.title = title
        self.content = content.strip()
        self.source = source
        self.service = service
        self.metadata = metadata or {}


def chunk_markdown_document(
    content: str,
    doc_id: str,
    title: str,
    source: str,
    service: str = "all",
    max_chunk_chars: int = 800,
    min_chunk_chars: int = 100,
) -> List[DocumentChunk]:
    """Chunk a markdown document into semantic sections based on headers and paragraphs."""
    chunks: List[DocumentChunk] = []
    
    # Split by markdown headers (## or #)
    sections = re.split(r"\n(?=#{1,3}\s+)", content)
    
    chunk_idx = 0
    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue
            
        # Extract section header if present
        header_match = re.match(r"^#{1,3}\s+(.+)$", sec, flags=re.MULTILINE)
        section_title = header_match.group(1).strip() if header_match else title
        
        # If section is small enough, keep as single chunk
        if len(sec) <= max_chunk_chars:
            chunks.append(
                DocumentChunk(
                    doc_id=doc_id,
                    chunk_index=chunk_idx,
                    title=f"{title} - {section_title}" if section_title != title else title,
                    content=sec,
                    source=source,
                    service=service,
                    metadata={"section": section_title, "length": len(sec)},
                )
            )
            chunk_idx += 1
        else:
            # Split longer sections by double newlines (paragraphs)
            paragraphs = sec.split("\n\n")
            current_buffer = ""
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                if len(current_buffer) + len(para) + 2 <= max_chunk_chars:
                    current_buffer = f"{current_buffer}\n\n{para}".strip()
                else:
                    if len(current_buffer) >= min_chunk_chars:
                        chunks.append(
                            DocumentChunk(
                                doc_id=doc_id,
                                chunk_index=chunk_idx,
                                title=f"{title} - {section_title}",
                                content=current_buffer,
                                source=source,
                                service=service,
                                metadata={"section": section_title, "length": len(current_buffer)},
                            )
                        )
                        chunk_idx += 1
                    current_buffer = para
            if current_buffer and len(current_buffer) >= min_chunk_chars:
                chunks.append(
                    DocumentChunk(
                        doc_id=doc_id,
                        chunk_index=chunk_idx,
                        title=f"{title} - {section_title}",
                        content=current_buffer,
                        source=source,
                        service=service,
                        metadata={"section": section_title, "length": len(current_buffer)},
                    )
                )
                chunk_idx += 1

    return chunks


class KnowledgeIngestionManager:
    """Manages document chunking, embedding generation, and database vector persistence."""

    def __init__(
        self,
        db: Session,
        embedding_provider: Optional[EmbeddingProvider] = None,
    ):
        self.db = db
        self.embedding_provider = embedding_provider or get_embedding_provider()

    def ingest_document(
        self,
        doc_id: str,
        title: str,
        content: str,
        source: str,
        doc_type: str = "runbook",
        service: str = "all",
        metadata: Optional[Dict[str, Any]] = None,
        force_reembed: bool = False,
    ) -> int:
        """Ingest or update a single document with chunking and embeddings.

        Returns:
            Number of chunks persisted.
        """
        # 1. Check existing document
        existing_doc = (
            self.db.query(KnowledgeDocumentModel)
            .filter(KnowledgeDocumentModel.doc_id == doc_id)
            .first()
        )

        now_utc = datetime.now(timezone.utc)
        if not existing_doc:
            doc_model = KnowledgeDocumentModel(
                id=str(uuid.uuid4()),
                doc_id=doc_id,
                title=title,
                doc_type=doc_type,
                service=service,
                source=source,
                raw_content=content,
                extra_metadata=metadata or {},
                created_at=now_utc,
                updated_at=now_utc,
            )
            self.db.add(doc_model)
            self.db.flush()
        else:
            doc_model = existing_doc
            doc_model.title = title
            doc_model.source = source
            doc_model.service = service
            doc_model.raw_content = content
            doc_model.extra_metadata = metadata or {}
            doc_model.updated_at = now_utc
            # Delete existing chunks for full clean re-ingest
            self.db.query(KnowledgeChunkModel).filter(KnowledgeChunkModel.document_id == doc_model.id).delete()
            self.db.flush()

        # 2. Chunk document content
        chunks = chunk_markdown_document(
            content=content,
            doc_id=doc_id,
            title=title,
            source=source,
            service=service,
        )

        if not chunks:
            self.db.commit()
            return 0

        # 3. Compute vector embeddings in batch
        texts_to_embed = [c.content for c in chunks]
        try:
            embeddings = self.embedding_provider.embed_batch(texts_to_embed)
        except Exception as exc:
            logger.warning("Embedding generation failed: %s. Using fallback.", exc)
            fallback = get_embedding_provider("fallback")
            embeddings = fallback.embed_batch(texts_to_embed)

        # 4. Save chunks with embeddings to PostgreSQL
        for chunk, emb in zip(chunks, embeddings):
            chunk_model = KnowledgeChunkModel(
                id=str(uuid.uuid4()),
                document_id=doc_model.id,
                doc_id=doc_id,
                chunk_index=chunk.chunk_index,
                title=chunk.title,
                source=chunk.source,
                service=chunk.service,
                content=chunk.content,
                embedding=emb,
                embedding_model=self.embedding_provider.provider_name,
                extra_metadata=chunk.metadata,
                created_at=now_utc,
            )
            self.db.add(chunk_model)

        self.db.commit()
        logger.info("Ingested document '%s' with %d chunks into knowledge base", doc_id, len(chunks))
        return len(chunks)

    def ingest_directory(
        self,
        docs_dir: Path,
        doc_type: str = "runbook",
    ) -> Dict[str, int]:
        """Ingest all markdown files in a directory."""
        results = {}
        if not docs_dir.exists():
            return results

        for file_path in docs_dir.glob("*.md"):
            try:
                content = file_path.read_text(encoding="utf-8")
                doc_id = f"{doc_type}:{file_path.stem}"
                # Derive title from first line or file stem
                first_line = content.splitlines()[0] if content else ""
                title = first_line.lstrip("#").strip() if first_line.startswith("#") else file_path.stem.replace("_", " ").title()
                
                # Derive service from content or filename
                service = "all"
                if "orders" in file_path.stem:
                    service = "orders"
                elif "payments" in file_path.stem:
                    service = "payments"
                elif "api" in file_path.stem:
                    service = "api"

                count = self.ingest_document(
                    doc_id=doc_id,
                    title=title,
                    content=content,
                    source=str(file_path.relative_to(docs_dir.parent.parent) if docs_dir.parent.parent in file_path.parents else file_path),
                    doc_type=doc_type,
                    service=service,
                )
                results[doc_id] = count
            except Exception as exc:
                logger.error("Failed to ingest file %s: %s", file_path, exc)
                results[str(file_path.stem)] = 0

        return results
