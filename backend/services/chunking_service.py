"""
Text Chunking Service.
Handles splitting text into chunks using LangChain.
"""
from typing import List, Dict, Any
from backend.config import settings
import logging

logger = logging.getLogger(__name__)


class ChunkingService:
    """Service for chunking text documents."""
    
    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        parent_chunk_size: int = None,
        parent_chunk_overlap: int = None
    ):
        """
        Initialize chunking service.
        
        Args:
            chunk_size: Size of each child chunk (defaults to settings)
            chunk_overlap: Overlap between child chunks (defaults to settings)
            parent_chunk_size: Size of each parent chunk (defaults to settings)
            parent_chunk_overlap: Overlap between parent chunks (defaults to settings)
        """
        self.child_chunk_size = chunk_size or settings.chunk_size
        self.child_chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.parent_chunk_size = parent_chunk_size or settings.parent_chunk_size
        self.parent_chunk_overlap = parent_chunk_overlap or settings.parent_chunk_overlap

        if self.parent_chunk_size <= self.child_chunk_size:
            self.parent_chunk_size = self.child_chunk_size * 3
            self.parent_chunk_overlap = self.child_chunk_overlap * 3
            logger.warning(
                "Parent chunk size too small; auto-adjusted to "
                f"size={self.parent_chunk_size}, overlap={self.parent_chunk_overlap}"
            )
        
        # Lazy import to avoid heavy startup costs
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        # Initialize text splitters
        self.child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.child_chunk_size,
            chunk_overlap=self.child_chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        self.parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.parent_chunk_size,
            chunk_overlap=self.parent_chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        logger.info(
            "Chunking service initialized "
            f"(child_size={self.child_chunk_size}, child_overlap={self.child_chunk_overlap}, "
            f"parent_size={self.parent_chunk_size}, parent_overlap={self.parent_chunk_overlap})"
        )
    
    async def chunk_text(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Split text into chunks with metadata (simple strategy).
        
        Args:
            text: Text to chunk
            metadata: Optional base metadata for all chunks
            
        Returns:
            List of chunk dictionaries with 'content' and 'metadata'
        """
        try:
            # Split text
            text_chunks = self.child_splitter.split_text(text)
            
            # Create chunk objects with metadata
            chunks = []
            base_metadata = metadata or {}
            
            for i, chunk_text in enumerate(text_chunks):
                chunk_metadata = {
                    **base_metadata,
                    'chunk_strategy': 'simple',
                    'chunk_level': 'child',
                    'chunk_index': i,
                    'total_chunks': len(text_chunks),
                    'chunk_size': len(chunk_text),
                    'child_chunk_size': self.child_chunk_size,
                    'child_chunk_overlap': self.child_chunk_overlap
                }
                
                chunks.append({
                    'content': chunk_text,
                    'metadata': chunk_metadata
                })
            
            logger.info(f"Created {len(chunks)} chunks from text ({len(text)} characters)")
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking text: {str(e)}")
            raise
    
    async def chunk_document(
        self,
        text: str,
        document_name: str,
        additional_metadata: Dict[str, Any] = None,
        chunk_strategy: str = None
    ) -> List[Dict[str, Any]]:
        """
        Chunk document with automatic metadata.
        
        Args:
            text: Document text
            document_name: Name of document
            additional_metadata: Optional additional metadata
            
        Returns:
            List of chunks with metadata
        """
        metadata = {
            'document_name': document_name,
            **(additional_metadata or {})
        }

        strategy = (chunk_strategy or settings.chunk_strategy or "parent_child").lower()
        if strategy == "simple":
            return await self.chunk_text(text, metadata)

        return await self._chunk_parent_child(text, metadata)

    async def _chunk_parent_child(
        self,
        text: str,
        base_metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Chunk text using parent-child (small-to-big) strategy.

        Args:
            text: Full document text
            base_metadata: Base metadata applied to all chunks

        Returns:
            List of child chunks with parent references
        """
        try:
            parent_chunks = self.parent_splitter.split_text(text)
            chunks: List[Dict[str, Any]] = []
            global_index = 0

            for parent_index, parent_text in enumerate(parent_chunks):
                child_chunks = self.child_splitter.split_text(parent_text)
                for child_index, child_text in enumerate(child_chunks):
                    chunk_metadata = {
                        **base_metadata,
                        'chunk_strategy': 'parent_child_small_to_big',
                        'chunk_level': 'child',
                        'chunk_index': global_index,
                        'chunk_size': len(child_text),
                        'parent_index': parent_index,
                        'parent_total': len(parent_chunks),
                        'parent_chunk_size': self.parent_chunk_size,
                        'parent_chunk_overlap': self.parent_chunk_overlap,
                        'parent_content': parent_text,
                        'parent_content_size': len(parent_text),
                        'child_index': child_index,
                        'child_total': len(child_chunks),
                        'child_chunk_size': self.child_chunk_size,
                        'child_chunk_overlap': self.child_chunk_overlap
                    }

                    chunks.append({
                        'content': child_text,
                        'metadata': chunk_metadata
                    })
                    global_index += 1

            total_chunks = len(chunks)
            for chunk in chunks:
                chunk['metadata']['total_chunks'] = total_chunks

            logger.info(
                f"Created {len(chunks)} child chunks from {len(parent_chunks)} parents "
                f"({len(text)} characters)"
            )
            return chunks

        except Exception as e:
            logger.error(f"Error chunking text with parent-child strategy: {str(e)}")
            raise
