"""Lidhja me orders_db.

pool_pre_ping verifikon lidhjen para përdorimit, që një lidhje e vjetruar pas
rindezjes së bazës të mos e rrëzojë kërkesën e parë.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://orders_user:orders_pass@localhost:5433/orders_db",
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
