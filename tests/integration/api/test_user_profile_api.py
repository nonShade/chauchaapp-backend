"""
Integration tests for Users Profile API endpoints.

Tests the full HTTP pipeline (controller → service → mocked DB)
using FastAPI TestClient.

Test cases covered:
    CP-P01: GET perfil exitoso → 200
    CP-P02: PUT email duplicado → 409
    CP-P03: PUT income_type_id inválido → 400
    CP-P04: PUT tópicos inválidos → 400
    CP-P05: Acceso sin token / token inválido → 401
           + validaciones Pydantic → 422
"""

import os
import uuid
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("JWT_SECRET", "test_jwt_secret_for_testing")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "30")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")

from fastapi.testclient import TestClient

from app.modules.news.entities import NewsTag, UserInterest
from app.modules.users.entities import IncomeType, User
from app.shared.database import get_db
from app.shared.security.jwt_handler import create_access_token
from main import app


@pytest.fixture
def mock_db():
    """Provide a mock database session."""
    session = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    return session


@pytest.fixture
def client(mock_db):
    """Provide a FastAPI TestClient with overridden DB dependency."""
    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def user_id():
    """Return a fixed user UUID."""
    return uuid.uuid4()


@pytest.fixture
def income_type_id():
    """Return a fixed income type UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_user(user_id, income_type_id):
    """Create a mock User entity for tests."""
    user = MagicMock(spec=User)
    user.user_id = user_id
    user.first_name = "Carlos"
    user.last_name = "Lopez"
    user.email = "carlos@example.com"
    user.birth_date = date(1995, 5, 25)
    user.income_type_id = income_type_id
    user.monthly_income = Decimal("950750")
    user.monthly_expenses = Decimal("450120")
    user.created_at = datetime.now()
    return user


@pytest.fixture
def auth_token(user_id):
    """Generate a valid JWT for the sample user."""
    token, _, _ = create_access_token(str(user_id), "carlos@example.com")
    return token


@pytest.fixture
def auth_headers(auth_token):
    """Return Authorization headers for authenticated requests."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def valid_update_payload(income_type_id):
    """Provide a valid PUT /profile JSON payload."""
    return {
        "first_name": "Carlos",
        "last_name": "Lopez",
        "email": "carlos@example.com",
        "birth_date": "1995-05-25",
        "income_type_id": str(income_type_id),
        "monthly_income": 1200000,
        "monthly_expenses": 500000,
        "topics": [str(uuid.uuid4()), str(uuid.uuid4())],
    }


# -----------------------------------------------------------------------
# GET /v1/users/profile
# -----------------------------------------------------------------------


class TestGetProfileEndpoint:
    """Integration tests for GET /v1/users/profile."""

    def test_get_profile_success_returns_200(
        self, client, mock_db, sample_user, auth_headers, user_id
    ):
        """CP-P01: Valid token returns 200 with full profile payload."""
        tag_id_1 = uuid.uuid4()
        tag_id_2 = uuid.uuid4()

        interest_1 = MagicMock(spec=UserInterest)
        interest_1.user_id = user_id
        interest_1.tag_id = tag_id_1

        interest_2 = MagicMock(spec=UserInterest)
        interest_2.user_id = user_id
        interest_2.tag_id = tag_id_2

        # Chained query mocks: first call = auth middleware (get user by user_id)
        # subsequent calls = service repository methods
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        mock_db.query.return_value.filter.return_value.all.return_value = [
            interest_1, interest_2
        ]

        response = client.get("/v1/users/profile", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Carlos"
        assert data["last_name"] == "Lopez"
        assert data["email"] == "carlos@example.com"
        assert data["birth_date"] == "1995-05-25"
        assert "income_type_id" in data
        assert "monthly_income" in data
        assert "monthly_expenses" in data
        assert "topics" in data
        assert isinstance(data["topics"], list)

    def test_get_profile_without_token_returns_401(self, client):
        """CP-P05: Request without Authorization header returns 401."""
        response = client.get("/v1/users/profile")
        assert response.status_code == 401

    def test_get_profile_invalid_token_returns_401(self, client):
        """CP-P05: Invalid JWT returns 401."""
        response = client.get(
            "/v1/users/profile",
            headers={"Authorization": "Bearer not-a-valid-jwt"},
        )
        assert response.status_code == 401


# -----------------------------------------------------------------------
# PUT /v1/users/profile
# -----------------------------------------------------------------------


class TestUpdateProfileEndpoint:
    """Integration tests for PUT /v1/users/profile."""

    def test_update_profile_success_returns_200(
        self,
        client,
        mock_db,
        sample_user,
        auth_headers,
        valid_update_payload,
        income_type_id,
        user_id,
    ):
        """CP-P01: Valid update returns 200 with updated profile."""
        income_type = MagicMock(spec=IncomeType)
        income_type.income_type_id = income_type_id

        tags = [MagicMock(spec=NewsTag), MagicMock(spec=NewsTag)]

        # auth middleware returns user, service also uses user lookup
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        mock_db.query.return_value.filter.return_value.all.return_value = []

        # Patch the repository methods to return valid entities
        income_type_mock = MagicMock()
        income_type_mock.transaction_type_id = uuid.uuid4()

        sueldo_category_mock = MagicMock()
        sueldo_category_mock.transaction_category_id = uuid.uuid4()

        existing_tx_mock = MagicMock()
        existing_tx_mock.amount = Decimal("500000")

        with patch(
            "app.modules.users.repository.UserRepository.get_user_by_id",
            return_value=sample_user,
        ), patch(
            "app.modules.users.repository.UserRepository.get_user_by_email",
            return_value=None,
        ), patch(
            "app.modules.users.repository.UserRepository.get_income_type_by_id",
            return_value=income_type,
        ), patch(
            "app.modules.users.repository.UserRepository.get_tags_by_ids",
            return_value=tags,
        ), patch(
            "app.modules.users.repository.UserRepository.get_interests_by_user_id",
            return_value=[],
        ), patch(
            "app.modules.users.repository.UserRepository.delete_user_interests",
        ), patch(
            "app.modules.users.repository.UserRepository.create_user_interests",
        ), patch(
            "app.modules.users.repository.UserRepository.update_user",
            return_value=sample_user,
        ), patch(
            "app.modules.transactions.repository.TransactionsRepository.get_transaction_type_by_name",
            return_value=income_type_mock,
        ), patch(
            "app.modules.transactions.repository.TransactionsRepository.get_transaction_category_by_name",
            return_value=sueldo_category_mock,
        ), patch(
            "app.modules.transactions.repository.TransactionsRepository.get_transaction_by_user_type_category",
            return_value=existing_tx_mock,
        ):
            response = client.put(
                "/v1/users/profile",
                headers=auth_headers,
                json=valid_update_payload,
            )

        assert response.status_code == 200
        data = response.json()
        assert "first_name" in data
        assert "email" in data

    def test_update_profile_duplicate_email_returns_409(
        self,
        client,
        mock_db,
        sample_user,
        auth_headers,
        valid_update_payload,
    ):
        """CP-P02: Email already in use by another user returns 409."""
        other_user = MagicMock(spec=User)

        mock_db.query.return_value.filter.return_value.first.return_value = sample_user

        new_payload = dict(valid_update_payload)
        new_payload["email"] = "other@example.com"

        with patch(
            "app.modules.users.repository.UserRepository.get_user_by_id",
            return_value=sample_user,
        ), patch(
            "app.modules.users.repository.UserRepository.get_user_by_email",
            return_value=other_user,  # email taken by someone else
        ):
            response = client.put(
                "/v1/users/profile",
                headers=auth_headers,
                json=new_payload,
            )

        assert response.status_code == 409

    def test_update_profile_invalid_income_type_returns_400(
        self,
        client,
        mock_db,
        sample_user,
        auth_headers,
        valid_update_payload,
    ):
        """CP-P03: Non-existent income_type_id returns 400."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user

        with patch(
            "app.modules.users.repository.UserRepository.get_user_by_id",
            return_value=sample_user,
        ), patch(
            "app.modules.users.repository.UserRepository.get_user_by_email",
            return_value=None,
        ), patch(
            "app.modules.users.repository.UserRepository.get_income_type_by_id",
            return_value=None,  # income type not found
        ):
            response = client.put(
                "/v1/users/profile",
                headers=auth_headers,
                json=valid_update_payload,
            )

        assert response.status_code == 400

    def test_update_profile_invalid_topics_returns_400(
        self,
        client,
        mock_db,
        sample_user,
        auth_headers,
        valid_update_payload,
        income_type_id,
    ):
        """CP-P04: Topic UUID not found in database returns 400."""
        income_type = MagicMock(spec=IncomeType)
        income_type.income_type_id = income_type_id

        mock_db.query.return_value.filter.return_value.first.return_value = sample_user

        with patch(
            "app.modules.users.repository.UserRepository.get_user_by_id",
            return_value=sample_user,
        ), patch(
            "app.modules.users.repository.UserRepository.get_user_by_email",
            return_value=None,
        ), patch(
            "app.modules.users.repository.UserRepository.get_income_type_by_id",
            return_value=income_type,
        ), patch(
            "app.modules.users.repository.UserRepository.get_tags_by_ids",
            return_value=[MagicMock(spec=NewsTag)],  # only 1 found, 2 requested
        ):
            response = client.put(
                "/v1/users/profile",
                headers=auth_headers,
                json=valid_update_payload,
            )

        assert response.status_code == 400

    def test_update_profile_negative_income_returns_422(
        self, client, auth_headers, valid_update_payload, mock_db, sample_user
    ):
        """Pydantic validation: negative monthly_income returns 422."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user

        payload = dict(valid_update_payload)
        payload["monthly_income"] = -1

        response = client.put(
            "/v1/users/profile",
            headers=auth_headers,
            json=payload,
        )
        assert response.status_code == 422

    def test_update_profile_invalid_age_returns_422(
        self, client, auth_headers, valid_update_payload, mock_db, sample_user
    ):
        """Pydantic validation: birth_date outside 18-50 range returns 422."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user

        payload = dict(valid_update_payload)
        payload["birth_date"] = "2015-01-01"  # too young

        response = client.put(
            "/v1/users/profile",
            headers=auth_headers,
            json=payload,
        )
        assert response.status_code == 422

    def test_update_profile_without_token_returns_401(
        self, client, valid_update_payload
    ):
        """CP-P05: Request without Authorization header returns 401."""
        response = client.put("/v1/users/profile", json=valid_update_payload)
        assert response.status_code == 401

    def test_update_profile_invalid_token_returns_401(
        self, client, valid_update_payload
    ):
        """CP-P05: Invalid JWT returns 401."""
        response = client.put(
            "/v1/users/profile",
            headers={"Authorization": "Bearer invalid-jwt-token"},
            json=valid_update_payload,
        )
        assert response.status_code == 401

    def test_update_profile_missing_fields_returns_422(
        self, client, auth_headers, mock_db, sample_user
    ):
        """Missing required fields in request body returns 422."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user

        response = client.put("/v1/users/profile", headers=auth_headers, json={})
        assert response.status_code == 422
