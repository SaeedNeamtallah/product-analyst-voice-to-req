"""
Database models using SQLAlchemy async ORM.
Defines tables for projects, assets, and chunks with vector embeddings.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, JSON, LargeBinary, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from datetime import datetime

Base = declarative_base()


class Project(Base):
    """Project model for organizing documents."""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Metadata (renamed to avoid conflict with SQLAlchemy metadata)
    extra_metadata = Column("metadata", JSON, default={})
    
    # Relationships
    assets = relationship("Asset", back_populates="project", cascade="all, delete-orphan")
    chunks = relationship("Chunk", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}')>"


class Asset(Base):
    """Asset model for uploaded documents."""
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # File information
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer, nullable=False)  # in bytes
    file_type = Column(String(50), nullable=False)  # pdf, txt, docx
    
    # Status
    status = Column(String(50), default="uploaded")  # uploaded, processing, completed, failed
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata (renamed to avoid conflict)
    extra_metadata = Column("metadata", JSON, default={})
    
    # Relationships
    project = relationship("Project", back_populates="assets")
    chunks = relationship("Chunk", back_populates="asset", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_assets_project_status', 'project_id', 'status'),
    )

    def __repr__(self):
        return f"<Asset(id={self.id}, filename='{self.filename}', status='{self.status}')>"


class Chunk(Base):
    """Chunk model for text chunks with vector embeddings."""
    __tablename__ = "chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    
    # Content
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Position in document
    
    # Vector embedding (stored as JSON/List for compatibility if pgvector is missing)
    # Vector search is handled by Qdrant if pgvector is not available
    embedding = Column(JSON, nullable=True)
    
    # Metadata (renamed to avoid conflict)
    extra_metadata = Column("metadata", JSON, default={})  # page_number, section, etc.
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="chunks")
    asset = relationship("Asset", back_populates="chunks")

    __table_args__ = (
        Index('ix_chunks_project_asset', 'project_id', 'asset_id'),
        Index('ix_chunks_asset_idx', 'asset_id', 'chunk_index'),
    )

    def __repr__(self):
        return f"<Chunk(id={self.id}, asset_id={self.asset_id}, chunk_index={self.chunk_index})>"
