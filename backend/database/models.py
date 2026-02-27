"""
Database models using SQLAlchemy async ORM.
Defines tables for projects, assets, chat messages, and SRS drafts.
"""
from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, ForeignKey, JSON, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="admin")  # user, admin
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"


class Project(Base):
    """Project model for organizing documents."""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Metadata (renamed to avoid conflict with SQLAlchemy metadata)
    extra_metadata = Column("metadata", JSON, default={})

    # Relationships
    owner = relationship("User", backref="projects")
    
    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}')>"





class ChatMessage(Base):
    """Chat message model for project conversations."""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    extra_metadata = Column("metadata", JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project")

    __table_args__ = (
        Index('ix_chat_messages_project_created', 'project_id', 'created_at'),
    )

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, project_id={self.project_id}, role='{self.role}')>"


class SRSDraft(Base):
    """SRS draft model for project requirements summaries."""
    __tablename__ = "srs_drafts"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    status = Column(String(50), default="draft")
    language = Column(String(10), default="ar")
    content = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project")

    __table_args__ = (
        Index('ix_srs_drafts_project_version', 'project_id', 'version'),
    )

    def __repr__(self):
        return f"<SRSDraft(id={self.id}, project_id={self.project_id}, version={self.version}, status='{self.status}')>"


class TelegramSession(Base):
    """Telegram session model for linking chat_id to project_id."""
    __tablename__ = "telegram_sessions"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(BigInteger, nullable=False, unique=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project")

    def __repr__(self):
        return f"<TelegramSession(chat_id={self.chat_id}, project_id={self.project_id})>"
