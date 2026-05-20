"""
Transactions controller — HTTP endpoint layer.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.modules.transactions.dto import (
    CategoryDistributionDTO,
    FinancialSummaryDTO,
    GroupTransactionPaginationResponseDTO,
    IncomeTypeResponseDTO,
    IncomeVsExpensesChartDTO,
    TransactionCategoryResponseDTO,
    TransactionCreateDTO,
    TransactionFrequencyResponseDTO,
    TransactionPaginationResponseDTO,
    TransactionResponseDTO,
    TransactionTypeResponseDTO,
    TransactionUpdateDTO,
)
from app.modules.transactions.repository import TransactionsRepository
from app.modules.transactions.service import TransactionsService
from app.modules.groups.repository import GroupsRepository
from app.modules.users.entities import User
from app.modules.users.repository import UserRepository
from app.shared.database import get_db
from app.shared.security.auth_middleware import get_current_user

router = APIRouter(prefix="/v1/transactions", tags=["Transactions"])


def _get_transactions_service(db: Session = Depends(get_db)) -> TransactionsService:
    """Dependency to build transactions service with its database repository."""
    repository = TransactionsRepository(db)
    user_repo = UserRepository(db)
    groups_repo = GroupsRepository(db)
    return TransactionsService(repository, user_repo, groups_repo)


@router.get(
    "/income-types",
    response_model=list[IncomeTypeResponseDTO],
    summary="Obtener tipos de ingresos",
    description="Devuelve el catálogo de tipos de ingresos disponibles para registro.",
)
def get_income_types(service: TransactionsService = Depends(_get_transactions_service)):
    """Retrieve all available income types."""
    return service.get_income_types()


@router.get(
    "/types",
    response_model=list[TransactionTypeResponseDTO],
    summary="Obtener tipos de transacciones",
    description="Devuelve el catálogo de tipos de transacciones (ej: ingreso, gasto).",
)
def get_transaction_types(service: TransactionsService = Depends(_get_transactions_service)):
    """Retrieve all available transaction types."""
    return service.get_transaction_types()


@router.get(
    "/frequencies",
    response_model=list[TransactionFrequencyResponseDTO],
    summary="Obtener frecuencias de transacciones",
    description="Devuelve el catálogo de frecuencias (ej: única, mensual).",
)
def get_transaction_frequencies(service: TransactionsService = Depends(_get_transactions_service)):
    """Retrieve all available transaction frequencies."""
    return service.get_transaction_frequencies()


@router.get(
    "/categories",
    response_model=list[TransactionCategoryResponseDTO],
    summary="Obtener categorías de transacciones",
    description="Devuelve el catálogo de categorías de transacciones y su tipo asociado.",
)
def get_transaction_categories(service: TransactionsService = Depends(_get_transactions_service)):
    """Retrieve all available transaction categories."""
    return service.get_transaction_categories()


@router.post(
    "",
    response_model=TransactionResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar transacción",
    description="Crea un nuevo registro de ingreso o gasto para el usuario autenticado.",
)
def create_transaction(
    data: TransactionCreateDTO,
    user: User = Depends(get_current_user),
    service: TransactionsService = Depends(_get_transactions_service),
):
    """Create a new transaction record."""
    return service.create_transaction(user.user_id, data)


@router.get(
    "/individual",
    response_model=TransactionPaginationResponseDTO,
    summary="Listar transacciones individualmente",
    description="Obtiene la lista paginada de transacciones del usuario, con filtros opcionales.",
)
def list_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    user: User = Depends(get_current_user),
    service: TransactionsService = Depends(_get_transactions_service),
):
    """List paginated transactions for the current user."""
    return service.get_user_transactions(
        user.user_id, page, limit, start_date, end_date
    )


@router.put(
    "/{transaction_id}",
    response_model=TransactionResponseDTO,
    summary="Actualizar transacción",
    description="Modifica un registro de transacción existente.",
)
def update_transaction(
    transaction_id: UUID,
    data: TransactionUpdateDTO,
    user: User = Depends(get_current_user),
    service: TransactionsService = Depends(_get_transactions_service),
):
    """Update an existing transaction record."""
    return service.update_transaction(user.user_id, transaction_id, data)


@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar transacción",
    description="Elimina un registro de transacción permanentemente.",
)
def delete_transaction(
    transaction_id: UUID,
    user: User = Depends(get_current_user),
    service: TransactionsService = Depends(_get_transactions_service),
):
    """Delete a transaction record."""
    service.delete_transaction(user.user_id, transaction_id)
    return


@router.get(
    "/summary",
    response_model=FinancialSummaryDTO,
    summary="Resumen financiero",
    description="Obtiene el balance total, ingresos y gastos del periodo actual.",
)
def get_financial_summary(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    user: User = Depends(get_current_user),
    service: TransactionsService = Depends(_get_transactions_service),
):
    """Get financial summary for the current user."""
    return service.get_financial_summary(user.user_id, start_date, end_date)


@router.get(
    "/analytics/distribution",
    response_model=list[CategoryDistributionDTO],
    summary="Distribución por categorías",
    description="Obtiene el desglose de gastos por categoría y su porcentaje del total.",
)
def get_expense_distribution(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    user: User = Depends(get_current_user),
    service: TransactionsService = Depends(_get_transactions_service),
):
    """Get expense distribution for the current user."""
    return service.get_expense_distribution(user.user_id, start_date, end_date)


@router.get(
    "/analytics/income-vs-expenses",
    response_model=IncomeVsExpensesChartDTO,
    summary="Ingresos vs Gastos",
    description="Obtiene la comparativa mensual de ingresos y gastos de los últimos 6 meses.",
)
def get_income_vs_expenses(
    user: User = Depends(get_current_user),
    service: TransactionsService = Depends(_get_transactions_service),
):
    """Get monthly income vs expenses comparison for the current user."""
    return service.get_income_vs_expenses(user.user_id)


# ---------------------------------------------------------------------------
# Family Group Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/family-group",
    response_model=GroupTransactionPaginationResponseDTO,
    summary="Listar transacciones del grupo familiar",
    description="Obtiene la lista paginada de transacciones de todos los miembros del grupo.",
)
def list_group_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    user: User = Depends(get_current_user),
    service: TransactionsService = Depends(_get_transactions_service),
):
    """List paginated transactions for the current user's family group."""
    return service.get_group_transactions(
        user.user_id, page, limit, start_date, end_date
    )


@router.get(
    "/family-group/summary",
    response_model=FinancialSummaryDTO,
    summary="Resumen financiero del grupo",
    description="Obtiene el balance total, ingresos y gastos del periodo actual para todo el grupo.",
)
def get_group_financial_summary(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    user: User = Depends(get_current_user),
    service: TransactionsService = Depends(_get_transactions_service),
):
    """Get financial summary for the current user's family group."""
    return service.get_group_financial_summary(user.user_id, start_date, end_date)


@router.get(
    "/family-group/analytics/distribution",
    response_model=list[CategoryDistributionDTO],
    summary="Distribución por categorías del grupo",
    description="Obtiene el desglose de gastos por categoría y su porcentaje del total para el grupo.",
)
def get_group_expense_distribution(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    user: User = Depends(get_current_user),
    service: TransactionsService = Depends(_get_transactions_service),
):
    """Get expense distribution for the current user's family group."""
    return service.get_group_expense_distribution(user.user_id, start_date, end_date)


@router.get(
    "/family-group/analytics/income-vs-expenses",
    response_model=IncomeVsExpensesChartDTO,
    summary="Ingresos vs Gastos del grupo",
    description="Obtiene la comparativa mensual de ingresos y gastos de los últimos 6 meses para el grupo.",
)
def get_group_income_vs_expenses(
    user: User = Depends(get_current_user),
    service: TransactionsService = Depends(_get_transactions_service),
):
    """Get monthly income vs expenses comparison for the current user's family group."""
    return service.get_group_income_vs_expenses(user.user_id)
