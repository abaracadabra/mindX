"""
RAGE Ingestion Engine

Handles ingestion of various file types and data sources for context retrieval.
"""

import asyncio
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import json

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger
from .storage import StorageEngine
from .indexing import IndexingEngine

logger = get_logger(__name__)


class IngestionEngine:
    """
    Ingestion engine for RAGE system.
    
    Handles ingestion of files, documents, and other data sources.
    """
    
    def __init__(
        self,
        storage_engine: Optional[StorageEngine] = None,
        indexing_engine: Optional[IndexingEngine] = None
    ):
        self.storage = storage_engine or StorageEngine()
        self.indexing = indexing_engine
        
        # Supported file types
        self.supported_types = {
            '.txt': self._ingest_text,
            '.md': self._ingest_text,
            '.json': self._ingest_json,
            '.py': self._ingest_text,
            '.js': self._ingest_text,
            '.ts': self._ingest_text,
            '.html': self._ingest_html,
            '.pdf': self._ingest_pdf,
            '.docx': self._ingest_docx,
        }
    
    async def ingest_file(
        self,
        file_path: Union[str, Path],
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        auto_index: bool = True
    ) -> Dict[str, Any]:
        """
        Ingest a file into the RAGE system.
        
        Returns:
            Dictionary with doc_id, status, and metadata
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}"
            }
        
        try:
            # Read file content
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Determine file type
            file_type = file_path.suffix.lower()
            if file_type not in self.supported_types:
                return {
                    "success": False,
                    "error": f"Unsupported file type: {file_type}"
                }
            
            # Extract text content
            extractor = self.supported_types[file_type]
            text_content = await extractor(content)
            
            if not text_content:
                return {
                    "success": False,
                    "error": "Could not extract text content"
                }
            
            # Store document
            doc_id = self.storage.store_document(
                source_path=str(file_path),
                content=content,
                file_type=file_type,
                tags=tags or [],
                metadata=metadata or {}
            )
            
            # Index document
            if auto_index and self.indexing:
                await self.indexing.index_document(doc_id, text_content)
            
            return {
                "success": True,
                "doc_id": doc_id,
                "file_path": str(file_path),
                "file_type": file_type,
                "content_length": len(text_content),
                "tags": tags or []
            }
            
        except Exception as e:
            logger.error(f"Error ingesting file {file_path}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def ingest_directory(
        self,
        directory_path: Union[str, Path],
        recursive: bool = True,
        file_patterns: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Ingest all supported files from a directory.
        """
        directory_path = Path(directory_path)
        
        if not directory_path.exists() or not directory_path.is_dir():
            return {
                "success": False,
                "error": f"Directory not found: {directory_path}"
            }
        
        results = {
            "success": True,
            "ingested": [],
            "failed": [],
            "total": 0
        }
        
        # Find files
        if recursive:
            files = list(directory_path.rglob('*'))
        else:
            files = list(directory_path.glob('*'))
        
        # Filter by supported types and patterns
        supported_files = [
            f for f in files
            if f.is_file() and f.suffix.lower() in self.supported_types
        ]
        
        if file_patterns:
            import fnmatch
            pattern_files = []
            for file in supported_files:
                for pattern in file_patterns:
                    if fnmatch.fnmatch(str(file), pattern):
                        pattern_files.append(file)
                        break
            supported_files = pattern_files
        
        results["total"] = len(supported_files)
        
        # Ingest each file
        for file_path in supported_files:
            result = await self.ingest_file(file_path, tags=tags)
            if result.get("success"):
                results["ingested"].append(result)
            else:
                results["failed"].append({
                    "file": str(file_path),
                    "error": result.get("error")
                })
        
        return results
    
    async def _ingest_text(self, content: bytes) -> str:
        """Extract text from text files"""
        try:
            return content.decode('utf-8')
        except UnicodeDecodeError:
            return content.decode('utf-8', errors='ignore')
    
    async def _ingest_json(self, content: bytes) -> str:
        """Extract text from JSON files"""
        try:
            data = json.loads(content.decode('utf-8'))
            return json.dumps(data, indent=2)
        except Exception as e:
            logger.error(f"Error parsing JSON: {e}")
            return content.decode('utf-8', errors='ignore')
    
    async def _ingest_html(self, content: bytes) -> str:
        """Extract text from HTML files"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            return soup.get_text()
        except ImportError:
            logger.warning("BeautifulSoup not available, using raw HTML")
            return content.decode('utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return content.decode('utf-8', errors='ignore')
    
    async def _ingest_pdf(self, content: bytes) -> str:
        """Extract text from PDF files"""
        try:
            import PyPDF2
            from io import BytesIO
            
            pdf_file = BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        except ImportError:
            logger.warning("PyPDF2 not available, cannot extract PDF text")
            return ""
        except Exception as e:
            logger.error(f"Error parsing PDF: {e}")
            return ""
    
    async def _ingest_docx(self, content: bytes) -> str:
        """Extract text from DOCX files"""
        try:
            from docx import Document
            from io import BytesIO
            
            doc_file = BytesIO(content)
            doc = Document(doc_file)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text
        except ImportError:
            logger.warning("python-docx not available, cannot extract DOCX text")
            return ""
        except Exception as e:
            logger.error(f"Error parsing DOCX: {e}")
            return ""


