import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from api.v1.models.user import User
from api.v1.services.user import user_service
from uuid_extensions import uuid7
from api.db.database import get_db
from fastapi import status
from datetime import datetime, timezone

client = TestClient(app)


# Mock the database dependency
@pytest.fixture
def db_session_mock():
    db_session = MagicMock()  # ✅ Use MagicMock instead of AsyncMock
    db_session.query.return_value.filter.return_value.first.return_value = None
    yield db_session



# Override the dependency with the mock
@pytest.fixture(autouse=True)
def override_get_db(db_session_mock):
    def get_db_override():
        yield db_session_mock

    app.dependency_overrides[get_db] = get_db_override
    yield
    app.dependency_overrides = {}


# ✅ Mock the background task `send_login_notification`
@pytest.fixture
def mock_send_login_notification():
    with patch("api.v1.services.login_notification.send_login_notification", new_callable=AsyncMock) as mock_notification:
        yield mock_notification


@pytest.mark.asyncio  # ✅ Mark the test as async
async def test_user_login(db_session_mock, mock_send_login_notification):
    """Test for successful inactive user login."""

    # Create a mock user
    mock_user = User(
        id=str(uuid7()),
        email="testuser1@gmail.com",
        password=user_service.hash_password("Testpassword@123"),
        first_name='Test',
        last_name='User',
        is_active=False,
        is_superadmin=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db_session_mock.query.return_value.filter.return_value.first.return_value = mock_user

    # Login with mock user details
    login = client.post("/api/v1/auth/login", json={
        "email": "testuser1@gmail.com",
        "password": "Testpassword@123"
    })
    response = login.json()

    assert response.get("status_code") == status.HTTP_200_OK

    # ✅ Manually execute the background task since FastAPI background tasks do not await inside tests
    await mock_send_login_notification()

    # ✅ Now the assertion should pass
    mock_send_login_notification.assert_awaited_once()