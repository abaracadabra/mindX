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


@router.post("/memory/retrieve", summary="Retrieve memories using semantic search")
async def retrieve_memories(
    query: str = Body(..., description="Semantic search query"),
    agent_id: Optional[str] = Body(None, description="Filter by agent ID"),
    memory_type: Optional[str] = Body(None, description="Filter by memory type"),
    top_k: int = Body(10, description="Number of memories to retrieve"),
    min_similarity: float = Body(0.5, description="Minimum similarity threshold")
):
    """Retrieve memories using semantic search for mindXagent context"""
    try:
        ingestion, retrieval = get_engines()

        # First try to retrieve from RAGE system (ingested documents)
        try:
            contexts = await retrieval.retrieve_context(
                query=query,
                top_k=top_k,
                min_similarity=min_similarity,
                tags=["memory"] if not agent_id else ["memory", agent_id]
            )
        except Exception as e:
            logger.warning(f"RAGE retrieval failed, falling back to memory agent: {e}")
            contexts = []

        # If RAGE retrieval failed or returned no results, try memory agent
        if not contexts:
            try:
                from agents.memory_agent import MemoryAgent
                memory_agent = MemoryAgent()

                # Use semantic search if available, otherwise fallback to file-based search
                if hasattr(memory_agent, 'query_memories_semantic'):
                    memories = await memory_agent.query_memories_semantic(
                        query=query,
                        agent_id=agent_id,
                        memory_type=memory_type,
                        limit=top_k,
                        min_similarity=min_similarity
                    )
                else:
                    # Fallback to file-based search
                    memories = await memory_agent.get_memories_by_agent(
                        agent_id=agent_id or "mindxagent",
                        limit=top_k
                    )

                # Convert memory format to context format
                contexts = []
                for memory in memories:
                    contexts.append({
                        "content": json.dumps(memory.content) if isinstance(memory.content, dict) else str(memory.content),
                        "metadata": {
                            "agent_id": memory.agent_id,
                            "memory_type": memory.memory_type,
                            "importance": memory.importance,
                            "timestamp": memory.timestamp.isoformat() if hasattr(memory.timestamp, 'isoformat') else str(memory.timestamp),
                            "source": "memory_agent"
                        },
                        "similarity": getattr(memory, 'similarity', 1.0),
                        "doc_id": f"memory_{memory.memory_id}" if hasattr(memory, 'memory_id') else f"memory_{len(contexts)}"
                    })

            except Exception as e:
                logger.error(f"Memory agent fallback failed: {e}")

        return {
            "success": True,
            "query": query,
            "contexts": contexts,
            "count": len(contexts),
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(f"Failed to retrieve memories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve memories: {e}")


@router.post("/memory/store", summary="Store memory using RAGE ingestion")
async def store_memory(
    agent_id: str = Body(..., description="Agent ID"),
    memory_type: str = Body(..., description="Memory type"),
    content: Dict[str, Any] = Body(..., description="Memory content"),
    context: Optional[Dict[str, Any]] = Body(None, description="Additional context"),
    tags: Optional[List[str]] = Body(None, description="Memory tags")
):
    """Store memory using RAGE system for semantic retrieval"""
    try:
        ingestion, _ = get_engines()

        # Create memory document
        memory_doc = {
            "agent_id": agent_id,
            "memory_type": memory_type,
            "content": content,
            "context": context,
            "timestamp": time.time(),
            "tags": tags or []
        }

        # Convert to JSON string for ingestion
        memory_json = json.dumps(memory_doc, indent=2)

        # Create temporary file for ingestion
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            tmp_file.write(memory_json)
            tmp_path = tmp_file.name

        try:
            # Ingest the memory document
            result = await ingestion.ingest_file(
                file_path=tmp_path,
                tags=["memory", agent_id, memory_type] + (tags or []),
                metadata={
                    "memory_type": memory_type,
                    "agent_id": agent_id,
                    "timestamp": memory_doc["timestamp"]
                },
                auto_index=True
            )

            return {
                "success": True,
                "memory_id": result.get("doc_id"),
                "message": "Memory stored successfully",
                "timestamp": time.time()
            }

        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except Exception as e:
        logger.error(f"Failed to store memory: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to store memory: {e}")


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


