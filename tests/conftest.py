import sys, os
import warnings
from unittest.mock import patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from alembic.command import upgrade
from alembic.config import Config
from decouple import config as decouple_config

 
warnings.filterwarnings("ignore", category=DeprecationWarning)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Get the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@pytest.fixture(scope='module')
def mock_send_email():
    with patch("api.core.dependencies.email_sender.send_email") as mock_email_sending:
        with patch("fastapi.BackgroundTasks.add_task") as add_task_mock:
            add_task_mock.side_effect = lambda func, *args, **kwargs: func(*args, **kwargs)
            
            yield mock_email_sending


@pytest.fixture(scope="session")
def db_engine():
    """
    Create a PostgreSQL test database engine.

    This uses a dedicated test database. Make sure the database exists
    and the user has permissions to create/drop tables.
    """
    # Use environment variables or a fixed test database URL
    # You can also use TEST_DATABASE_URL environment variable if available
    db_url = decouple_config('DB_URL')

    engine = create_engine(db_url)
    yield engine

    # Optional: Drop all tables after all tests are done
    # Uncomment if you want to clean up completely after tests
    # from api.v1.models.base_model import BaseTableModel
    # BaseTableModel.metadata.drop_all(engine)


@pytest.fixture(scope="session")
def apply_migrations(db_engine):
    """Apply all migrations to the test database."""
    # Configure Alembic
    config = Config(os.path.join(project_root, "alembic.ini"))

    # Set the SQLAlchemy URL to the test database
    config.set_main_option("sqlalchemy.url", str(db_engine.url))

    # Run the migrations
    upgrade(config, "head")
    return


@pytest.fixture(scope="function")
def db_session(db_engine, apply_migrations):
    """
    Create a new database session for a test.

    The session is rolled back after each test function.
    """
    # Connect to the database
    connection = db_engine.connect()

    # Begin a transaction
    transaction = connection.begin()

    # Create a session bound to the connection
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    # Rollback the transaction after the test completes
    session.close()
    transaction.rollback()
    connection.close()