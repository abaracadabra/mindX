"""
RAGE Retrieval Engine

Provides intelligent retrieval of relevant context from ingested documents.
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from utils.logging_config import get_logger
from .storage import StorageEngine
from .indexing import IndexingEngine

logger = get_logger(__name__)


class RetrievalEngine:
    """
    Retrieval engine for RAGE system.
    
    Provides context retrieval for LLM generation.
    """
    
    def __init__(
        self,
        storage_engine: StorageEngine,
        indexing_engine: Optional[IndexingEngine] = None
    ):
        self.storage = storage_engine
        self.indexing = indexing_engine
    
    async def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.5,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context for a query.
        
        Returns:
            List of context dictionaries with doc_id, content, similarity, and metadata
        """
        results = []
        
        # Use vector search if available
        if self.indexing:
            search_results = await self.indexing.search(query, top_k=top_k * 2)  # Get more for filtering
            
            for doc_id, similarity, metadata in search_results:
                if similarity < min_similarity:
                    continue
                
                # Filter by tags if provided
                if tags and not any(tag in metadata.tags for tag in tags):
                    continue
                
                # Get document content
                content = self.storage.get_document(doc_id)
                if not content:
                    continue
                
                # Extract text (simplified - in production would use proper extraction)
                try:
                    text_content = content.decode('utf-8')
                except:
                    text_content = str(content)[:1000]  # Fallback
                
                results.append({
                    "doc_id": doc_id,
                    "content": text_content[:2000],  # Limit content length
                    "similarity": similarity,
                    "metadata": {
                        "source_path": metadata.source_path,
                        "file_type": metadata.file_type,
                        "tags": metadata.tags,
                        "ingested_at": metadata.ingested_at
                    }
                })
                
                if len(results) >= top_k:
                    break
        else:
            # Fallback to tag-based retrieval
            documents = self.storage.list_documents(tags=tags)
            for metadata in documents[:top_k]:
                content = self.storage.get_document(metadata.doc_id)
                if content:
                    try:
                        text_content = content.decode('utf-8')
                    except:
                        text_content = str(content)[:1000]
                    
                    results.append({
                        "doc_id": metadata.doc_id,
                        "content": text_content[:2000],
                        "similarity": 0.5,  # Default similarity for non-vector search
                        "metadata": {
                            "source_path": metadata.source_path,
                            "file_type": metadata.file_type,
                            "tags": metadata.tags,
                            "ingested_at": metadata.ingested_at
                        }
                    })
        
        return results
    
    async def retrieve_for_llm(
        self,
        query: str,
        max_context_length: int = 4000,
        top_k: int = 5
    ) -> str:
        """
        Retrieve and format context for LLM consumption.
        
        Returns formatted context string ready for LLM prompt.
        """
        contexts = await self.retrieve_context(query, top_k=top_k)
        
        formatted_contexts = []
        total_length = 0
        
        for ctx in contexts:
            context_text = f"[Source: {ctx['metadata']['source_path']}]\n{ctx['content']}\n"
            
            if total_length + len(context_text) > max_context_length:
                break
            
            formatted_contexts.append(context_text)
            total_length += len(context_text)
        
        return "\n---\n".join(formatted_contexts)
    
    def get_retrieval_stats(self) -> Dict[str, Any]:
        """Get retrieval system statistics"""
        all_docs = self.storage.list_documents()
        
        stats = {
            "total_documents": len(all_docs),
            "total_size_bytes": sum(doc.file_size for doc in all_docs),
            "indexed_documents": 0,
            "index_vectors": 0
        }
        
        if self.indexing:
            index_stats = self.indexing.get_index_stats()
            stats["indexed_documents"] = index_stats.get("total_documents", 0)
            stats["index_vectors"] = index_stats.get("total_vectors", 0)
        
        return stats


