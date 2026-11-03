"""Verify configured PostgreSQL endpoints without printing DSNs or credentials."""

from __future__ import annotations

import sys

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import ConfigurationError, get_settings
from app.database import make_engine


def verify(label: str, database_url: str) -> bool:
    engine = make_engine(database_url)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print(f"{label}: SUCCESS")
        return True
    except SQLAlchemyError as exc:
        print(f"{label}: FAILED ({type(exc).__name__}); connection details omitted")
        return False
    finally:
        engine.dispose()


def main() -> int:
    try:
        settings = get_settings()
    except ConfigurationError as exc:
        print(f"Configuration: FAILED ({exc})")
        return 1

    if settings.test_database_url is None:
        print("Test database: FAILED (TEST_DATABASE_URL is missing; value omitted)")
        return 1

    dev_ok = verify("Development database", settings.database_url.get_secret_value())
    test_ok = verify("Test database", settings.test_database_url.get_secret_value())
    return 0 if dev_ok and test_ok else 1


if __name__ == "__main__":
    sys.exit(main())
