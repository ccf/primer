import secrets

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from primer.common.config import settings
from primer.common.database import Base, get_db
from primer.common.models import Engineer, Team
from primer.server.app import create_app

TEST_DB_URL = "sqlite:///./test_primer.db"


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    import contextlib
    import os

    with contextlib.suppress(FileNotFoundError):
        os.remove("test_primer.db")


@pytest.fixture
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    testing_session = sessionmaker(bind=connection)
    session = testing_session()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    app = create_app()

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


@pytest.fixture
def admin_headers():
    return {"x-admin-key": settings.admin_api_key}


@pytest.fixture
def engineer_with_key(db_session):
    """Create an engineer and return (engineer, raw_api_key)."""
    raw_key = f"primer_{secrets.token_urlsafe(32)}"
    hashed = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()
    team = Team(name="Test Team")
    db_session.add(team)
    db_session.flush()
    eng = Engineer(
        name="Test Engineer", email="test@example.com", team_id=team.id, api_key_hash=hashed
    )
    db_session.add(eng)
    db_session.flush()
    return eng, raw_key
