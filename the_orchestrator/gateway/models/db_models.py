"""
SQLAlchemy models for the orchestrator database.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from the_orchestrator.gateway.database import Base


class Project(Base):
    """
    Project entity for storing project-specific configuration.
    """
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    keywords: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Comma-separated or space-separated keywords",
    )
    folder_path: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Project(name={self.name!r}, id={self.id!r})>"


class Conversation(Base):
    """
    Represents a conversation session.
    """
    __tablename__ = "conversation"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    source: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    number: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    chat_histories: Mapped[list["ChatHistory"]] = relationship("ChatHistory", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id!r}, source={self.source!r})>"


class ChatHistory(Base):
    """
    Represents a specific message within a conversation.
    """
    __tablename__ = "chat_history"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversation.id"),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    all_agent_responses: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id"),
        nullable=True,
    )
    is_from_agent: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="chat_histories")
    project: Mapped["Project"] = relationship("Project")
    file_changes: Mapped[list["FileChange"]] = relationship("FileChange", back_populates="chat_history", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ChatHistory(id={self.id!r}, is_from_agent={self.is_from_agent!r})>"


class FileChange(Base):
    """
    Represents a file modification tracked within a specific chat message.
    """
    __tablename__ = "file_changes"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    hash: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )
    chat_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_history.id"),
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    chat_history: Mapped["ChatHistory"] = relationship("ChatHistory", back_populates="file_changes")

    def __repr__(self) -> str:
        return f"<FileChange(id={self.id!r}, file_name={self.file_name!r})>"
