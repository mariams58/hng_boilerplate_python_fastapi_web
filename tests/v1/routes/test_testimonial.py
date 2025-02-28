from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from api.v1.models.testimonial import Testimonial
from api.v1.models.user import User
import pytest
from datetime import datetime

# Mock data
MOCK_USER_ID = "067c0f12-1fd3-736d-8000-13328adefbd5"
MOCK_TESTIMONIAL_ID = "067c0f12-20a5-77d9-8000-e83895bcbbb9"

@pytest.fixture
def mock_db():
    return Mock(spec=Session)

@pytest.fixture
def mock_current_user():
    return User(
        id=MOCK_USER_ID,
        email="test@example.com",
        first_name="Test",
        last_name="User",
        is_active=True
    )

@pytest.fixture
def mock_testimonial():
    return Testimonial(
        id=MOCK_TESTIMONIAL_ID,
        author_id=MOCK_USER_ID,
        content="Test testimonial",
        created_at=datetime.now(),
        ratings=4.5
    )

class TestTestimonialRoutes:
    
    def test_get_user_testimonials_success(self, client: TestClient, mock_db, mock_current_user, mock_testimonial):
        """Test successful retrieval of user testimonials"""
        # Mock the authentication
        with patch('api.v1.services.user.user_service.get_current_user', return_value=mock_current_user):
            # Mock the paginated response
            mock_response = {
                "data": {
                    "items": [{
                        "id": mock_testimonial.id,
                        "author_id": mock_testimonial.author_id,
                        "content": mock_testimonial.content,
                        "created_at": mock_testimonial.created_at.isoformat()
                    }],
                    "total": 1
                }
            }
            
            with patch('api.utils.pagination.paginated_response', return_value=Mock(body=json.dumps(mock_response))):
                response = client.get(f"/api/v1/testimonials/user/{MOCK_USER_ID}")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status_code"] == 200
                assert data["total_testimonials"] == 1
                assert len(data["testimonials"]) == 1
                assert data["testimonials"][0]["user_id"] == MOCK_USER_ID
                assert data["testimonials"][0]["message"] == mock_testimonial.content

    def test_get_user_testimonials_empty(self, client: TestClient, mock_db, mock_current_user):
        """Test when user has no testimonials"""
        with patch('api.v1.services.user.user_service.get_current_user', return_value=mock_current_user):
            mock_response = {
                "data": {
                    "items": [],
                    "total": 0
                }
            }
            
            with patch('api.utils.pagination.paginated_response', return_value=Mock(body=json.dumps(mock_response))):
                response = client.get(f"/api/v1/testimonials/user/{MOCK_USER_ID}")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status_code"] == 200
                assert data["total_testimonials"] == 0
                assert data["testimonials"] == []

    def test_get_user_testimonials_unauthorized(self, client: TestClient):
        """Test unauthorized access"""
        response = client.get(f"/api/v1/testimonials/user/{MOCK_USER_ID}")
        assert response.status_code == 401
        data = response.json()
        assert data["status_code"] == 401
        assert data["message"] == "Not authorized"

    def test_get_user_testimonials_server_error(self, client: TestClient, mock_db, mock_current_user):
        """Test server error handling"""
        with patch('api.v1.services.user.user_service.get_current_user', return_value=mock_current_user):
            with patch('api.utils.pagination.paginated_response', side_effect=Exception("Database error")):
                response = client.get(f"/api/v1/testimonials/user/{MOCK_USER_ID}")
                
                assert response.status_code == 500
                data = response.json()
                assert data["status_code"] == 500
                assert data["message"] == "An unexpected error occurred."

    def test_get_user_testimonials_pagination(self, client: TestClient, mock_db, mock_current_user, mock_testimonial):
        """Test pagination of testimonials"""
        with patch('api.v1.services.user.user_service.get_current_user', return_value=mock_current_user):
            # Create mock response with multiple items
            mock_response = {
                "data": {
                    "items": [
                        {
                            "id": f"{mock_testimonial.id}_{i}",
                            "author_id": mock_testimonial.author_id,
                            "content": f"Testimonial {i}",
                            "created_at": mock_testimonial.created_at.isoformat()
                        }
                        for i in range(3)
                    ],
                    "total": 3
                }
            }
            
            with patch('api.utils.pagination.paginated_response', return_value=Mock(body=json.dumps(mock_response))):
                # Test with different page sizes
                response = client.get(f"/api/v1/testimonials/user/{MOCK_USER_ID}?page_size=2&page=1")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status_code"] == 200
                assert data["total_testimonials"] == 3
                assert len(data["testimonials"]) == 3 