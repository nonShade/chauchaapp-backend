"""
Transactions module DTOs.

Handles data transfer formatting for endpoints in the Transactions module.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

SANTIAGO_TZ = ZoneInfo("America/Santiago")


def parse_local_date(value: Any) -> datetime | None:
    """Normalize incoming dates to timezone-aware datetimes in Santiago."""
    if value is None:
        return None

    if isinstance(value, str):
        value = datetime.fromisoformat(value)

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=SANTIAGO_TZ)
        return value.astimezone(SANTIAGO_TZ)

    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), tzinfo=SANTIAGO_TZ)

    raise TypeError("transaction_date must be a date, datetime, or ISO string")


class IncomeTypeResponseDTO(BaseModel):
    """Details of an income type available for selection."""

    id: UUID
    name: str

    model_config = {"from_attributes": True}


class TransactionTypeResponseDTO(BaseModel):
    """Details of a transaction type (e.g. income, expense)."""

    id: UUID
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}


class TransactionFrequencyResponseDTO(BaseModel):
    """Details of a transaction frequency (e.g. one_time, monthly)."""

    id: UUID
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}


class TransactionCategoryResponseDTO(BaseModel):
    """Details of a transaction category."""

    id: UUID
    name: str
    description: str | None = None
    transaction_type_id: UUID | None = None

    model_config = {"from_attributes": True}


class TransactionCreateDTO(BaseModel):
    """Schema for creating a new transaction."""

    amount: Decimal = Field(gt=0)
    transaction_type_id: UUID
    transaction_category_id: UUID | None = None
    transaction_frequency_id: UUID | None = None
    description: str | None = None
    transaction_date: datetime

    @field_validator("transaction_date", mode="before")
    @classmethod
    def _parse_local_date(cls, value: Any) -> datetime:
        normalized = parse_local_date(value)
        if normalized is None:
            raise ValueError("transaction_date is required")
        return normalized


class TransactionUpdateDTO(BaseModel):
    """Schema for updating an existing transaction."""

    amount: Decimal | None = Field(None, gt=0)
    transaction_type_id: UUID | None = None
    transaction_category_id: UUID | None = None
    transaction_frequency_id: UUID | None = None
    description: str | None = None
    transaction_date: datetime | None = None

    @field_validator("transaction_date", mode="before")
    @classmethod
    def _parse_local_date(cls, value: Any) -> datetime | None:
        return parse_local_date(value)


class TransactionResponseDTO(BaseModel):
    """Schema for transaction record response."""

    transaction_id: UUID
    amount: Decimal
    description: str | None = None
    transaction_date: date
    transaction_type_id: UUID
    transaction_category_id: UUID | None = None
    transaction_frequency_id: UUID | None = None

    model_config = {"from_attributes": True}


class PaginationMetaDTO(BaseModel):
    """Schema for pagination metadata."""

    currentPage: int
    totalPages: int
    totalItems: int
    itemsPerPage: int


class TransactionPaginationResponseDTO(BaseModel):
    """Schema for paginated transaction list response."""

    meta: PaginationMetaDTO
    data: list[TransactionResponseDTO]


class GroupTransactionResponseDTO(TransactionResponseDTO):
    """Schema for group transaction record response. Includes user name."""

    user_name: str


class GroupTransactionPaginationResponseDTO(BaseModel):
    """Schema for paginated group transaction list response."""

    meta: PaginationMetaDTO
    data: list[GroupTransactionResponseDTO]


class FinancialSummaryDTO(BaseModel):
    """Schema for general financial summary (income, expenses, balance)."""

    total_balance: Decimal
    total_income: Decimal
    total_expenses: Decimal


class CategoryDistributionDTO(BaseModel):
    """Schema for expense distribution by category."""

    category_id: UUID | None
    category_name: str
    total_amount: Decimal
    percentage: float


class IncomeVsExpensesChartDTO(BaseModel):
    """Schema for the monthly income vs expenses chart.

    Returns parallel arrays ready for chart rendering:
    - labels: abbreviated Spanish month names (e.g. "Ene", "Feb", ...)
    - income: total income per month
    - expense: total expenses per month
    """

    labels: list[str]
    income: list[Decimal]
    expense: list[Decimal]
