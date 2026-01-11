"""
RAGE: Retrieval Augmented Generative Engine

A comprehensive system for ingesting, indexing, and retrieving data for context-aware generation.
Supports file ingestion, document processing, and intelligent retrieval for LLM context.
"""

from .ingestion import IngestionEngine
from .retrieval import RetrievalEngine
from .indexing import IndexingEngine
from .storage import StorageEngine

__all__ = [
    "IngestionEngine",
    "RetrievalEngine",
    "IndexingEngine",
    "StorageEngine",
]


