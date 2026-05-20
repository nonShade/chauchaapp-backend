"""
Education module entities.

Tables:
    - educational_topic: Lookup table for educational topics.
    - educational_module: Educational content modules.
    - educational_module_topic: M2M pivot — a module can have multiple topics.
    - user_progress: Tracks user progress through educational modules.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_entity import AuditMixin
from app.shared.database import Base


class EducationalTopic(Base, AuditMixin):
    """Lookup table for educational module topics."""

    __tablename__ = "educational_topic"

    educational_topic_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    module_topics: Mapped[list["EducationalModuleTopic"]] = relationship(
        back_populates="topic"
    )


class EducationalModule(Base, AuditMixin):
    """Educational content module (lessons, courses)."""

    __tablename__ = "educational_module"

    educational_module_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(45), nullable=True)

    # Relationships
    module_topics: Mapped[list["EducationalModuleTopic"]] = relationship(
        back_populates="educational_module"
    )
    user_progress: Mapped[list["UserProgress"]] = relationship(
        back_populates="educational_module"
    )
    quizzes: Mapped[list["Quiz"]] = relationship(
        back_populates="educational_module"
    )


class EducationalModuleTopic(Base, AuditMixin):
    """
    M2M pivot table: an educational module can have multiple topics.

    Composite primary key (educational_module_id, educational_topic_id).
    """

    __tablename__ = "educational_module_topic"

    educational_module_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("educational_module.educational_module_id"),
        primary_key=True,
    )
    educational_topic_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("educational_topic.educational_topic_id"),
        primary_key=True,
    )

    # Relationships
    educational_module: Mapped["EducationalModule"] = relationship(
        back_populates="module_topics"
    )
    topic: Mapped["EducationalTopic"] = relationship(
        back_populates="module_topics"
    )


class UserProgress(Base, AuditMixin):
    """Tracks a user's progress through an educational module."""

    __tablename__ = "user_progress"
    __table_args__ = (UniqueConstraint("user_id", "educational_module_id"),)

    progress_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.user_id"),
        nullable=False,
    )
    educational_module_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("educational_module.educational_module_id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(45), nullable=False, default="not_started"
    )
    progress_percentage: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    completed_sections: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    quiz_attempts: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="user_progress")
    educational_module: Mapped["EducationalModule"] = relationship(
        back_populates="user_progress"
    )
