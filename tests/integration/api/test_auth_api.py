"""
Integration tests for Auth API endpoints.

Tests the full HTTP pipeline (controller → service → mocked DB)
using FastAPI TestClient.

Test cases covered:
    CP-001: Login exitoso → 200
    CP-002: Credenciales incorrectas → 401
    CP-003: Campos vacíos → 422
    CP-005: Registro — validation errors → 422
    CP-009: Logout exitoso → 200
    CP-010: Logout sin token → 403
"""

import os
import uuid
from datetime import datetime
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("JWT_SECRET", "test_jwt_secret_for_testing")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "30")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")

from fastapi.testclient import TestClient

from app.modules.users.entities import User
from app.shared.database import get_db
from app.shared.security.jwt_handler import create_access_token
from app.shared.security.password import hash_password
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
def sample_user():
    """Create a mock User entity with known password."""
    user = MagicMock(spec=User)
    user.user_id = uuid.uuid4()
    user.email = "test@example.com"
    user.password = hash_password("TestPass123!")
    user.first_name = "Test"
    user.last_name = "User"
    user.created_at = datetime.now()
    return user


# -----------------------------------------------------------------------
# Login Endpoint Tests
# -----------------------------------------------------------------------


class TestLoginEndpoint:
    """Integration tests for POST /v1/auth/login."""

    def test_login_success_returns_200(self, client, mock_db, sample_user):
        """CP-001: Valid credentials return 200 with tokens."""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_user
        )

        response = client.post(
            "/v1/auth/login",
            json={"email": "test@example.com", "password": "TestPass123!"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert data["message"] == "Inicio de sesión exitoso"
        assert data["user"]["email"] == "test@example.com"

    def test_login_wrong_password_returns_401(
        self, client, mock_db, sample_user
    ):
        """CP-002: Wrong password returns 401."""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_user
        )

        response = client.post(
            "/v1/auth/login",
            json={"email": "test@example.com", "password": "WrongPassword"},
        )

        assert response.status_code == 401

    def test_login_user_not_found_returns_401(self, client, mock_db):
        """CP-002: Non-existent user returns 401."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        response = client.post(
            "/v1/auth/login",
            json={"email": "noexist@example.com", "password": "TestPass123!"},
        )

        assert response.status_code == 401

    def test_login_invalid_email_returns_422(self, client):
        """Invalid email format returns 422 (Pydantic validation)."""
        response = client.post(
            "/v1/auth/login",
            json={"email": "not-an-email", "password": "TestPass123!"},
        )

        assert response.status_code == 422

    def test_login_missing_fields_returns_422(self, client):
        """CP-003: Missing fields return 422."""
        response = client.post("/v1/auth/login", json={})

        assert response.status_code == 422

    def test_login_empty_password_returns_422(self, client):
        """CP-003: Empty password returns 422."""
        response = client.post(
            "/v1/auth/login",
            json={"email": "test@example.com", "password": ""},
        )

        assert response.status_code == 422


# -----------------------------------------------------------------------
# Register Endpoint Tests (validation-focused)
# -----------------------------------------------------------------------


class TestRegisterEndpoint:
    """Integration tests for POST /v1/auth/register."""

    @pytest.fixture
    def valid_register_data(self):
        """Provide valid registration JSON payload."""
        return {
            "first_name": "Carlos",
            "last_name": "Lopez",
            "email": "carlos@example.com",
            "password": "Passw0rd",
            "birth_date": "1995-05-25",
            "income_type": str(uuid.uuid4()),
            "monthly_income": 950750,
            "monthly_expenses": 450120,
            "topics": [str(uuid.uuid4()), str(uuid.uuid4())],
        }

    def test_register_short_password_returns_422(
        self, client, valid_register_data
    ):
        """Password < 6 chars returns 422."""
        valid_register_data["password"] = "12345"
        response = client.post(
            "/v1/auth/register", json=valid_register_data
        )
        assert response.status_code == 422

    def test_register_invalid_age_returns_422(
        self, client, valid_register_data
    ):
        """CP-007: Age outside 18-50 returns 422."""
        valid_register_data["birth_date"] = "2015-05-25"
        response = client.post(
            "/v1/auth/register", json=valid_register_data
        )
        assert response.status_code == 422

    def test_register_low_income_returns_422(
        self, client, valid_register_data
    ):
        """Income <= 5000 returns 422."""
        valid_register_data["monthly_income"] = 3000
        response = client.post(
            "/v1/auth/register", json=valid_register_data
        )
        assert response.status_code == 422

    def test_register_no_topics_returns_422(
        self, client, valid_register_data
    ):
        """Empty topics list returns 422."""
        valid_register_data["topics"] = []
        response = client.post(
            "/v1/auth/register", json=valid_register_data
        )
        assert response.status_code == 422

    def test_register_invalid_email_returns_422(
        self, client, valid_register_data
    ):
        """Invalid email format returns 422."""
        valid_register_data["email"] = "not-an-email"
        response = client.post(
            "/v1/auth/register", json=valid_register_data
        )
        assert response.status_code == 422

    def test_register_missing_fields_returns_422(self, client):
        """CP-008: Missing required fields return 422."""
        response = client.post("/v1/auth/register", json={})
        assert response.status_code == 422


# -----------------------------------------------------------------------
# Logout Endpoint Tests
# -----------------------------------------------------------------------


class TestLogoutEndpoint:
    """Integration tests for POST /v1/auth/logout."""

    def test_logout_success_returns_200(self, client):
        """CP-009: Valid token logout returns 200."""
        token, _, _ = create_access_token("test-id", "test@example.com")

        response = client.post(
            "/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Cierre de sesión exitoso"

    def test_logout_without_token_returns_401(self, client):
        """CP-010: Request without Authorization header returns 401."""
        response = client.post("/v1/auth/logout")

        assert response.status_code == 401

    def test_logout_invalid_token_returns_401(self, client):
        """Invalid JWT string returns 401."""
        response = client.post(
            "/v1/auth/logout",
            headers={"Authorization": "Bearer invalid-jwt-token"},
        )

        assert response.status_code == 401


# -----------------------------------------------------------------------
# Verify Email Endpoint Tests
# -----------------------------------------------------------------------


class TestVerifyEmailEndpoint:
    """Integration tests for POST /v1/auth/verify-email."""

    def test_verify_email_exists_returns_200(self, client, mock_db, sample_user):
        """Should return 200 with exists=True."""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_user
        )

        response = client.post(
            "/v1/auth/verify-email",
            json={"email": "test@example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is True
        assert data["message"] == "El correo ya se encuentra registrado"

    def test_verify_email_not_exists_returns_200(self, client, mock_db):
        """Should return 200 with exists=False."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        response = client.post(
            "/v1/auth/verify-email",
            json={"email": "new@example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is False
        assert data["message"] == "El correo está disponible"

    def test_verify_email_invalid_format_returns_422(self, client):
        """Should return 422 for invalid email format."""
        response = client.post(
            "/v1/auth/verify-email",
            json={"email": "not-an-email"},
        )

        assert response.status_code == 422


# -----------------------------------------------------------------------
# Health Check
# -----------------------------------------------------------------------


class TestHealthCheck:
    """Smoke test for the health endpoint."""

    def test_health_returns_200(self, client):
        """Health check endpoint must return 200."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
