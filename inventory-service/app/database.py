"""Lidhja me inventory_db — bazë e ndarë nga ajo e porosive (database-per-service)."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://inventory_user:inventory_pass@localhost:5434/inventory_db",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency e FastAPI-t: hap një sesion dhe e mbyll gjithmonë në fund."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
