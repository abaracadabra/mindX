"""
RAGE Storage Engine

Handles persistent storage of ingested documents, embeddings, and metadata.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class DocumentMetadata:
    """Metadata for an ingested document"""
    doc_id: str
    source_path: str
    file_type: str
    file_size: int
    content_hash: str
    ingested_at: str
    last_accessed: Optional[str] = None
    access_count: int = 0
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}


class StorageEngine:
    """
    Storage engine for RAGE system.
    
    Manages document storage, metadata, and retrieval indexes.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or (PROJECT_ROOT / "data" / "rage" / "storage")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.documents_path = self.storage_path / "documents"
        self.documents_path.mkdir(exist_ok=True)
        
        self.metadata_path = self.storage_path / "metadata.json"
        self.metadata: Dict[str, DocumentMetadata] = {}
        
        self._load_metadata()
    
    def _load_metadata(self):
        """Load metadata from disk"""
        if self.metadata_path.exists():
            try:
                with open(self.metadata_path, 'r') as f:
                    data = json.load(f)
                    for doc_id, meta_dict in data.items():
                        self.metadata[doc_id] = DocumentMetadata(**meta_dict)
                logger.info(f"Loaded {len(self.metadata)} document metadata entries")
            except Exception as e:
                logger.error(f"Error loading metadata: {e}")
    
    def _save_metadata(self):
        """Save metadata to disk"""
        try:
            data = {}
            for doc_id, metadata in self.metadata.items():
                data[doc_id] = asdict(metadata)
            
            with open(self.metadata_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
    
    def _generate_doc_id(self, source_path: str, content: bytes) -> str:
        """Generate unique document ID"""
        content_hash = hashlib.sha256(content).hexdigest()[:16]
        path_hash = hashlib.md5(source_path.encode()).hexdigest()[:8]
        return f"{path_hash}_{content_hash}"
    
    def store_document(
        self,
        source_path: str,
        content: bytes,
        file_type: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a document and return its document ID.
        """
        doc_id = self._generate_doc_id(source_path, content)
        
        # Check if already stored
        if doc_id in self.metadata:
            logger.info(f"Document {doc_id} already exists, updating metadata")
            existing = self.metadata[doc_id]
            existing.last_accessed = datetime.now().isoformat()
            existing.access_count += 1
            if tags:
                existing.tags.extend(tags)
                existing.tags = list(set(existing.tags))  # Remove duplicates
            if metadata:
                existing.metadata.update(metadata)
            self._save_metadata()
            return doc_id
        
        # Store document
        doc_file = self.documents_path / f"{doc_id}.bin"
        with open(doc_file, 'wb') as f:
            f.write(content)
        
        # Create metadata
        doc_metadata = DocumentMetadata(
            doc_id=doc_id,
            source_path=source_path,
            file_type=file_type,
            file_size=len(content),
            content_hash=hashlib.sha256(content).hexdigest(),
            ingested_at=datetime.now().isoformat(),
            tags=tags or [],
            metadata=metadata or {}
        )
        
        self.metadata[doc_id] = doc_metadata
        self._save_metadata()
        
        logger.info(f"Stored document {doc_id} from {source_path}")
        return doc_id
    
    def get_document(self, doc_id: str) -> Optional[bytes]:
        """Retrieve document content by ID"""
        if doc_id not in self.metadata:
            return None
        
        doc_file = self.documents_path / f"{doc_id}.bin"
        if not doc_file.exists():
            return None
        
        # Update access metadata
        metadata = self.metadata[doc_id]
        metadata.last_accessed = datetime.now().isoformat()
        metadata.access_count += 1
        self._save_metadata()
        
        with open(doc_file, 'rb') as f:
            return f.read()
    
    def get_metadata(self, doc_id: str) -> Optional[DocumentMetadata]:
        """Get document metadata"""
        return self.metadata.get(doc_id)
    
    def list_documents(self, tags: Optional[List[str]] = None) -> List[DocumentMetadata]:
        """List all documents, optionally filtered by tags"""
        documents = list(self.metadata.values())
        
        if tags:
            documents = [
                doc for doc in documents
                if any(tag in doc.tags for tag in tags)
            ]
        
        return documents
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document"""
        if doc_id not in self.metadata:
            return False
        
        # Delete file
        doc_file = self.documents_path / f"{doc_id}.bin"
        if doc_file.exists():
            doc_file.unlink()
        
        # Remove metadata
        del self.metadata[doc_id]
        self._save_metadata()
        
        logger.info(f"Deleted document {doc_id}")
        return True


