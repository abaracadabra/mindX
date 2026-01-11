"""
RAGE API Routes

FastAPI routes for RAGE (Retrieval Augmented Generative Engine) system.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Body
from typing import Optional, List, Dict, Any
from pathlib import Path
import time

from .ingestion import IngestionEngine
from .retrieval import RetrievalEngine
from .storage import StorageEngine
from .indexing import IndexingEngine
from utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/rage", tags=["RAGE"])

# Global engines (initialized on first use)
_ingestion_engine: Optional[IngestionEngine] = None
_retrieval_engine: Optional[RetrievalEngine] = None


def get_engines():
    """Get or create RAGE engines"""
    global _ingestion_engine, _retrieval_engine
    
    if _ingestion_engine is None:
        storage = StorageEngine()
        indexing = IndexingEngine(storage_engine=storage)
        _ingestion_engine = IngestionEngine(
            storage_engine=storage,
            indexing_engine=indexing
        )
        _retrieval_engine = RetrievalEngine(
            storage_engine=storage,
            indexing_engine=indexing
        )
    
    return _ingestion_engine, _retrieval_engine


@router.post("/ingest/file", summary="Ingest a file")
async def ingest_file(
    file: UploadFile = File(...),
    tags: Optional[List[str]] = Body(None),
    auto_index: bool = Body(True)
):
    """Ingest a file into the RAGE system"""
    try:
        ingestion, _ = get_engines()
        
        # Save uploaded file temporarily
        from tempfile import NamedTemporaryFile
        import os
        
        with NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            result = await ingestion.ingest_file(
                file_path=tmp_path,
                tags=tags,
                metadata={"original_filename": file.filename},
                auto_index=auto_index
            )
            return result
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
    except Exception as e:
        logger.error(f"Failed to ingest file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest file: {e}")


@router.post("/ingest/path", summary="Ingest a file or directory by path")
async def ingest_path(
    path: str = Body(...),
    recursive: bool = Body(True),
    file_patterns: Optional[List[str]] = Body(None),
    tags: Optional[List[str]] = Body(None)
):
    """Ingest a file or directory by path"""
    try:
        ingestion, _ = get_engines()
        path_obj = Path(path)
        
        if path_obj.is_file():
            result = await ingestion.ingest_file(path_obj, tags=tags)
            return {"success": True, "results": [result]}
        elif path_obj.is_dir():
            result = await ingestion.ingest_directory(
                path_obj,
                recursive=recursive,
                file_patterns=file_patterns,
                tags=tags
            )
            return result
        else:
            raise HTTPException(status_code=404, detail=f"Path not found: {path}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to ingest path: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest path: {e}")


@router.post("/retrieve", summary="Retrieve context for a query")
async def retrieve_context(
    query: str = Body(...),
    top_k: int = Body(5),
    min_similarity: float = Body(0.5),
    tags: Optional[List[str]] = Body(None)
):
    """Retrieve relevant context for a query"""
    try:
        _, retrieval = get_engines()
        contexts = await retrieval.retrieve_context(
            query=query,
            top_k=top_k,
            min_similarity=min_similarity,
            tags=tags
        )
        return {
            "success": True,
            "query": query,
            "contexts": contexts,
            "count": len(contexts)
        }
    except Exception as e:
        logger.error(f"Failed to retrieve context: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve context: {e}")


@router.post("/retrieve/for-llm", summary="Retrieve formatted context for LLM")
async def retrieve_for_llm(
    query: str = Body(...),
    max_context_length: int = Body(4000),
    top_k: int = Body(5)
):
    """Retrieve and format context for LLM consumption"""
    try:
        _, retrieval = get_engines()
        context = await retrieval.retrieve_for_llm(
            query=query,
            max_context_length=max_context_length,
            top_k=top_k
        )
        return {
            "success": True,
            "query": query,
            "context": context,
            "context_length": len(context)
        }
    except Exception as e:
        logger.error(f"Failed to retrieve context for LLM: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve context: {e}")


@router.get("/documents", summary="List all ingested documents")
async def list_documents(
    tags: Optional[List[str]] = Query(None)
):
    """List all ingested documents"""
    try:
        ingestion, _ = get_engines()
        documents = ingestion.storage.list_documents(tags=tags)
        
        return {
            "success": True,
            "documents": [
                {
                    "doc_id": doc.doc_id,
                    "source_path": doc.source_path,
                    "file_type": doc.file_type,
                    "file_size": doc.file_size,
                    "ingested_at": doc.ingested_at,
                    "tags": doc.tags,
                    "access_count": doc.access_count
                }
                for doc in documents
            ],
            "count": len(documents)
        }
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {e}")


@router.get("/documents/{doc_id}", summary="Get document content")
async def get_document(doc_id: str):
    """Get document content by ID"""
    try:
        ingestion, _ = get_engines()
        content = ingestion.storage.get_document(doc_id)
        metadata = ingestion.storage.get_metadata(doc_id)
        
        if not content:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
        
        # Try to decode as text
        try:
            text_content = content.decode('utf-8')
        except:
            text_content = None
        
        return {
            "success": True,
            "doc_id": doc_id,
            "metadata": {
                "source_path": metadata.source_path,
                "file_type": metadata.file_type,
                "file_size": metadata.file_size,
                "ingested_at": metadata.ingested_at,
                "tags": metadata.tags
            },
            "content": text_content,
            "content_size": len(content)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get document: {e}")


@router.delete("/documents/{doc_id}", summary="Delete a document")
async def delete_document(doc_id: str):
    """Delete a document from RAGE"""
    try:
        ingestion, _ = get_engines()
        success = ingestion.storage.delete_document(doc_id)
        
        if success:
            return {"success": True, "message": f"Document {doc_id} deleted"}
        else:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {e}")


@router.get("/stats", summary="Get RAGE system statistics")
async def get_rage_stats():
    """Get RAGE system statistics"""
    try:
        _, retrieval = get_engines()
        stats = retrieval.get_retrieval_stats()
        return {
            "success": True,
            "stats": stats,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Failed to get RAGE stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get RAGE stats: {e}")


