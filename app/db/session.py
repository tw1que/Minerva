from __future__ import annotations

import logging
import time

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

logger = logging.getLogger(__name__)


def wait_for_db(retries: int, delay: float) -> None:
    attempts = max(1, retries)
    last_exc: OperationalError | None = None

    for attempt in range(1, attempts + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except OperationalError as exc:
            last_exc = exc
            logger.warning(
                "Database not ready (attempt %s/%s). Retrying in %.1fs",
                attempt,
                attempts,
                delay,
            )
            time.sleep(delay)

    if last_exc:
        raise last_exc
