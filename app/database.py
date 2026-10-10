# app/database.py
# Sets up the SQLAlchemy engine, session factory, and a Base class.
# All models inherit from Base so SQLAlchemy can create/manage their tables.

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings

# create_engine connects SQLAlchemy to the database.
# The URL comes from .env — never hardcoded.
#
# check_same_thread=False is required for SQLite: FastAPI's dependency injection
# can serve one request across multiple threads, which SQLite blocks by default.
# This flag is only passed for SQLite URLs; other databases ignore it.
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)

# SessionLocal is a factory for database sessions.
# autocommit=False means we control when to commit transactions.
# autoflush=False means SQLAlchemy won't automatically flush changes before queries.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is the parent class for all our models.
# SQLAlchemy uses it to track which classes are tables.
Base = declarative_base()


def get_db():
    """
    Dependency function used by FastAPI endpoints.
    Yields a database session and ensures it is closed after the request,
    even if an error occurs.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
