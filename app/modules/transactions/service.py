"""
Transactions service — business logic layer.
"""

import calendar
import math
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from uuid import UUID

from app.modules.transactions.dto import (
    CategoryDistributionDTO,
    FinancialSummaryDTO,
    IncomeTypeResponseDTO,
    IncomeVsExpensesChartDTO,
    PaginationMetaDTO,
    TransactionCategoryResponseDTO,
    TransactionCreateDTO,
    TransactionFrequencyResponseDTO,
    TransactionPaginationResponseDTO,
    TransactionResponseDTO,
    TransactionTypeResponseDTO,
    TransactionUpdateDTO,
)
from app.modules.transactions.entities import Transaction
from app.modules.transactions.repository import TransactionsRepository
from app.modules.users.repository import UserRepository
from app.shared.exceptions import ForbiddenException, NotFoundException

SANTIAGO_TZ = ZoneInfo("America/Santiago")


class TransactionsService:
    """Business logic for transaction entities."""

    def __init__(self, repository: TransactionsRepository, user_repository: UserRepository):
        self._repository = repository
        self._user_repository = user_repository

    def get_income_types(self) -> list[IncomeTypeResponseDTO]:
        """Get all available income types.
        
        Returns:
            List of income types.
        """
        income_types = self._repository.get_all_income_types()
        return [
            IncomeTypeResponseDTO(id=it.income_type_id, name=it.name)
            for it in income_types
        ]

    def get_transaction_types(self) -> list[TransactionTypeResponseDTO]:
        """Get all transaction types."""
        types = self._repository.get_all_transaction_types()
        return [
            TransactionTypeResponseDTO(
                id=t.transaction_type_id, name=t.name, description=t.description
            )
            for t in types
        ]

    def get_transaction_frequencies(self) -> list[TransactionFrequencyResponseDTO]:
        """Get all transaction frequencies."""
        frequencies = self._repository.get_all_transaction_frequencies()
        return [
            TransactionFrequencyResponseDTO(
                id=f.transaction_frequency_id, name=f.name, description=f.description
            )
            for f in frequencies
        ]

    def get_transaction_categories(self) -> list[TransactionCategoryResponseDTO]:
        """Get all transaction categories."""
        categories = self._repository.get_all_transaction_categories()
        return [
            TransactionCategoryResponseDTO(
                id=c.transaction_category_id,
                name=c.name,
                description=c.description,
                transaction_type_id=c.transaction_type_id,
            )
            for c in categories
        ]

    def create_transaction(
        self, user_id: UUID, data: TransactionCreateDTO
    ) -> TransactionResponseDTO:
        """Create a new transaction for the user."""
        transaction = Transaction(
            user_id=user_id,
            amount=data.amount,
            transaction_type_id=data.transaction_type_id,
            transaction_category_id=data.transaction_category_id,
            transaction_frequency_id=data.transaction_frequency_id,
            description=data.description,
            transaction_date=data.transaction_date,
        )
        created = self._repository.create_transaction(transaction)
        return self._map_to_response_dto(created)

    def update_transaction(
        self, user_id: UUID, transaction_id: UUID, data: TransactionUpdateDTO
    ) -> TransactionResponseDTO:
        """Update an existing transaction if it belongs to the user."""
        transaction = self._repository.get_transaction_by_id(transaction_id)
        if not transaction:
            raise NotFoundException("La transacción no existe")

        if transaction.user_id != user_id:
            raise ForbiddenException("No puedes editar una transacción que no te pertenece")

        updated = self._repository.update_transaction(
            transaction_id, **data.model_dump(exclude_unset=True)
        )

        # Sync user.monthly_income when a Sueldo income transaction is updated
        if data.amount is not None:
            income_type = self._repository.get_transaction_type_by_name("Ingreso")
            sueldo_category = self._repository.get_transaction_category_by_name("Sueldo")
            if (
                income_type
                and sueldo_category
                and updated.transaction_type_id == income_type.transaction_type_id
                and updated.transaction_category_id == sueldo_category.transaction_category_id
            ):
                user = self._user_repository.get_user_by_id(user_id)
                if user:
                    user.monthly_income = data.amount
                    self._user_repository.update_user_with_commit(user)

        return self._map_to_response_dto(updated)

    def delete_transaction(self, user_id: UUID, transaction_id: UUID) -> bool:
        """Delete a transaction if it belongs to the user."""
        transaction = self._repository.get_transaction_by_id(transaction_id)
        if not transaction:
            raise NotFoundException("La transacción no existe")

        if transaction.user_id != user_id:
            raise ForbiddenException("No tienes permiso para eliminar este registro")

        return self._repository.delete_transaction(transaction_id)

    def get_user_transactions(
        self,
        user_id: UUID,
        page: int = 1,
        limit: int = 10,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> TransactionPaginationResponseDTO:
        """Get paginated transactions for the user, respecting frequency logic.

        Recurring transactions (Mensual/Semanal) that are active in the date
        range are included even if their transaction_date falls before the
        queried period.
        """
        transactions = self._repository.get_all_user_transactions_eager(user_id)
        projected: list[TransactionResponseDTO] = []

        if end_date is None:
            end_date = date.today()

        for transaction in transactions:
            local_tx_date = self._to_santiago_date(transaction.transaction_date)
            freq_name = (
                transaction.transaction_frequency.name
                if transaction.transaction_frequency
                else None
            )
            freq_lower = freq_name.lower().strip() if freq_name else ""

            if freq_lower == "mensual":
                current_date = local_tx_date
                while current_date <= end_date:
                    if start_date is None or current_date >= start_date:
                        projected.append(
                            self._map_to_response_dto(transaction, current_date)
                        )
                    current_date = self._next_month_date(
                        current_date, local_tx_date.day
                    )
                continue

            if freq_lower == "semanal":
                current_date = local_tx_date
                while current_date <= end_date:
                    if start_date is None or current_date >= start_date:
                        projected.append(
                            self._map_to_response_dto(transaction, current_date)
                        )
                    current_date += timedelta(days=7)
                continue

            if local_tx_date > end_date:
                continue
            if start_date is not None and local_tx_date < start_date:
                continue

            projected.append(self._map_to_response_dto(transaction, local_tx_date))

        projected.sort(key=lambda item: item.transaction_date, reverse=True)
        total_count = len(projected)

        total_pages = math.ceil(total_count / limit) if total_count > 0 else 0
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit

        meta = PaginationMetaDTO(
            currentPage=page,
            totalPages=total_pages,
            totalItems=total_count,
            itemsPerPage=limit,
        )

        data = projected[start_idx:end_idx]

        return TransactionPaginationResponseDTO(meta=meta, data=data)

    def _calculate_frequency_contribution(
        self,
        amount: Decimal,
        frequency_name: str | None,
        transaction_date: date | datetime,
        period_start: date,
        period_end: date,
    ) -> Decimal:
        """Calculate how much a transaction contributes to a period based on its frequency.

        Args:
            amount: The base transaction amount.
            frequency_name: The frequency name (None, Única, Mensual, Semanal).
            transaction_date: The transaction's recorded date.
            period_start: Start of the period (inclusive).
            period_end: End of the period (inclusive).

        Returns:
            The adjusted amount contributed to the period.
        """
        local_tx_date = self._to_santiago_date(transaction_date)

        if local_tx_date > period_end:
            return Decimal("0")

        freq_lower = frequency_name.lower().strip() if frequency_name else ""

        if freq_lower in ("única", "unica"):
            # One-time: only if within the period
            if period_start <= local_tx_date <= period_end:
                return amount
            return Decimal("0")

        if freq_lower == "mensual":
            # Monthly: count months from max(transaction_date, period_start) to period_end
            effective_start = max(local_tx_date, period_start)
            months = (
                (period_end.year - effective_start.year) * 12
                + (period_end.month - effective_start.month)
                + 1
            )
            if months <= 0:
                return Decimal("0")
            return amount * Decimal(str(months))

        if freq_lower == "semanal":
            # Weekly: count weeks from effective_start to period_end
            effective_start = max(local_tx_date, period_start)
            days = (period_end - effective_start).days + 1
            if days <= 0:
                return Decimal("0")
            weeks = (days + 6) // 7  # ceiling division
            return amount * Decimal(str(weeks))

        # Default / null frequency: treat as one-time
        if period_start <= local_tx_date <= period_end:
            return amount
        return Decimal("0")

    def _to_santiago_datetime(self, transaction_date: date | datetime) -> datetime:
        """Convert a stored transaction timestamp to America/Santiago."""
        if isinstance(transaction_date, datetime):
            if transaction_date.tzinfo is None:
                return transaction_date.replace(tzinfo=SANTIAGO_TZ)
            return transaction_date.astimezone(SANTIAGO_TZ)

        return datetime.combine(transaction_date, datetime.min.time(), tzinfo=SANTIAGO_TZ)

    def _to_santiago_date(self, transaction_date: date | datetime) -> date:
        """Return the Chile-local calendar date for a transaction timestamp."""
        return self._to_santiago_datetime(transaction_date).date()

    def _next_month_date(self, current_date: date, original_day: int) -> date:
        """Advance a date by one calendar month, clamping to the last valid day."""
        next_year = current_date.year + (1 if current_date.month == 12 else 0)
        next_month = 1 if current_date.month == 12 else current_date.month + 1
        last_day = calendar.monthrange(next_year, next_month)[1]
        next_day = min(original_day, last_day)
        return date(next_year, next_month, next_day)

    def _map_to_response_dto(
        self, t: Transaction, transaction_date: date | datetime | None = None
    ) -> TransactionResponseDTO:
        """Helper to map Transaction entity to TransactionResponseDTO."""
        response_date = (
            transaction_date
            if isinstance(transaction_date, date)
            and not isinstance(transaction_date, datetime)
            else self._to_santiago_date(transaction_date or t.transaction_date)
        )
        return TransactionResponseDTO(
            transaction_id=t.transaction_id,
            amount=t.amount,
            description=t.description,
            transaction_date=response_date,
            transaction_type_id=t.transaction_type_id,
            transaction_category_id=t.transaction_category_id,
            transaction_frequency_id=t.transaction_frequency_id,
        )

    def get_financial_summary(
        self, user_id: UUID, start_date: date | None = None, end_date: date | None = None
    ) -> FinancialSummaryDTO:
        """Calculate financial totals for a given period, respecting transaction frequencies.

        Recurring transactions (Mensual/Semanal) are projected across the period
        based on their frequency. For example, a monthly transaction of 1000
        spanning 3 months contributes 3000.
        """
        if not start_date:
            start_date = date.today().replace(day=1)
        if not end_date:
            end_date = date.today()

        transactions = self._repository.get_all_user_transactions_eager(user_id)

        income = Decimal("0")
        expenses = Decimal("0")

        for t in transactions:
            freq_name = (
                t.transaction_frequency.name if t.transaction_frequency else None
            )
            amount = self._calculate_frequency_contribution(
                t.amount, freq_name, t.transaction_date, start_date, end_date
            )
            if amount <= 0:
                continue
            type_name = (
                t.transaction_type.name.lower().strip()
                if t.transaction_type
                else ""
            )
            if type_name == "ingreso":
                income += amount
            elif type_name == "gasto":
                expenses += amount

        return FinancialSummaryDTO(
            total_income=income,
            total_expenses=expenses,
            total_balance=income - expenses,
        )

    def get_expense_distribution(
        self, user_id: UUID, start_date: date | None = None, end_date: date | None = None
    ) -> list[CategoryDistributionDTO]:
        """Get total expenses by category and their percentage, respecting frequencies.

        Recurring expenses are projected across the period. For example, a
        monthly expense of 200 spanning 3 months contributes 600 to its category.
        """
        if not start_date:
            start_date = date.today().replace(day=1)
        if not end_date:
            end_date = date.today()

        transactions = self._repository.get_all_user_transactions_eager(user_id)

        # Group by category, only for expenses
        category_totals: dict[UUID | None, dict] = {}
        for t in transactions:
            type_name = (
                t.transaction_type.name.lower().strip()
                if t.transaction_type
                else ""
            )
            if type_name != "gasto":
                continue

            freq_name = (
                t.transaction_frequency.name if t.transaction_frequency else None
            )
            amount = self._calculate_frequency_contribution(
                t.amount, freq_name, t.transaction_date, start_date, end_date
            )
            if amount <= 0:
                continue

            cat_id = t.transaction_category_id
            cat_name = t.category.name if t.category else "Sin categoría"
            if cat_id not in category_totals:
                category_totals[cat_id] = {"name": cat_name, "total": Decimal("0")}
            category_totals[cat_id]["total"] += amount

        total_expense = sum(v["total"] for v in category_totals.values())

        distribution = []
        for cat_id, data in category_totals.items():
            percentage = (
                (float(data["total"]) / float(total_expense) * 100)
                if total_expense > 0
                else 0
            )
            distribution.append(
                CategoryDistributionDTO(
                    category_id=cat_id,
                    category_name=data["name"],
                    total_amount=data["total"],
                    percentage=round(percentage, 2),
                )
            )

        # Sort by amount descending
        distribution.sort(key=lambda x: x.total_amount, reverse=True)
        return distribution

    def get_income_vs_expenses(self, user_id: UUID) -> IncomeVsExpensesChartDTO:
        """Compare income vs expenses over the last 6 months, respecting frequencies.

        Recurring transactions are projected into each month. For the current
        month the upper bound is capped at today (not end-of-month) so the
        values are consistent with the financial summary card, which also uses
        today as its default end_date.
        """
        from datetime import timedelta

        MONTH_LABELS = {
            1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr",
            5: "May", 6: "Jun", 7: "Jul", 8: "Ago",
            9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
        }

        transactions = self._repository.get_all_user_transactions_eager(user_id)

        today = date.today()

        # Generate the last 6 calendar months (oldest → newest)
        months: list[tuple[int, int]] = []
        for i in range(5, -1, -1):
            m = today.month - i
            y = today.year
            while m < 1:
                m += 12
                y -= 1
            while m > 12:
                m -= 12
                y += 1
            months.append((y, m))

        labels: list[str] = []
        income_series: list[Decimal] = []
        expense_series: list[Decimal] = []

        for year, month_num in months:
            month_start = date(year, month_num, 1)

            # Cap the current month at today so the chart and summary always
            # reflect the same "snapshot as of today".
            if year == today.year and month_num == today.month:
                month_end = today
            elif month_num == 12:
                month_end = date(year, 12, 31)
            else:
                month_end = date(year, month_num + 1, 1) - timedelta(days=1)

            income = Decimal("0")
            expenses = Decimal("0")

            for t in transactions:
                freq_name = (
                    t.transaction_frequency.name
                    if t.transaction_frequency
                    else None
                )
                amount = self._calculate_frequency_contribution(
                    t.amount,
                    freq_name,
                    t.transaction_date,
                    month_start,
                    month_end,
                )
                if amount <= 0:
                    continue
                type_name = (
                    t.transaction_type.name.lower().strip()
                    if t.transaction_type
                    else ""
                )
                if type_name == "ingreso":
                    income += amount
                elif type_name == "gasto":
                    expenses += amount

            labels.append(MONTH_LABELS[month_num])
            income_series.append(income)
            expense_series.append(expenses)

        return IncomeVsExpensesChartDTO(
            labels=labels,
            income=income_series,
            expense=expense_series,
        )
