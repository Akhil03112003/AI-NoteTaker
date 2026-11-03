"""Synchronous SQLAlchemy engine and per-request sessions."""

from __future__ import annotations

from collections.abc import Generator

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import ConfigurationError


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str) -> Engine:
    try:
        url = make_url(database_url)
        if url.get_backend_name() != "postgresql" or url.get_driver_name() != "psycopg":
            raise ConfigurationError("DATABASE_URL must use PostgreSQL with psycopg; value omitted.")
        return create_engine(url, pool_pre_ping=True)
    except ConfigurationError:
        raise
    except Exception as exc:
        raise ConfigurationError(
            f"Cannot configure the PostgreSQL engine ({type(exc).__name__}); URL omitted."
        ) from None


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db(request: Request) -> Generator[Session, None, None]:
    factory: sessionmaker[Session] = request.app.state.session_factory
    session = factory()
    try:
        yield session
    finally:
        session.close()
