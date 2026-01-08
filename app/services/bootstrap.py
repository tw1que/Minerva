from __future__ import annotations

import logging

from sqlalchemy import select

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.models import User, UserRole
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def ensure_admin_user() -> None:
    username = settings.initial_admin_username
    password = settings.initial_admin_password

    if not username or not password:
        logger.warning("Initial admin credentials not configured; skipping.")
        return

    with SessionLocal() as db:
        existing = db.execute(select(User.id)).first()
        if existing:
            return

        user = User(
            username=username,
            password_hash=get_password_hash(password),
            role=UserRole.ADMIN,
            active=True,
        )
        db.add(user)
        db.commit()
        logger.warning("Created initial admin user '%s'.", username)
