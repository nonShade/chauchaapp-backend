from datetime import date
from unittest.mock import MagicMock
import uuid

from fastapi.testclient import TestClient

from app.modules.groups.entities import FamilyGroup
from app.modules.transactions.entities import Transaction
from app.shared.security.auth_middleware import get_current_user
from main import app


def _setup_auth_and_group(mock_db, user_id=None):
    if user_id is None:
        user_id = uuid.uuid4()
        
    mock_user = MagicMock()
    mock_user.user_id = user_id
    mock_user.first_name = "Test"
    mock_user.last_name = "User"
    app.dependency_overrides[get_current_user] = lambda: mock_user

    group = MagicMock(spec=FamilyGroup)
    group.admin_id = user_id
    group.members = []
    
    # First query in _get_group_user_ids is get_group_by_admin
    # We'll set up the mock chain to return this group
    mock_db.query.return_value.filter.return_value.first.return_value = group
    
    return user_id, mock_user


def test_list_group_transactions_api(client: TestClient, mock_db: MagicMock):
    user_id, mock_user = _setup_auth_and_group(mock_db)

    tx = Transaction(
        transaction_id=uuid.uuid4(),
        user_id=user_id,
        amount=250.75,
        transaction_date=date(2026, 2, 1),
        transaction_type_id=uuid.uuid4()
    )
    tx.user = mock_user
    tx.transaction_type = MagicMock()
    tx.category = None
    tx.transaction_frequency = None
    
    # We need to mock the eager-load query path for get_all_group_transactions_eager
    # The first query is for the group, the second is for the transactions
    # To handle this, we can use a side_effect or just rely on the fact that 
    # mock_db.query returns a MagicMock that we can chain
    
    # Let's mock the specific repository method instead of the DB session to make it easier
    # Or we can just mock the whole DB chain. We'll mock the DB chain.
    # The transactions query ends with .all()
    mock_db.query.return_value.options.return_value.filter.return_value.all.return_value = [tx]

    response = client.get("/v1/transactions/family-group?page=1&limit=10")
    
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["totalItems"] == 1
    assert len(data["data"]) == 1
    assert str(data["data"][0]["amount"]) == "250.75"
    assert data["data"][0]["user_name"] == "Test User"


def test_get_group_financial_summary_api(client: TestClient, mock_db: MagicMock):
    user_id, _ = _setup_auth_and_group(mock_db)

    # Build mock transactions with proper relationships
    income_tx = MagicMock()
    income_tx.amount = 3000
    income_tx.transaction_date = date.today()
    income_tx.transaction_type = MagicMock()
    income_tx.transaction_type.name = "ingreso"
    income_tx.transaction_frequency = None

    expense_tx = MagicMock()
    expense_tx.amount = 800
    expense_tx.transaction_date = date.today()
    expense_tx.transaction_type = MagicMock()
    expense_tx.transaction_type.name = "gasto"
    expense_tx.transaction_frequency = None

    # Mock the eager-load query path
    mock_db.query.return_value.options.return_value.filter.return_value.all.return_value = [
        income_tx, expense_tx
    ]

    response = client.get("/v1/transactions/family-group/summary")

    assert response.status_code == 200
    data = response.json()
    assert str(data["total_income"]) == "3000"
    assert str(data["total_expenses"]) == "800"
    assert str(data["total_balance"]) == "2200"


def test_get_group_expense_distribution_api(client: TestClient, mock_db: MagicMock):
    user_id, _ = _setup_auth_and_group(mock_db)

    expense_tx = MagicMock()
    expense_tx.amount = 500
    expense_tx.transaction_date = date.today()
    expense_tx.transaction_type = MagicMock()
    expense_tx.transaction_type.name = "gasto"
    expense_tx.transaction_frequency = None
    expense_tx.transaction_category_id = str(uuid.uuid4())
    expense_tx.category = MagicMock()
    expense_tx.category.name = "Transporte"

    mock_db.query.return_value.options.return_value.filter.return_value.all.return_value = [
        expense_tx
    ]

    response = client.get("/v1/transactions/family-group/analytics/distribution")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["category_name"] == "Transporte"
    assert str(data[0]["total_amount"]) == "500"
    assert data[0]["percentage"] == 100.0


def test_get_group_income_vs_expenses_api(client: TestClient, mock_db: MagicMock):
    user_id, _ = _setup_auth_and_group(mock_db)

    income_tx = MagicMock()
    income_tx.amount = 1000
    income_tx.transaction_date = date.today()
    income_tx.transaction_type = MagicMock()
    income_tx.transaction_type.name = "ingreso"
    income_tx.transaction_frequency = None

    mock_db.query.return_value.options.return_value.filter.return_value.all.return_value = [
        income_tx
    ]

    response = client.get("/v1/transactions/family-group/analytics/income-vs-expenses")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["labels"], list)
    assert isinstance(data["income"], list)
    assert isinstance(data["expense"], list)
    assert len(data["labels"]) == 6
