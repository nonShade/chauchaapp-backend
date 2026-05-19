"""
Transactions module entities.

Tables:
    - transaction_type: Lookup table (income, expense).
    - transaction_frequency: Lookup table (one_time, monthly, weekly).
    - transaction_category: Lookup table for transaction categories.
    - transaction: Financial transaction records.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_entity import AuditMixin
from app.shared.database import Base


class TransactionType(Base, AuditMixin):
    """Lookup table for transaction types (income, expense)."""

    __tablename__ = "transaction_type"

    transaction_type_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    categories: Mapped[list["TransactionCategory"]] = relationship(
        back_populates="transaction_type"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="transaction_type"
    )


class TransactionFrequency(Base, AuditMixin):
    """Lookup table for transaction frequency (one_time, monthly, weekly)."""

    __tablename__ = "transaction_frequency"

    transaction_frequency_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="transaction_frequency"
    )


class TransactionCategory(Base, AuditMixin):
    """
    Lookup table for transaction categories.

    Categories are linked to a transaction type to differentiate between
    income categories (sueldo, freelance, etc.) and expense categories
    (alimentacion, transporte, etc.).
    """

    __tablename__ = "transaction_category"

    transaction_category_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transaction_type_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("transaction_type.transaction_type_id"),
        nullable=True,
    )

    # Relationships
    transaction_type: Mapped["TransactionType | None"] = relationship(
        back_populates="categories"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="category"
    )


class Transaction(Base, AuditMixin):
    """Financial transaction record (income or expense)."""

    __tablename__ = "transaction"

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.user_id"),
        nullable=False,
    )
    family_group_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("family_group.family_group_id"),
        nullable=True,
    )
    transaction_type_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("transaction_type.transaction_type_id"),
        nullable=False,
    )
    transaction_category_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("transaction_category.transaction_category_id"),
        nullable=True,
    )
    transaction_frequency_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("transaction_frequency.transaction_frequency_id"),
        nullable=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transaction_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="transactions")
    family_group: Mapped["FamilyGroup | None"] = relationship(
        back_populates="transactions"
    )
    transaction_type: Mapped["TransactionType"] = relationship(
        back_populates="transactions"
    )
    category: Mapped["TransactionCategory | None"] = relationship(
        back_populates="transactions"
    )
    transaction_frequency: Mapped["TransactionFrequency | None"] = relationship(
        back_populates="transactions"
    )
