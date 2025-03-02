import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
from uuid_extensions import uuid7


from main import app
from sqlalchemy.orm import Session
from api.v1.services.product_comment import product_comment_service
from api.v1.models import User
from api.utils.dependencies import get_current_user
from api.v1.services.product_comment import ProductCommentService
from api.utils.success_response import success_response


from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session


from api.db.database import get_db
from api.v1.services.user import user_service
from api.v1.models.user import User
from api.v1.models.product import Product, ProductComment
from api.v1.services.product_comment import product_comment_service
from api.v1.services.product import product_service
from main import app
from faker import Faker

fake = Faker()

def mock_get_current_admin():
    return User(
        id=str(uuid7()),
        email="admin@gmail.com",
        password=user_service.hash_password("Testadmin@123"),
        first_name='Admin',
        last_name='User',
        is_active=True,
        is_superadmin=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


def mock_product():
    return Product(
        id=str(uuid7()),
        name=fake.numerify(text='Intel Core i%-%%##K vs AMD Ryzen % %%##X'),
        description=fake.paragraph(),
        price=fake.pydecimal(left_digits=3, right_digits=2, positive=True),
        org_id=str(uuid7()),
        category_id=str(uuid7()),
        quantity=fake.random_int(min=0, max=100),
        image_url=fake.image_url(),
        status=fake.random_element(elements=("in_stock", "out_of_stock", "low_on_stock")),
        archived=fake.boolean(),
        filter_status=fake.random_element(elements=("active", "draft")),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

def mock_product_comment():
    return ProductComment(
        id=str(uuid7()),
        content=fake.paragraph(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

@pytest.fixture
def db_session_mock():
    db_session = MagicMock(spec=Session)
    return db_session

@pytest.fixture
def client(db_session_mock):
    app.dependency_overrides[get_db] = lambda: db_session_mock
    client = TestClient(app)
    yield client
    app.dependency_overrides = {}


def test_fetch_single_product_comment(client, db_session_mock):
    '''Test to successfully fetch a single product comment'''

    # Mock the user service to return the current user
    app.dependency_overrides[user_service.get_current_user] = lambda: mock_get_current_admin()
    app.dependency_overrides[product_service.create] = lambda: mock_product()
    app.dependency_overrides[product_comment_service.create] = lambda: mock_product_comment()
    app.dependency_overrides[product_comment_service.fetch] = lambda: mock_product_comment()

    
    # Mock job update
    db_session_mock.add.return_value = None
    db_session_mock.commit.return_value = None
    db_session_mock.refresh.return_value = None

    mock_product_comment_instance = mock_product_comment()
    mock_product_instance = mock_product()


    with patch("api.v1.services.product_comment.product_comment_service.create", return_value=mock_product_comment_instance) as mock_update:
        response = client.get(
            f"/api/v1/products/{mock_product_instance.id}/comments/{mock_product_comment_instance.id}",
            headers={'Authorization': 'Bearer token'}
        )

        assert response.status_code == 200

        



def test_fetch_all_product_comment(client, db_session_mock):
    '''Test to successfully fetch all product comment'''

    # Mock the user service to return the current user
    app.dependency_overrides[user_service.get_current_user] = lambda: mock_get_current_admin()
    app.dependency_overrides[product_service.create] = lambda: mock_product()
    app.dependency_overrides[product_comment_service.create] = lambda: mock_product_comment()
    app.dependency_overrides[product_comment_service.fetch_all] = lambda: mock_product_comment()

    
    # Mock job update
    db_session_mock.add.return_value = None
    db_session_mock.commit.return_value = None
    db_session_mock.refresh.return_value = None

    mock_product_instance = mock_product()
    
    
    response = client.get(
            f"/api/v1/products/{mock_product_instance.id}/comments",
            headers={'Authorization': 'Bearer token'}
        )

    assert response.status_code == 200
    
    
    
    
# ========= delete a comment of a single product PYTEST TEST =====

# Add these after your existing tests

