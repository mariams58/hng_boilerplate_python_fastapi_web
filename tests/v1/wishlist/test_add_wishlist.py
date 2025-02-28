import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from api.v1.services.wishlist import wishlist_service
from api.v1.services.user import user_service
from fastapi import HTTPException


@pytest.fixture
def client():
	return TestClient(app)


def mock_current_user():
	return MagicMock(id="test-user-id")


class TestAddToWishlist:
	@classmethod
	def setup_class(cls):
		app.dependency_overrides[user_service.get_current_user] = mock_current_user

	@classmethod
	def teardown_class(cls):
		app.dependency_overrides = {}

	
	@patch('api.v1.services.wishlist.wishlist_service.create')
	def test_add_to_wishlist_success(self, mock_create, client):
		mock_create.return_value = {"id":"wishlist-id", "user_id":"test-user-id", "product_id":"test-product-id"}

		response = client.post("/api/v1/wishlist/", json={"product_id": "test-product-id"})

		assert response.status_code == 201
		assert response.json()["message"] == "Product added to waitlist successfully"

	
	@patch('api.v1.services.wishlist.wishlist_service.create')
	def test_add_to_wishlist_product_not_found(self, mock_create, client):
		mock_create.side_effect = HTTPException(status_code=404, detail="Product not found")
		
		response = client.post("/api/v1/wishlist/", json={"product_id": "invalid-product-id"})
		
		assert response.status_code == 404


	@patch('api.v1.services.wishlist.wishlist_service.create')
	def test_add_to_wishlist_already_exists(self, mock_create, client):
		mock_create.side_effect = HTTPException(status_code=400, detail="Product already in wishlist")
		
		response = client.post("/api/v1/wishlist/", json={"product_id": "test-product-id"})
		
		assert response.status_code == 400