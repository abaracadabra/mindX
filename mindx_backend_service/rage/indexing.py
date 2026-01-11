"""
RAGE Indexing Engine

Creates searchable indexes from ingested documents using embeddings and vector search.
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import numpy as np

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger
from .storage import StorageEngine, DocumentMetadata

logger = get_logger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logger.warning("sentence-transformers or faiss not installed. Install with: pip install sentence-transformers faiss-cpu")


class IndexingEngine:
    """
    Indexing engine for RAGE system.
    
    Creates vector embeddings and searchable indexes from documents.
    """
    
    def __init__(
        self,
        storage_engine: StorageEngine,
        embedding_model: str = "all-MiniLM-L6-v2",
        index_path: Optional[Path] = None
    ):
        self.storage = storage_engine
        self.embedding_model_name = embedding_model
        self.index_path = index_path or (PROJECT_ROOT / "data" / "rage" / "indexes")
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        self.embedder = None
        self.index = None
        self.doc_id_to_index: Dict[str, int] = {}
        self.index_to_doc_id: Dict[int, str] = {}
        
        if EMBEDDINGS_AVAILABLE:
            self._initialize_embedder()
            self._load_index()
        else:
            logger.warning("Embeddings not available, indexing will be limited")
    
    def _initialize_embedder(self):
        """Initialize embedding model"""
        if not EMBEDDINGS_AVAILABLE:
            return
        
        try:
            self.embedder = SentenceTransformer(self.embedding_model_name)
            logger.info(f"Initialized embedding model: {self.embedding_model_name}")
        except Exception as e:
            logger.error(f"Error initializing embedder: {e}")
    
    def _load_index(self):
        """Load existing index from disk"""
        index_file = self.index_path / "faiss.index"
        mapping_file = self.index_path / "mapping.json"
        
        if index_file.exists() and mapping_file.exists():
            try:
                import json
                self.index = faiss.read_index(str(index_file))
                
                with open(mapping_file, 'r') as f:
                    mapping = json.load(f)
                    self.doc_id_to_index = mapping.get("doc_to_idx", {})
                    self.index_to_doc_id = {v: k for k, v in self.doc_id_to_index.items()}
                
                logger.info(f"Loaded index with {self.index.ntotal} vectors")
            except Exception as e:
                logger.error(f"Error loading index: {e}")
        else:
            # Create new index (384 dimensions for all-MiniLM-L6-v2)
            dimension = 384
            self.index = faiss.IndexFlatL2(dimension)
            logger.info(f"Created new index with dimension {dimension}")
    
    def _save_index(self):
        """Save index to disk"""
        if not self.index:
            return
        
        try:
            import json
            index_file = self.index_path / "faiss.index"
            mapping_file = self.index_path / "mapping.json"
            
            faiss.write_index(self.index, str(index_file))
            
            with open(mapping_file, 'w') as f:
                json.dump({
                    "doc_to_idx": self.doc_id_to_index,
                    "model": self.embedding_model_name
                }, f, indent=2)
            
            logger.info("Saved index to disk")
        except Exception as e:
            logger.error(f"Error saving index: {e}")
    
    async def index_document(self, doc_id: str, content: str, chunks: Optional[List[str]] = None) -> bool:
        """
        Index a document by creating embeddings.
        
        Args:
            doc_id: Document ID
            content: Full document content
            chunks: Optional pre-chunked content (if None, will chunk automatically)
        """
        if not self.embedder or not self.index:
            logger.warning("Indexing not available")
            return False
        
        try:
            # Chunk content if not provided
            if chunks is None:
                chunks = self._chunk_text(content)
            
            # Create embeddings for each chunk
            embeddings = self.embedder.encode(chunks, show_progress_bar=False)
            
            # Add to index
            start_idx = self.index.ntotal
            self.index.add(embeddings.astype('float32'))
            
            # Update mappings
            for i, chunk in enumerate(chunks):
                idx = start_idx + i
                chunk_id = f"{doc_id}_chunk_{i}"
                self.doc_id_to_index[chunk_id] = idx
                self.index_to_doc_id[idx] = chunk_id
            
            self._save_index()
            logger.info(f"Indexed document {doc_id} with {len(chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Error indexing document {doc_id}: {e}")
            return False
    
    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            chunks.append(chunk)
        
        return chunks
    
    async def search(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Tuple[str, float, DocumentMetadata]]:
        """
        Search for similar documents.
        
        Returns:
            List of (doc_id, similarity_score, metadata) tuples
        """
        if not self.embedder or not self.index:
            return []
        
        try:
            # Create query embedding
            query_embedding = self.embedder.encode([query], show_progress_bar=False)
            
            # Search index
            k = min(top_k, self.index.ntotal)
            if k == 0:
                return []
            
            distances, indices = self.index.search(query_embedding.astype('float32'), k)
            
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx == -1:  # Invalid index
                    continue
                
                chunk_id = self.index_to_doc_id.get(idx)
                if not chunk_id:
                    continue
                
                # Extract doc_id from chunk_id
                doc_id = chunk_id.split('_chunk_')[0]
                metadata = self.storage.get_metadata(doc_id)
                
                if metadata:
                    # Convert distance to similarity (lower distance = higher similarity)
                    similarity = 1.0 / (1.0 + dist)
                    results.append((doc_id, similarity, metadata))
            
            # Sort by similarity (descending)
            results.sort(key=lambda x: x[1], reverse=True)
            
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Error searching index: {e}")
            return []
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        return {
            "total_vectors": self.index.ntotal if self.index else 0,
            "total_documents": len(set(doc_id.split('_chunk_')[0] for doc_id in self.doc_id_to_index.keys())),
            "embedding_model": self.embedding_model_name,
            "dimension": self.index.d if self.index else 0
        }


