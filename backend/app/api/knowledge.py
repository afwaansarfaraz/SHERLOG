"""Knowledge Base API endpoints for document management and RAG ingestion.

Provides CRUD operations for operational runbooks, architecture docs, and postmortems.
Documents are chunked, embedded, and persisted for vector retrieval during investigations.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.db.models.knowledge import KnowledgeDocumentModel, KnowledgeChunkModel
from backend.app.investigation.ingestion import KnowledgeIngestionManager

logger = logging.getLogger(__name__)

router = APIRouter()

# Maximum upload size: 2MB
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
SUPPORTED_CONTENT_TYPES = {
    "text/plain": "txt",
    "text/markdown": "markdown",
    "text/x-markdown": "markdown",
    "application/pdf": "pdf",
    "application/octet-stream": "auto",  # fallback, detect by extension
}
SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf", ".markdown"}


# ==========================================================================
# Response Schemas
# ==========================================================================

class ChunkResponse(BaseModel):
    id: str
    chunk_index: int
    title: str
    content_preview: str = Field(description="First 200 chars of chunk content")
    service: str
    embedding_model: str

class DocumentResponse(BaseModel):
    id: str
    doc_id: str
    title: str
    doc_type: str
    service: str
    source: str
    status: str = Field(default="indexed", description="Processing status: indexed, failed, processing")
    chunk_count: int = 0
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class DocumentDetailResponse(DocumentResponse):
    raw_content_preview: str = Field(default="", description="First 500 chars of raw content")
    chunks: List[ChunkResponse] = []
    metadata: Dict[str, Any] = {}

class UploadResponse(BaseModel):
    document: DocumentResponse
    chunks_created: int
    message: str


# ==========================================================================
# Helper Functions
# ==========================================================================

def _doc_to_response(doc: KnowledgeDocumentModel, chunk_count: int = 0) -> DocumentResponse:
    """Convert SQLAlchemy model to response schema."""
    return DocumentResponse(
        id=doc.id,
        doc_id=doc.doc_id,
        title=doc.title,
        doc_type=doc.doc_type,
        service=doc.service,
        source=doc.source,
        status="indexed" if chunk_count > 0 else "empty",
        chunk_count=chunk_count,
        error_message=None,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


def _extract_text_from_pdf(content_bytes: bytes) -> str:
    """Extract text from PDF bytes. Falls back to placeholder if PyPDF is unavailable."""
    try:
        import pypdf
        import io
        reader = pypdf.PdfReader(io.BytesIO(content_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)
    except ImportError:
        logger.warning("pypdf not installed; PDF text extraction unavailable")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="PDF processing requires the 'pypdf' package. Install it with: pip install pypdf",
        )
    except Exception as exc:
        logger.error("PDF extraction failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to extract text from PDF: {str(exc)}",
        )


# ==========================================================================
# Endpoints
# ==========================================================================

@router.get(
    "",
    response_model=List[DocumentResponse],
    summary="List all knowledge base documents",
)
def list_documents(db: Session = Depends(get_db)) -> List[DocumentResponse]:
    """Retrieve all indexed knowledge documents with their chunk counts."""
    docs = (
        db.query(KnowledgeDocumentModel)
        .order_by(KnowledgeDocumentModel.updated_at.desc())
        .all()
    )
    results = []
    for doc in docs:
        chunk_count = (
            db.query(KnowledgeChunkModel)
            .filter(KnowledgeChunkModel.document_id == doc.id)
            .count()
        )
        results.append(_doc_to_response(doc, chunk_count))
    return results


@router.get(
    "/{doc_id:path}",
    response_model=DocumentDetailResponse,
    summary="Get document details with chunks",
)
def get_document(doc_id: str, db: Session = Depends(get_db)) -> DocumentDetailResponse:
    """Retrieve a single knowledge document with its chunks and metadata."""
    doc = (
        db.query(KnowledgeDocumentModel)
        .filter(KnowledgeDocumentModel.doc_id == doc_id)
        .first()
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found",
        )

    chunks = (
        db.query(KnowledgeChunkModel)
        .filter(KnowledgeChunkModel.document_id == doc.id)
        .order_by(KnowledgeChunkModel.chunk_index)
        .all()
    )

    chunk_responses = [
        ChunkResponse(
            id=c.id,
            chunk_index=c.chunk_index,
            title=c.title,
            content_preview=c.content[:200] if c.content else "",
            service=c.service,
            embedding_model=c.embedding_model,
        )
        for c in chunks
    ]

    return DocumentDetailResponse(
        id=doc.id,
        doc_id=doc.doc_id,
        title=doc.title,
        doc_type=doc.doc_type,
        service=doc.service,
        source=doc.source,
        status="indexed" if len(chunks) > 0 else "empty",
        chunk_count=len(chunks),
        error_message=None,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        raw_content_preview=(doc.raw_content or "")[:500],
        chunks=chunk_responses,
        metadata=doc.extra_metadata or {},
    )


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a document",
)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    doc_type: str = Form("runbook"),
    service: str = Form("all"),
    db: Session = Depends(get_db),
) -> UploadResponse:
    """Upload a document file (Markdown, TXT, or PDF), extract text, chunk, embed, and persist."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Validate extension
    filename_lower = file.filename.lower()
    ext = "." + filename_lower.rsplit(".", 1)[-1] if "." in filename_lower else ""
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    # Read file content with size limit
    content_bytes = await file.read()
    if len(content_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {MAX_UPLOAD_BYTES // (1024*1024)}MB",
        )

    if len(content_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Extract text content
    if ext == ".pdf":
        text_content = _extract_text_from_pdf(content_bytes)
    else:
        try:
            text_content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="File is not valid UTF-8 text",
            )

    if not text_content.strip():
        raise HTTPException(status_code=400, detail="Extracted text content is empty")

    # Derive title from filename if not provided
    doc_title = title or file.filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
    doc_id = f"upload:{uuid.uuid4().hex[:12]}"

    # Ingest using existing manager
    try:
        manager = KnowledgeIngestionManager(db=db)
        chunks_created = manager.ingest_document(
            doc_id=doc_id,
            title=doc_title,
            content=text_content,
            source=f"upload/{file.filename}",
            doc_type=doc_type,
            service=service,
        )
    except Exception as exc:
        logger.error("Ingestion failed for %s: %s", file.filename, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document ingestion failed: {str(exc)}",
        )

    # Fetch persisted document for response
    doc = (
        db.query(KnowledgeDocumentModel)
        .filter(KnowledgeDocumentModel.doc_id == doc_id)
        .first()
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document persisted but could not be retrieved",
        )

    return UploadResponse(
        document=_doc_to_response(doc, chunks_created),
        chunks_created=chunks_created,
        message=f"Successfully ingested '{doc_title}' with {chunks_created} chunks",
    )


@router.post(
    "/{doc_id:path}/retry",
    response_model=UploadResponse,
    summary="Retry ingestion for an existing document",
)
def retry_ingestion(doc_id: str, db: Session = Depends(get_db)) -> UploadResponse:
    """Re-chunk and re-embed an existing document's content."""
    doc = (
        db.query(KnowledgeDocumentModel)
        .filter(KnowledgeDocumentModel.doc_id == doc_id)
        .first()
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found",
        )

    try:
        manager = KnowledgeIngestionManager(db=db)
        chunks_created = manager.ingest_document(
            doc_id=doc.doc_id,
            title=doc.title,
            content=doc.raw_content,
            source=doc.source,
            doc_type=doc.doc_type,
            service=doc.service,
            force_reembed=True,
        )
    except Exception as exc:
        logger.error("Retry ingestion failed for %s: %s", doc_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Re-ingestion failed: {str(exc)}",
        )

    # Refresh document
    db.refresh(doc)
    return UploadResponse(
        document=_doc_to_response(doc, chunks_created),
        chunks_created=chunks_created,
        message=f"Re-ingested '{doc.title}' with {chunks_created} chunks",
    )


@router.delete(
    "/{doc_id:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a knowledge document and its chunks",
)
def delete_document(doc_id: str, db: Session = Depends(get_db)):
    """Remove a document and all its vector chunks from the knowledge base."""
    doc = (
        db.query(KnowledgeDocumentModel)
        .filter(KnowledgeDocumentModel.doc_id == doc_id)
        .first()
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found",
        )

    db.delete(doc)  # Cascades to chunks
    db.commit()
    logger.info("Deleted knowledge document '%s' and all chunks", doc_id)
