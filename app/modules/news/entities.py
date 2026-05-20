"""
News module entities.

Tables:
    - news: News articles with financial/economic content.
    - news_tag: Tags for categorizing news.
    - news_tag_map: M2M pivot between news and tags (composite PK).
    - personalized_analysis_news: AI-generated analysis of news for a user.
    - user_interest: User's interest in specific news tags.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_entity import AuditMixin
from app.shared.database import Base

if TYPE_CHECKING:
    from app.modules.users.entities import User


class News(Base, AuditMixin):
    """News article with financial/economic content."""

    __tablename__ = "news"

    news_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    impact_level: Mapped[str | None] = mapped_column(String(45), nullable=True)
    affects: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_audience: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    # Relationships
    tag_maps: Mapped[list["NewsTagMap"]] = relationship(back_populates="news")
    personalized_analyses: Mapped[list["PersonalizedAnalysisNews"]] = relationship(
        back_populates="news"
    )


class NewsTag(Base, AuditMixin):
    """Tag for categorizing news articles."""

    __tablename__ = "news_tag"

    tag_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    tag_maps: Mapped[list["NewsTagMap"]] = relationship(back_populates="tag")
    user_interests: Mapped[list["UserInterest"]] = relationship(
        back_populates="tag"
    )


class NewsTagMap(Base, AuditMixin):
    """M2M pivot table between news and tags (composite primary key)."""

    __tablename__ = "news_tag_map"

    news_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("news.news_id"),
        primary_key=True,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("news_tag.tag_id"),
        primary_key=True,
    )

    # Relationships
    news: Mapped["News"] = relationship(back_populates="tag_maps")
    tag: Mapped["NewsTag"] = relationship(back_populates="tag_maps")


class PersonalizedAnalysisNews(Base, AuditMixin):
    """AI-generated personalized analysis of a news article for a user."""

    __tablename__ = "personalized_analysis_news"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    news_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("news.news_id"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.user_id"),
        nullable=False,
    )
    analysis_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    # Relationships
    news: Mapped["News"] = relationship(back_populates="personalized_analyses")
    user: Mapped["User"] = relationship(back_populates="personalized_analyses")


class UserInterest(Base, AuditMixin):
    """Record of a user's interest in a specific news tag."""

    __tablename__ = "user_interest"

    interest_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.user_id"),
        nullable=False,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("news_tag.tag_id"),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="user_interests")
    tag: Mapped["NewsTag"] = relationship(back_populates="user_interests")
