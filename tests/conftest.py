"""
Shared test configuration and fixtures.

Sets up test environment variables BEFORE any app imports
to ensure the test configuration is used.
"""

import os

# Set test environment variables before importing app modules
os.environ["JWT_SECRET"] = "test_jwt_secret_for_testing"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_EXPIRE_MINUTES"] = "30"
os.environ["DATABASE_URL"] = "sqlite:///test.db"
# Prevent DailyTipsAgent from raising ValueError on import (no real API call is made in tests)
os.environ.setdefault("NVIDIA_API_KEY", "test_dummy_key_for_tests")
os.environ.setdefault("TAVILY_API_KEY", "test_dummy_tavily_key_for_tests")

import uuid
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.shared.database import get_db
from app.shared.security.password import hash_password
from app.shared.security.token_blacklist import token_blacklist
from main import app


@pytest.fixture(autouse=True)
def clear_blacklist():
    """Clear the token blacklist between tests."""
    token_blacklist.clear()
    yield
    token_blacklist.clear()


@pytest.fixture
def mock_db():
    """Provide a mock database session."""
    session = MagicMock()
    return session


@pytest.fixture
def client(mock_db):
    """Provide a FastAPI TestClient with mocked DB dependency."""
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
def sample_user_password():
    """Return the plain-text test password."""
    return "TestPass123!"


@pytest.fixture
def sample_user(sample_user_password):
    """Create a mock User entity with hashed password."""
    from app.modules.users.entities import User

    user = MagicMock(spec=User)
    user.user_id = uuid.uuid4()
    user.email = "test@example.com"
    user.password = hash_password(sample_user_password)
    user.first_name = "Test"
    user.last_name = "User"
    user.created_at = datetime.now()
    return user
