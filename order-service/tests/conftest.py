"""Konfigurimi i testeve: baza SQLite në memorie dhe broker i simuluar.

Testet nuk duhet të kërkojnë PostgreSQL as RabbitMQ, ndaj:
  * `get_db` zëvendësohet me një sesion mbi SQLite in-memory (StaticPool, që i
    njëjti lidhje t'u shërbejë të gjitha kërkesave brenda një testi);
  * `publish_event` zëvendësohet me një listë ku mbahen event-et e publikuara,
    kështu që testi verifikon kontratën e event-it pa broker real.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main as app_main
from app.database import Base, get_db

API_KEY = "test-key"


@pytest.fixture()
def engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def published(monkeypatch):
    """Kap event-et e publikuara: lista e (routing_key, payload)."""
    events = []
    monkeypatch.setattr(
        app_main, "publish_event", lambda key, payload: events.append((key, payload))
    )
    return events


@pytest.fixture()
def client(engine, published, monkeypatch):
    monkeypatch.setenv("API_KEY", API_KEY)
    monkeypatch.setattr("app.security.API_KEY", API_KEY, raising=False)

    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app_main.app.dependency_overrides[get_db] = override_get_db
    with TestClient(app_main.app) as client:
        yield client
    app_main.app.dependency_overrides.clear()


@pytest.fixture()
def auth():
    return {"X-API-Key": API_KEY}
