from __future__ import annotations

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, engine, wait_for_db
from app.services.bootstrap import ensure_reference_data


def _truncate_core_tables() -> None:
    table_names = [table.name for table in reversed(Base.metadata.sorted_tables)]
    if not table_names:
        return

    joined = ", ".join(f'"{name}"' for name in table_names)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {joined} RESTART IDENTITY CASCADE"))


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    wait_for_db(settings.db_connect_retries, settings.db_connect_delay)

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(config, "head")

    _truncate_core_tables()
    yield
    _truncate_core_tables()


@pytest.fixture
def db_session(migrated_database: None) -> Session:
    _truncate_core_tables()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        _truncate_core_tables()


@pytest.fixture
def bootstrapped_db(db_session: Session) -> Session:
    ensure_reference_data()
    db_session.expire_all()
    return db_session
