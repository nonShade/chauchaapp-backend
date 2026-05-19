from datetime import date
from unittest.mock import MagicMock
import uuid

from fastapi.testclient import TestClient

from app.modules.transactions.entities import (
    Transaction,
    TransactionCategory,
    TransactionFrequency,
    TransactionType,
)
from app.shared.security.auth_middleware import get_current_user
from main import app


def test_get_transaction_types(client: TestClient, mock_db: MagicMock):
    fake_id = uuid.uuid4()
    fake_type = TransactionType(transaction_type_id=fake_id, name="ingreso", description="Ingreso desc")
    mock_db.query.return_value.all.return_value = [fake_type]
    
    response = client.get("/v1/transactions/types")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == str(fake_id)
    assert data[0]["name"] == "ingreso"
    assert data[0]["description"] == "Ingreso desc"


def test_get_transaction_frequencies(client: TestClient, mock_db: MagicMock):
    fake_id = uuid.uuid4()
    fake_freq = TransactionFrequency(transaction_frequency_id=fake_id, name="mensual", description="Mensual desc")
    mock_db.query.return_value.all.return_value = [fake_freq]

    response = client.get("/v1/transactions/frequencies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == str(fake_id)
    assert data[0]["name"] == "mensual"
    assert data[0]["description"] == "Mensual desc"


def test_get_transaction_categories(client: TestClient, mock_db: MagicMock):
    fake_cat_id = uuid.uuid4()
    fake_type_id = uuid.uuid4()
    fake_cat = TransactionCategory(
        transaction_category_id=fake_cat_id,
        name="salud",
        description="Gastos medicos",
        transaction_type_id=fake_type_id,
    )
    mock_db.query.return_value.all.return_value = [fake_cat]

    response = client.get("/v1/transactions/categories")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == str(fake_cat_id)
    assert data[0]["name"] == "salud"
    assert data[0]["description"] == "Gastos medicos"
    assert data[0]["transaction_type_id"] == str(fake_type_id)


def test_create_transaction_api(client: TestClient, mock_db: MagicMock):
    user_id = uuid.uuid4()
    mock_user = MagicMock()
    mock_user.user_id = user_id
    app.dependency_overrides[get_current_user] = lambda: mock_user

    type_id = uuid.uuid4()
    payload = {
        "amount": 5000,
        "transaction_type_id": str(type_id),
        "transaction_date": "2026-04-29",
        "description": "Test transaction"
    }

    # Mock the save operation
    def mock_save(t):
        t.transaction_id = uuid.uuid4()
        return t
    
    mock_db.add = MagicMock()
    mock_db.commit = MagicMock()
    mock_db.refresh = MagicMock(side_effect=mock_save)

    response = client.post("/v1/transactions", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert str(data["amount"]) == "5000"
    assert data["description"] == "Test transaction"


def test_list_transactions_api(client: TestClient, mock_db: MagicMock):
    user_id = uuid.uuid4()
    mock_user = MagicMock()
    mock_user.user_id = user_id
    app.dependency_overrides[get_current_user] = lambda: mock_user

    tx = Transaction(
        transaction_id=uuid.uuid4(),
        user_id=user_id,
        amount=100.50,
        transaction_date=date(2026, 1, 1),
        transaction_type_id=uuid.uuid4()
    )
    
    # Mock the eager-load query path
    mock_db.query.return_value.options.return_value.filter.return_value.all.return_value = [tx]

    response = client.get("/v1/transactions/individual?page=1&limit=10")
    
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["totalItems"] == 1
    assert len(data["data"]) == 1
    assert str(data["data"][0]["amount"]) == "100.5"


def test_get_financial_summary_api(client: TestClient, mock_db: MagicMock):
    user_id = uuid.uuid4()
    mock_user = MagicMock()
    mock_user.user_id = user_id
    app.dependency_overrides[get_current_user] = lambda: mock_user

    # Build mock transactions with proper relationships
    income_tx = MagicMock()
    income_tx.amount = 1000
    income_tx.transaction_date = date.today()
    income_tx.transaction_type = MagicMock()
    income_tx.transaction_type.name = "ingreso"
    income_tx.transaction_frequency = None

    expense_tx = MagicMock()
    expense_tx.amount = 400
    expense_tx.transaction_date = date.today()
    expense_tx.transaction_type = MagicMock()
    expense_tx.transaction_type.name = "gasto"
    expense_tx.transaction_frequency = None

    # Mock the eager-load query path
    mock_db.query.return_value.options.return_value.filter.return_value.all.return_value = [
        income_tx, expense_tx
    ]

    response = client.get("/v1/transactions/summary")

    assert response.status_code == 200
    data = response.json()
    assert str(data["total_income"]) == "1000"
    assert str(data["total_expenses"]) == "400"
    assert str(data["total_balance"]) == "600"
