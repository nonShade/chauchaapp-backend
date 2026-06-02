"""
Transactions repository — data access layer.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.users.entities import IncomeType
from app.modules.transactions.entities import (
    TransactionCategory,
    TransactionFrequency,
    Transaction,
    TransactionType,
)


class TransactionsRepository:
    """Data access for transaction-related entries (including income types)."""

    def __init__(self, session: Session):
        self._session = session

    def get_all_income_types(self) -> list[IncomeType]:
        """Get all available income types.

        Returns:
            A list of IncomeType entities.
        """
        return self._session.query(IncomeType).all()

    def get_all_transaction_types(self) -> list[TransactionType]:
        """Get all available transaction types."""
        return self._session.query(TransactionType).all()

    def get_all_transaction_frequencies(self) -> list[TransactionFrequency]:
        """Get all available transaction frequencies."""
        return self._session.query(TransactionFrequency).all()

    def get_all_transaction_categories(self) -> list[TransactionCategory]:
        """Get all available transaction categories."""
        return self._session.query(TransactionCategory).all()

    def get_transaction_type_by_name(self, name: str) -> TransactionType | None:
        """Find a transaction type by its name."""
        return (
            self._session.query(TransactionType)
            .filter(TransactionType.name == name)
            .first()
        )

    def get_transaction_type_by_id(
        self, transaction_type_id: UUID
    ) -> TransactionType | None:
        """Find a transaction type by its ID."""
        return (
            self._session.query(TransactionType)
            .filter(TransactionType.transaction_type_id == transaction_type_id)
            .first()
        )

    def get_transaction_category_by_name(self, name: str) -> TransactionCategory | None:
        """Find a transaction category by its name."""
        return (
            self._session.query(TransactionCategory)
            .filter(TransactionCategory.name == name)
            .first()
        )

    def get_transaction_frequency_by_name(self, name: str) -> TransactionFrequency | None:
        """Find a transaction frequency by its name."""
        return (
            self._session.query(TransactionFrequency)
            .filter(TransactionFrequency.name == name)
            .first()
        )

    def get_transaction_frequency_by_id(
        self, transaction_frequency_id: UUID
    ) -> TransactionFrequency | None:
        """Find a transaction frequency by its ID."""
        return (
            self._session.query(TransactionFrequency)
            .filter(
                TransactionFrequency.transaction_frequency_id
                == transaction_frequency_id
            )
            .first()
        )

    def get_transaction_by_user_type_category(
        self, user_id: UUID, transaction_type_id: UUID, transaction_category_id: UUID
    ) -> Transaction | None:
        """Find a transaction for a user by type and category."""
        return (
            self._session.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type_id == transaction_type_id,
                Transaction.transaction_category_id == transaction_category_id,
            )
            .first()
        )

    def add_transaction(self, transaction: Transaction) -> Transaction:
        """Add a transaction using flush instead of commit (for use within larger transactions)."""
        self._session.add(transaction)
        self._session.flush()
        return transaction

    def create_transaction(self, transaction: Transaction) -> Transaction:
        """Create a new financial transaction."""
        self._session.add(transaction)
        self._session.commit()
        self._session.refresh(transaction)
        return transaction

    def update_transaction(self, transaction_id: UUID, **kwargs) -> Transaction | None:
        """Update an existing transaction."""
        transaction = self.get_transaction_by_id(transaction_id)
        if not transaction:
            return None

        for key, value in kwargs.items():
            if value is not None:
                setattr(transaction, key, value)

        self._session.commit()
        self._session.refresh(transaction)
        return transaction

    def delete_transaction(self, transaction_id: UUID) -> bool:
        """Delete a transaction."""
        transaction = self.get_transaction_by_id(transaction_id)
        if not transaction:
            return False

        self._session.delete(transaction)
        self._session.commit()
        return True

    def get_transaction_by_id(self, transaction_id: UUID) -> Transaction | None:
        """Retrieve a transaction by its ID."""
        return (
            self._session.query(Transaction)
            .filter(Transaction.transaction_id == transaction_id)
            .first()
        )

    def get_transactions_by_user(
        self,
        user_id: UUID,
        page: int = 1,
        limit: int = 10,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[list[Transaction], int]:
        """Get paginated transactions for a user with optional date filtering."""
        query = self._session.query(Transaction).filter(Transaction.user_id == user_id)

        if start_date:
            query = query.filter(Transaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(Transaction.transaction_date <= end_date)

        total_count = query.count()

        offset = (page - 1) * limit
        transactions = (
            query.order_by(Transaction.transaction_date.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return transactions, total_count

    def get_totals_by_type(
        self, user_id: UUID, start_date: date, end_date: date
    ) -> list[tuple[str, Decimal]]:
        """Get total amounts grouped by transaction type (ingreso/gasto)."""
        return (
            self._session.query(TransactionType.name, func.sum(Transaction.amount))
            .join(TransactionType, Transaction.transaction_type_id == TransactionType.transaction_type_id)
            .filter(Transaction.user_id == user_id)
            .filter(Transaction.transaction_date >= start_date)
            .filter(Transaction.transaction_date <= end_date)
            .group_by(TransactionType.name)
            .all()
        )

    def get_distribution_by_category(
        self, user_id: UUID, start_date: date, end_date: date
    ) -> list[tuple[UUID | None, str, Decimal]]:
        """Get total amounts grouped by category for expenses."""
        return (
            self._session.query(
                TransactionCategory.transaction_category_id,
                TransactionCategory.name,
                func.sum(Transaction.amount),
            )
            .join(
                TransactionCategory,
                Transaction.transaction_category_id == TransactionCategory.transaction_category_id,
            )
            .join(
                TransactionType,
                Transaction.transaction_type_id == TransactionType.transaction_type_id,
            )
            .filter(Transaction.user_id == user_id)
            .filter(func.lower(TransactionType.name) == "gasto")
            .filter(Transaction.transaction_date >= start_date)
            .filter(Transaction.transaction_date <= end_date)
            .group_by(TransactionCategory.transaction_category_id, TransactionCategory.name)
            .all()
        )

    def get_all_user_transactions_eager(self, user_id: UUID) -> list[Transaction]:
        """Get all transactions for a user with eager-loaded relationships.

        This avoids N+1 queries when accessing transaction_type, category,
        and transaction_frequency relationships.

        Returns:
            A list of Transaction entities with relationships populated.
        """
        from sqlalchemy.orm import joinedload

        return (
            self._session.query(Transaction)
            .options(
                joinedload(Transaction.transaction_type),
                joinedload(Transaction.category),
                joinedload(Transaction.transaction_frequency),
                joinedload(Transaction.user),
            )
            .filter(Transaction.user_id == user_id)
            .filter(
                (Transaction.is_group_transaction == False)
                | (Transaction.is_group_transaction.is_(None))
            )
            .all()
        )

    def get_all_group_transactions_eager(self, user_ids: list[UUID]) -> list[Transaction]:
        """Get all transactions for a list of users with eager-loaded relationships.

        This avoids N+1 queries when accessing transaction_type, category,
        transaction_frequency, and user relationships.

        Returns:
            A list of Transaction entities with relationships populated.
        """
        from sqlalchemy.orm import joinedload

        return (
            self._session.query(Transaction)
            .options(
                joinedload(Transaction.transaction_type),
                joinedload(Transaction.category),
                joinedload(Transaction.transaction_frequency),
                joinedload(Transaction.user),
            )
            .filter(Transaction.user_id.in_(user_ids))
            .filter(Transaction.is_group_transaction == True)
            .all()
        )

    def get_transactions_by_user_in_range(
        self,
        user_id: UUID,
        page: int = 1,
        limit: int = 10,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[list[Transaction], int]:
        """Get paginated transactions respecting transaction frequency.

        One-time transactions (frequency = Única or NULL) are filtered by date range.
        Recurring transactions (Mensual/Semanal) are included if they are active,
        i.e. transaction_date <= end_date.

        When both start_date and end_date are provided, recurring transactions that
        started before the range but are still active are included.
        """
        from sqlalchemy import or_

        query = self._session.query(Transaction).filter(
            Transaction.user_id == user_id
        )

        if start_date and end_date:
            freqs = {
                f.name: f.transaction_frequency_id
                for f in self._session.query(TransactionFrequency).all()
            }
            one_time_id = freqs.get("Única")
            monthly_id = freqs.get("Mensual")
            weekly_id = freqs.get("Semanal")
            recurring_ids = [
                rid for rid in [monthly_id, weekly_id] if rid is not None
            ]

            conditions = []

            # One-time (or null frequency): within date range
            ot_cond = (
                (Transaction.transaction_date >= start_date)
                & (Transaction.transaction_date <= end_date)
            )
            if one_time_id:
                ot_cond = ot_cond & (
                    (Transaction.transaction_frequency_id == one_time_id)
                    | (Transaction.transaction_frequency_id.is_(None))
                )
            conditions.append(ot_cond)

            # Recurring: active if transaction_date <= end_date
            if recurring_ids:
                conditions.append(
                    (Transaction.transaction_frequency_id.in_(recurring_ids))
                    & (Transaction.transaction_date <= end_date)
                )

            query = query.filter(or_(*conditions))
        elif start_date:
            query = query.filter(Transaction.transaction_date >= start_date)
        elif end_date:
            query = query.filter(Transaction.transaction_date <= end_date)

        total_count = query.count()

        offset = (page - 1) * limit
        transactions = (
            query.order_by(Transaction.transaction_date.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return transactions, total_count

    def get_monthly_comparison(
        self, user_id: UUID, limit_months: int = 6
    ) -> list[tuple[str, str, Decimal]]:
        """Get monthly totals for income and expenses."""
        # Handle different dialects (PostgreSQL for QA/Prod, SQLite for tests/dev)
        if self._session.bind.dialect.name == "postgresql":
            month_format = func.to_char(Transaction.transaction_date, "YYYY-MM")
        else:
            month_format = func.strftime("%Y-%m", Transaction.transaction_date)
        
        return (
            self._session.query(
                month_format.label("month"),
                TransactionType.name,
                func.sum(Transaction.amount),
            )
            .join(TransactionType, Transaction.transaction_type_id == TransactionType.transaction_type_id)
            .filter(Transaction.user_id == user_id)
            .group_by("month", TransactionType.name)
            .order_by("month")
            .limit(limit_months * 2) 
            .all()
        )
