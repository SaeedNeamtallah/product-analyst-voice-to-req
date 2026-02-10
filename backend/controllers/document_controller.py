"""
Document Controller.
Business logic for document upload and processing.
"""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from backend.database.models import Asset, Chunk, Project
from backend.services.file_service import FileService
from backend.runtime_config import get_runtime_value
from backend.config import settings
from backend.providers.vectordb.factory import VectorDBProviderFactory
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DocumentController:
    """Controller for document operations."""
    
    def __init__(self):
        """Initialize document controller."""
        self.file_service = FileService()
        # Lazy imports keep startup fast and avoid circular-import pitfalls.
        from backend.services.document_loader import DocumentLoaderService
        from backend.services.chunking_service import ChunkingService
        from backend.services.embedding_service import EmbeddingService

        self.document_loader = DocumentLoaderService()
        self.chunking_service = ChunkingService()
        self.embedding_service = EmbeddingService()
        self.vector_db = VectorDBProviderFactory.create_provider()
    
    async def upload_document(
        self,
        db: AsyncSession,
        project_id: int,
        file_content: bytes,
        filename: str,
        file_size: int
    ) -> Asset:
        """
        Upload document and save metadata.
        
        Args:
            db: Database session
            project_id: Project ID
            file_content: File content bytes
            filename: Original filename
            file_size: File size in bytes
            
        Returns:
            Created asset
            
        Raises:
            ValueError: If validation fails
        """
        try:
            # Validate file
            is_valid, error_msg = self.file_service.validate_file(filename, file_size)
            if not is_valid:
                raise ValueError(error_msg)
            
            # Check project exists
            project_stmt = select(Project).where(Project.id == project_id)
            project_result = await db.execute(project_stmt)
            project = project_result.scalar_one_or_none()
            if not project:
                raise ValueError(f"Project not found: {project_id}")
            
            # Save file
            unique_filename, file_path = await self.file_service.save_upload_file(
                file_content=file_content,
                filename=filename,
                project_id=project_id
            )
            
            # Get file type
            from pathlib import Path
            file_type = Path(filename).suffix.lstrip('.')
            
            # Create asset record
            asset = Asset(
                project_id=project_id,
                filename=unique_filename,
                original_filename=filename,
                file_path=file_path,
                file_size=file_size,
                file_type=file_type,
                status="uploaded"
            )
            
            db.add(asset)
            await db.commit()
            await db.refresh(asset)
            
            logger.info(f"Uploaded document: {asset.id} - {filename}")
            return asset
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error uploading document: {str(e)}")
            raise
    
    async def process_document(self, asset_id: int, **_kw) -> bool:
        """Process document with a dedicated DB session (background-task safe)."""
        from backend.database.connection import async_session_maker
        async with async_session_maker() as db:
            return await self._process_document_impl(db, asset_id)

    async def _process_document_impl(
        self,
        db: AsyncSession,
        asset_id: int
    ) -> bool:
        """Extract, chunk, embed, and store document vectors."""
        try:
            # Get asset
            asset_stmt = select(Asset).where(Asset.id == asset_id)
            asset_result = await db.execute(asset_stmt)
            asset = asset_result.scalar_one_or_none()
            
            if not asset:
                raise ValueError(f"Asset not found: {asset_id}")
            
            # Update status to processing
            asset.status = "processing"
            await db.commit()
            
            try:
                # Extract text
                logger.info(f"Extracting text from {asset.original_filename}")
                text = await self.document_loader.load_document(asset.file_path)
                
                # Chunk text
                logger.info(f"Chunking text ({len(text)} characters)")
                await self._update_asset_progress(
                    db,
                    asset,
                    stage="chunking",
                    processed=0,
                    total=0,
                    progress=0
                )
                chunk_strategy = get_runtime_value("chunk_strategy", settings.chunk_strategy)
                chunk_size = get_runtime_value("chunk_size", settings.chunk_size)
                chunk_overlap = get_runtime_value("chunk_overlap", settings.chunk_overlap)
                parent_chunk_size = get_runtime_value("parent_chunk_size", settings.parent_chunk_size)
                parent_chunk_overlap = get_runtime_value("parent_chunk_overlap", settings.parent_chunk_overlap)

                chunking_service = self.chunking_service
                if any(value is not None for value in [chunk_size, chunk_overlap, parent_chunk_size, parent_chunk_overlap]):
                    from backend.services.chunking_service import ChunkingService
                    chunking_service = ChunkingService(
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        parent_chunk_size=parent_chunk_size,
                        parent_chunk_overlap=parent_chunk_overlap
                    )

                chunks_data = await chunking_service.chunk_document(
                    text=text,
                    document_name=asset.original_filename,
                    additional_metadata={
                        'file_type': asset.file_type,
                        'asset_id': asset.id
                    },
                    chunk_strategy=chunk_strategy
                )
                
                # Create chunk records
                chunk_records = []
                for i, chunk_data in enumerate(chunks_data):
                    chunk_records.append(
                        Chunk(
                            project_id=asset.project_id,
                            asset_id=asset.id,
                            content=chunk_data['content'],
                            chunk_index=i,
                            extra_metadata=chunk_data['metadata']
                        )
                    )

                db.add_all(chunk_records)
                await db.flush()

                total_chunks = len(chunk_records)
                await self._update_asset_progress(
                    db,
                    asset,
                    stage="embedding",
                    processed=0,
                    total=total_chunks,
                    progress=0
                )
                
                # Generate embeddings
                logger.info(f"Generating embeddings for {len(chunk_records)} chunks")
                texts = [chunk.content for chunk in chunk_records]

                async def on_embed_batch(processed: int, total: int) -> None:
                    progress = int((processed / max(total, 1)) * 100)
                    await self._update_asset_progress(
                        db,
                        asset,
                        stage="embedding",
                        processed=processed,
                        total=total,
                        progress=progress
                    )

                embeddings = await self.embedding_service.generate_embeddings(
                    texts,
                    on_batch=on_embed_batch
                )
                
                # Store embeddings in chunks and vector DB
                chunk_ids = [chunk.id for chunk in chunk_records]
                vector_metadata = [
                    {
                        'asset_id': chunk.asset_id,
                        'project_id': chunk.project_id,
                        'chunk_index': chunk.chunk_index
                    }
                    for chunk in chunk_records
                ]
                await self._update_asset_progress(
                    db,
                    asset,
                    stage="indexing",
                    processed=total_chunks,
                    total=total_chunks,
                    progress=95
                )

                vector_db = VectorDBProviderFactory.create_provider()
                await vector_db.add_vectors(
                    collection_name=f"project_{asset.project_id}",
                    vectors=embeddings,
                    ids=chunk_ids,
                    metadata=vector_metadata
                )
                
                # Update asset status
                asset.status = "completed"
                asset.processed_at = datetime.utcnow()
                await self._update_asset_progress(
                    db,
                    asset,
                    stage="completed",
                    processed=total_chunks,
                    total=total_chunks,
                    progress=100
                )
                await db.commit()
                
                logger.info(f"Completed processing document: {asset.id}")
                return True
                
            except Exception as e:
                # Mark as failed
                asset.status = "failed"
                asset.error_message = str(e)
                await db.commit()
                raise
                
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            raise

    async def _update_asset_progress(
        self,
        db: AsyncSession,
        asset: Asset,
        stage: str,
        processed: int,
        total: int,
        progress: int
    ) -> None:
        meta = dict(asset.extra_metadata or {})
        meta.update({
            "stage": stage,
            "processed_chunks": int(processed),
            "total_chunks": int(total),
            "progress": int(progress)
        })
        asset.extra_metadata = meta
        flag_modified(asset, "extra_metadata")
        await db.commit()
    
    async def get_document(
        self,
        db: AsyncSession,
        asset_id: int
    ) -> Optional[Asset]:
        """
        Get document by ID.
        
        Args:
            db: Database session
            asset_id: Asset ID
            
        Returns:
            Asset or None
        """
        try:
            stmt = select(Asset).where(Asset.id == asset_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting document: {str(e)}")
            raise
    
    async def list_project_documents(
        self,
        db: AsyncSession,
        project_id: int
    ) -> List[Asset]:
        """
        List all documents in project.
        
        Args:
            db: Database session
            project_id: Project ID
            
        Returns:
            List of assets
        """
        try:
            stmt = select(Asset).where(Asset.project_id == project_id).order_by(Asset.created_at.desc())
            result = await db.execute(stmt)
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Error listing documents: {str(e)}")
            raise
    
    async def delete_document(
        self,
        db: AsyncSession,
        asset_id: int
    ) -> bool:
        """
        Delete document and associated chunks.
        
        Args:
            db: Database session
            asset_id: Asset ID
            
        Returns:
            True if deleted
        """
        try:
            # Get asset
            asset = await self.get_document(db, asset_id)
            if not asset:
                return False
            
            # Delete file
            await self.file_service.delete_file(asset.file_path)
            
            # Delete from database (cascade will delete chunks)
            await db.delete(asset)
            await db.commit()
            
            logger.info(f"Deleted document: {asset_id}")
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting document: {str(e)}")
            raise
