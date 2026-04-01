"""
SQLAlchemy models for the orchestrator database.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

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
