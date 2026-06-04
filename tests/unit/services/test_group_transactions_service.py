from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock
import uuid

import pytest

from app.modules.groups.entities import FamilyGroup, GroupMember
from app.modules.groups.repository import GroupsRepository
from app.modules.transactions.entities import Transaction
from app.modules.transactions.repository import TransactionsRepository
from app.modules.transactions.service import TransactionsService
from app.modules.users.entities import User
from app.modules.users.repository import UserRepository
from app.shared.exceptions import NotFoundException


@pytest.fixture
def mock_repository():
    return MagicMock(spec=TransactionsRepository)


@pytest.fixture
def mock_user_repository():
    return MagicMock(spec=UserRepository)


@pytest.fixture
def mock_groups_repository():
    return MagicMock(spec=GroupsRepository)


@pytest.fixture
def service(mock_repository, mock_user_repository, mock_groups_repository):
    return TransactionsService(
        repository=mock_repository,
        user_repository=mock_user_repository,
        groups_repository=mock_groups_repository,
    )


def _make_user_mock(first_name: str, last_name: str) -> MagicMock:
    user = MagicMock(spec=User)
    user.first_name = first_name
    user.last_name = last_name
    return user


def _make_transaction_mock(
    amount: Decimal,
    type_name: str,
    tx_date: date,
    freq_name: str | None = None,
    category_name: str | None = None,
    category_id: uuid.UUID | None = None,
    user: MagicMock | None = None,
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
    tx.user = user

    return tx


def _setup_group_mock(mock_groups_repository, admin_id: uuid.UUID, member_ids: list[uuid.UUID]):
    """Set up the groups repository to return a valid group."""
    group = MagicMock(spec=FamilyGroup)
    group.admin_id = admin_id
    group.members = []
    
    # Setup members list
    for m_id in member_ids:
        member = MagicMock(spec=GroupMember)
        member.user_id = m_id
        group.members.append(member)

    # By default, pretend the requested user is the admin
    mock_groups_repository.get_group_by_admin.return_value = group
    return group


def test_get_group_transactions(service, mock_repository, mock_groups_repository):
    # Arrange
    admin_id = uuid.uuid4()
    member_id = uuid.uuid4()
    _setup_group_mock(mock_groups_repository, admin_id, [member_id])

    user_admin = _make_user_mock("Admin", "User")
    user_member = _make_user_mock("Member", "User")

    tx1 = _make_transaction_mock(
        amount=Decimal("100"),
        type_name="ingreso",
        tx_date=date(2026, 1, 1),
        user=user_admin,
    )
    tx2 = _make_transaction_mock(
        amount=Decimal("50"),
        type_name="gasto",
        tx_date=date(2026, 1, 2),
        user=user_member,
    )
    
    mock_repository.get_all_group_transactions_eager.return_value = [tx1, tx2]

    # Act
    result = service.get_group_transactions(admin_id, page=1, limit=10)

    # Assert
    assert result.meta.totalItems == 2
    assert len(result.data) == 2
    
    # Since they are sorted descending by date, tx2 comes first
    assert result.data[0].amount == Decimal("50")
    assert result.data[0].user_name == "Member User"
    
    assert result.data[1].amount == Decimal("100")
    assert result.data[1].user_name == "Admin User"


def test_get_group_transactions_not_in_group(service, mock_groups_repository):
    # Arrange
    user_id = uuid.uuid4()
    mock_groups_repository.get_group_by_admin.return_value = None
    mock_groups_repository.get_membership.return_value = None

    # Act & Assert
    with pytest.raises(NotFoundException):
        service.get_group_transactions(user_id)


def test_get_group_financial_summary(service, mock_repository, mock_groups_repository):
    # Arrange
    user_id = uuid.uuid4()
    _setup_group_mock(mock_groups_repository, user_id, [])

    income_tx = _make_transaction_mock(
        amount=Decimal("2000"),
        type_name="ingreso",
        tx_date=date(2026, 5, 1),
    )
    expense_tx = _make_transaction_mock(
        amount=Decimal("500"),
        type_name="gasto",
        tx_date=date(2026, 5, 1),
    )
    mock_repository.get_all_group_transactions_eager.return_value = [
        income_tx, expense_tx
    ]

    # Act
    result = service.get_group_financial_summary(
        user_id,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 31),
    )

    # Assert
    assert result.total_income == Decimal("2000")
    assert result.total_expenses == Decimal("500")
    assert result.total_balance == Decimal("1500")


def test_get_group_expense_distribution(service, mock_repository, mock_groups_repository):
    # Arrange
    user_id = uuid.uuid4()
    _setup_group_mock(mock_groups_repository, user_id, [])
    cat_id = uuid.uuid4()

    expense_tx1 = _make_transaction_mock(
        amount=Decimal("150"),
        type_name="gasto",
        tx_date=date(2026, 5, 1),
        category_name="Comida",
        category_id=cat_id,
    )
    expense_tx2 = _make_transaction_mock(
        amount=Decimal("50"),
        type_name="gasto",
        tx_date=date(2026, 5, 1),
        category_name="Comida",
        category_id=cat_id,
    )
    
    mock_repository.get_all_group_transactions_eager.return_value = [expense_tx1, expense_tx2]

    # Act
    result = service.get_group_expense_distribution(
        user_id,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 31),
    )

    # Assert
    assert len(result) == 1
    assert result[0].category_name == "Comida"
    assert result[0].total_amount == Decimal("200")
    assert result[0].percentage == 100.0


def test_get_group_income_vs_expenses(service, mock_repository, mock_groups_repository):
    # Arrange
    user_id = uuid.uuid4()
    _setup_group_mock(mock_groups_repository, user_id, [])

    income_tx = _make_transaction_mock(
        amount=Decimal("300"),
        type_name="ingreso",
        tx_date=date(2026, 3, 1),
    )
    expense_tx = _make_transaction_mock(
        amount=Decimal("100"),
        type_name="gasto",
        tx_date=date(2026, 3, 15),
    )
    mock_repository.get_all_group_transactions_eager.return_value = [
        income_tx, expense_tx
    ]

    # Act
    result = service.get_group_income_vs_expenses(user_id)

    # Assert
    assert hasattr(result, "labels")
    assert hasattr(result, "income")
    assert hasattr(result, "expense")
    assert len(result.labels) == 6
    assert len(result.income) == 6
    assert len(result.expense) == 6

    # March should be in the last 6 months; verify its values
    assert "Mar" in result.labels
    march_idx = result.labels.index("Mar")
    assert result.income[march_idx] == Decimal("300")
    assert result.expense[march_idx] == Decimal("100")
