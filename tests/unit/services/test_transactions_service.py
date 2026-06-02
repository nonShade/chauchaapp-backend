from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock
import uuid

import pytest

from app.modules.transactions.entities import (
    Transaction,
    TransactionCategory,
    TransactionFrequency,
    TransactionType,
)
from app.modules.transactions.repository import TransactionsRepository
from app.modules.transactions.service import TransactionsService
from app.modules.notifications.entities import NotificationStatus, NotificationType
from app.modules.notifications.repository import NotificationsRepository
from app.modules.transactions.dto import (
    TransactionCategoryResponseDTO,
    TransactionCreateDTO,
    TransactionFrequencyResponseDTO,
    TransactionPaginationResponseDTO,
    TransactionResponseDTO,
    TransactionTypeResponseDTO,
    TransactionUpdateDTO,
)
from app.shared.exceptions import ForbiddenException, NotFoundException
from app.modules.users.repository import UserRepository


@pytest.fixture
def mock_repository():
    return MagicMock(spec=TransactionsRepository)


@pytest.fixture
def mock_user_repository():
    return MagicMock(spec=UserRepository)


@pytest.fixture
def service(mock_repository, mock_user_repository):
    return TransactionsService(
        repository=mock_repository, user_repository=mock_user_repository
    )


def _make_transaction_mock(
    amount: Decimal,
    type_name: str,
    tx_date: date,
    freq_name: str | None = None,
    category_name: str | None = None,
    category_id: uuid.UUID | None = None,
) -> MagicMock:
    """Helper to build a mock Transaction with set up relationships."""
    tx = MagicMock(spec=Transaction)
    tx.amount = amount
    tx.transaction_date = tx_date
    tx.description = None

    tx.transaction_type = MagicMock()
    tx.transaction_type.name = type_name

    if freq_name:
        tx.transaction_frequency = MagicMock()
        tx.transaction_frequency.name = freq_name
        tx.transaction_frequency_id = uuid.uuid4()
    else:
        tx.transaction_frequency = None
        tx.transaction_frequency_id = None

    if category_name or category_id:
        tx.category = MagicMock()
        tx.category.name = category_name or "Test Category"
    else:
        tx.category = None

    tx.transaction_category_id = category_id
    tx.transaction_type_id = uuid.uuid4()
    tx.transaction_id = uuid.uuid4()

    return tx


def test_get_transaction_types(service, mock_repository):
    # Arrange
    fake_id = uuid.uuid4()
    fake_type = TransactionType(transaction_type_id=fake_id, name="ingreso", description="Ingreso desc")
    mock_repository.get_all_transaction_types.return_value = [fake_type]

    # Act
    result = service.get_transaction_types()

    # Assert
    mock_repository.get_all_transaction_types.assert_called_once()
    assert len(result) == 1
    assert isinstance(result[0], TransactionTypeResponseDTO)
    assert result[0].id == fake_id
    assert result[0].name == "ingreso"
    assert result[0].description == "Ingreso desc"


def test_get_transaction_frequencies(service, mock_repository):
    # Arrange
    fake_id = uuid.uuid4()
    fake_freq = TransactionFrequency(transaction_frequency_id=fake_id, name="mensual", description="Mensual desc")
    mock_repository.get_all_transaction_frequencies.return_value = [fake_freq]

    # Act
    result = service.get_transaction_frequencies()

    # Assert
    mock_repository.get_all_transaction_frequencies.assert_called_once()
    assert len(result) == 1
    assert isinstance(result[0], TransactionFrequencyResponseDTO)
    assert result[0].id == fake_id
    assert result[0].name == "mensual"
    assert result[0].description == "Mensual desc"


def test_get_transaction_categories(service, mock_repository):
    # Arrange
    fake_cat_id = uuid.uuid4()
    fake_type_id = uuid.uuid4()
    fake_cat = TransactionCategory(
        transaction_category_id=fake_cat_id,
        name="salud",
        description="Gastos medicos",
        transaction_type_id=fake_type_id,
    )
    mock_repository.get_all_transaction_categories.return_value = [fake_cat]

    # Act
    result = service.get_transaction_categories()

    # Assert
    mock_repository.get_all_transaction_categories.assert_called_once()
    assert len(result) == 1
    assert isinstance(result[0], TransactionCategoryResponseDTO)
    assert result[0].id == fake_cat_id
    assert result[0].name == "salud"
    assert result[0].description == "Gastos medicos"
    assert result[0].transaction_type_id == fake_type_id


def test_create_transaction(service, mock_repository):
    # Arrange
    user_id = uuid.uuid4()
    type_id = uuid.uuid4()
    cat_id = uuid.uuid4()
    data = TransactionCreateDTO(
        amount=Decimal("15000"),
        transaction_type_id=type_id,
        transaction_category_id=cat_id,
        transaction_date=date(2026, 4, 29),
    )

    mock_repository.create_transaction.side_effect = lambda t: setattr(t, 'transaction_id', uuid.uuid4()) or t

    # Act
    result = service.create_transaction(user_id, data)

    # Assert
    mock_repository.create_transaction.assert_called_once()
    assert result.amount == Decimal("15000")
    assert result.transaction_type_id == type_id
    assert result.transaction_category_id == cat_id


def test_update_transaction_success(service, mock_repository):
    # Arrange
    user_id = uuid.uuid4()
    tx_id = uuid.uuid4()
    existing_tx = Transaction(
        transaction_id=tx_id, user_id=user_id, amount=Decimal("1000"),
        transaction_date=date(2026, 1, 1), transaction_type_id=uuid.uuid4()
    )
    mock_repository.get_transaction_by_id.return_value = existing_tx

    data = TransactionUpdateDTO(amount=Decimal("2000"))
    mock_repository.update_transaction.return_value = Transaction(
        transaction_id=tx_id, user_id=user_id, amount=Decimal("2000"),
        transaction_date=date(2026, 1, 1), transaction_type_id=uuid.uuid4()
    )

    # Act
    result = service.update_transaction(user_id, tx_id, data)

    # Assert
    assert result.amount == Decimal("2000")
    mock_repository.update_transaction.assert_called_once()


def test_update_transaction_not_owner(service, mock_repository):
    # Arrange
    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    tx_id = uuid.uuid4()
    existing_tx = Transaction(
        transaction_id=tx_id, user_id=other_user_id, amount=Decimal("1000"),
        transaction_date=date(2026, 1, 1), transaction_type_id=uuid.uuid4()
    )
    mock_repository.get_transaction_by_id.return_value = existing_tx

    # Act & Assert
    with pytest.raises(ForbiddenException):
        service.update_transaction(user_id, tx_id, TransactionUpdateDTO(amount=Decimal("500")))


def test_delete_transaction_success(service, mock_repository):
    # Arrange
    user_id = uuid.uuid4()
    tx_id = uuid.uuid4()
    existing_tx = Transaction(transaction_id=tx_id, user_id=user_id)
    mock_repository.get_transaction_by_id.return_value = existing_tx
    mock_repository.delete_transaction.return_value = True

    # Act
    result = service.delete_transaction(user_id, tx_id)

    # Assert
    assert result is True
    mock_repository.delete_transaction.assert_called_once_with(tx_id)


def test_get_user_transactions(service, mock_repository):
    # Arrange
    user_id = uuid.uuid4()
    tx = Transaction(
        transaction_id=uuid.uuid4(),
        user_id=user_id,
        amount=Decimal("100"),
        transaction_date=date(2026, 1, 1),
        transaction_type_id=uuid.uuid4()
    )
    mock_repository.get_all_user_transactions_eager.return_value = [tx]

    # Act
    result = service.get_user_transactions(user_id, page=1, limit=10)

    # Assert
    assert result.meta.totalItems == 1
    assert len(result.data) == 1
    assert result.data[0].amount == Decimal("100")


def test_get_user_transactions_projects_monthly_recurrence(service, mock_repository):
    # Arrange
    user_id = uuid.uuid4()
    tx = _make_transaction_mock(
        amount=Decimal("1000"),
        type_name="ingreso",
        tx_date=date(2026, 1, 31),
        freq_name="Mensual",
    )
    mock_repository.get_all_user_transactions_eager.return_value = [tx]

    # Act
    result = service.get_user_transactions(
        user_id,
        page=1,
        limit=10,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
    )

    # Assert
    assert result.meta.totalItems == 3
    assert [item.transaction_date.date() for item in result.data] == [
        date(2026, 3, 31),
        date(2026, 2, 28),
        date(2026, 1, 31),
    ]
    assert all(item.amount == Decimal("1000") for item in result.data)


def test_get_user_transactions_orders_same_day_by_time(service, mock_repository):
    user_id = uuid.uuid4()
    early_tx = _make_transaction_mock(
        amount=Decimal("100"),
        type_name="gasto",
        tx_date=datetime(2026, 5, 20, 9, 0),
    )
    late_tx = _make_transaction_mock(
        amount=Decimal("200"),
        type_name="ingreso",
        tx_date=datetime(2026, 5, 20, 18, 30),
    )
    mock_repository.get_all_user_transactions_eager.return_value = [
        early_tx,
        late_tx,
    ]

    result = service.get_user_transactions(
        user_id,
        page=1,
        limit=10,
        start_date=date(2026, 5, 20),
        end_date=date(2026, 5, 20),
    )

    assert [item.amount for item in result.data] == [
        Decimal("200"),
        Decimal("100"),
    ]
    assert result.data[0].transaction_date.hour == 18


def test_transaction_create_dto_parses_local_timezone():
    data = TransactionCreateDTO(
        amount=Decimal("100"),
        transaction_type_id=uuid.uuid4(),
        transaction_date=date(2026, 4, 29),
    )

    assert isinstance(data.transaction_date, datetime)
    assert data.transaction_date.tzinfo is not None
    assert data.transaction_date.tzinfo.key == "America/Santiago"


def test_create_expense_transaction_creates_reminder_notification(
    mock_repository,
    mock_user_repository,
):
    notifications_repo = MagicMock(spec=NotificationsRepository)
    service = TransactionsService(
        repository=mock_repository,
        user_repository=mock_user_repository,
        notifications_repository=notifications_repo,
    )
    user_id = uuid.uuid4()
    type_id = uuid.uuid4()
    tx_id = uuid.uuid4()
    data = TransactionCreateDTO(
        amount=Decimal("8500"),
        transaction_type_id=type_id,
        description="Netflix",
        transaction_date="2026-06-20",
    )

    def _create_transaction(transaction):
        transaction.transaction_id = tx_id
        return transaction

    expense_type = MagicMock()
    expense_type.name = "Gasto"
    reminder_type = MagicMock(spec=NotificationType)
    reminder_type.notification_type_id = uuid.uuid4()
    pending_status = MagicMock(spec=NotificationStatus)
    pending_status.notification_status_id = uuid.uuid4()
    mock_repository.create_transaction.side_effect = _create_transaction
    mock_repository.get_transaction_type_by_id.return_value = expense_type
    notifications_repo.get_notification_type_by_name.return_value = reminder_type
    notifications_repo.get_notification_status_by_name.return_value = pending_status

    service.create_transaction(user_id, data)

    notifications_repo.create_notification.assert_called_once()
    notification = notifications_repo.create_notification.call_args.args[0]
    assert notification.user_id == user_id
    assert notification.reference_id == tx_id
    assert notification.reference_type == "transaction"
    assert notification.scheduled_date == date(2026, 6, 17)
    assert "Netflix" in notification.message


def test_get_financial_summary(service, mock_repository):
    # Arrange
    user_id = uuid.uuid4()

    income_tx = _make_transaction_mock(
        amount=Decimal("1000"),
        type_name="ingreso",
        tx_date=date(2026, 5, 1),
    )
    expense_tx = _make_transaction_mock(
        amount=Decimal("400"),
        type_name="gasto",
        tx_date=date(2026, 5, 1),
    )
    mock_repository.get_all_user_transactions_eager.return_value = [
        income_tx, expense_tx
    ]

    # Act
    result = service.get_financial_summary(
        user_id,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 31),
    )

    # Assert
    assert result.total_income == Decimal("1000")
    assert result.total_expenses == Decimal("400")
    assert result.total_balance == Decimal("600")


def test_get_financial_summary_with_monthly_frequency(service, mock_repository):
    """A monthly transaction started in April should contribute to May's summary."""
    # Arrange
    user_id = uuid.uuid4()

    monthly_tx = _make_transaction_mock(
        amount=Decimal("1000"),
        type_name="ingreso",
        tx_date=date(2026, 4, 1),
        freq_name="Mensual",
    )
    mock_repository.get_all_user_transactions_eager.return_value = [monthly_tx]

    # Act — query for May 2026
    result = service.get_financial_summary(
        user_id,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 31),
    )

    # Assert — monthly salary started in April, but contributes 1000 to May
    assert result.total_income == Decimal("1000")
    assert result.total_expenses == Decimal("0")
    assert result.total_balance == Decimal("1000")


def test_get_expense_distribution(service, mock_repository):
    # Arrange
    user_id = uuid.uuid4()
    cat_id = uuid.uuid4()

    expense_tx = _make_transaction_mock(
        amount=Decimal("100"),
        type_name="gasto",
        tx_date=date(2026, 5, 1),
        category_name="Comida",
        category_id=cat_id,
    )
    mock_repository.get_all_user_transactions_eager.return_value = [expense_tx]

    # Act
    result = service.get_expense_distribution(
        user_id,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 31),
    )

    # Assert
    assert len(result) == 1
    assert result[0].category_name == "Comida"
    assert result[0].percentage == 100.0


def test_get_income_vs_expenses(service, mock_repository):
    # Arrange
    user_id = uuid.uuid4()

    income_tx = _make_transaction_mock(
        amount=Decimal("100"),
        type_name="ingreso",
        tx_date=date(2026, 3, 1),
    )
    expense_tx = _make_transaction_mock(
        amount=Decimal("50"),
        type_name="gasto",
        tx_date=date(2026, 3, 15),
    )
    mock_repository.get_all_user_transactions_eager.return_value = [
        income_tx, expense_tx
    ]

    # Act
    result = service.get_income_vs_expenses(user_id)

    # Assert — new format: parallel arrays with Spanish abbreviated month labels
    assert hasattr(result, "labels")
    assert hasattr(result, "income")
    assert hasattr(result, "expense")
    assert len(result.labels) == 6
    assert len(result.income) == 6
    assert len(result.expense) == 6

    # March should be in the last 6 months; verify its values
    assert "Mar" in result.labels
    march_idx = result.labels.index("Mar")
    assert result.income[march_idx] == Decimal("100")
    assert result.expense[march_idx] == Decimal("50")


def test_get_income_vs_expenses_with_monthly_recurring(service, mock_repository):
    """A monthly transaction started in January should appear in March's data."""
    # Arrange
    user_id = uuid.uuid4()

    monthly_tx = _make_transaction_mock(
        amount=Decimal("1000"),
        type_name="ingreso",
        tx_date=date(2026, 1, 1),
        freq_name="Mensual",
    )
    mock_repository.get_all_user_transactions_eager.return_value = [monthly_tx]

    # Act
    result = service.get_income_vs_expenses(user_id)

    # Assert — new format: parallel arrays; monthly income should appear in March
    assert "Mar" in result.labels, "March should be in the last 6 months"
    march_idx = result.labels.index("Mar")
    assert result.income[march_idx] == Decimal("1000"), (
        f"Expected 1000 income in March, got {result.income[march_idx]}"
    )
