from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.models import (
    Manufacturer,
    MaterialClass,
    MovementReason,
    MovementReasonSign,
    Shade,
    ShadeSystem,
    StockLocation,
    UnitOfMeasure,
    User,
    UserRole,
)
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def ensure_admin_user() -> None:
    username = settings.initial_admin_username
    password = settings.initial_admin_password
    if not username or not password:
        logger.warning("Initial admin credentials not configured; skipping admin bootstrap.")
        return

    with SessionLocal() as db:
        existing = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if existing:
            existing.role = UserRole.ADMIN
            existing.active = True
            db.commit()
            return

        db.add(
            User(
                username=username,
                password_hash=get_password_hash(password),
                role=UserRole.ADMIN,
                active=True,
            )
        )
        db.commit()
        logger.warning("Created initial admin user '%s'.", username)


def ensure_reference_data() -> None:
    with SessionLocal() as db:
        _upsert_code_name_rows(
            db,
            UnitOfMeasure,
            [("disc", "Disc"), ("pcs", "Pieces"), ("ml", "Millilitre"), ("g", "Gram")],
        )
        _upsert_code_name_rows(db, Manufacturer, [("GENERIC", "Generic Manufacturer")])
        _upsert_code_name_rows(
            db,
            MaterialClass,
            [("ZIRCONIA", "Zirconia"), ("PMMA", "PMMA"), ("PEEK", "PEEK")],
        )
        _upsert_code_name_rows(db, StockLocation, [("MAIN", "Main Stock")])
        _upsert_movement_reasons(db)
        _upsert_default_shades(db)
        db.commit()


def _upsert_code_name_rows(db: Session, model, rows: list[tuple[str, str]]) -> None:
    for code, name in rows:
        existing = db.execute(select(model).where(model.code == code)).scalar_one_or_none()
        if existing:
            existing.name = name
            existing.active = True
        else:
            db.add(model(code=code, name=name, active=True))


def _upsert_movement_reasons(db: Session) -> None:
    rows = [
        ("RECEIPT", "Receipt", MovementReasonSign.POSITIVE),
        ("CONSUME", "Consume", MovementReasonSign.NEGATIVE),
        ("ADJUST", "Adjustment", MovementReasonSign.BOTH),
        ("RETURN", "Return", MovementReasonSign.POSITIVE),
        ("SCRAP", "Scrap", MovementReasonSign.NEGATIVE),
        ("TRANSFER", "Transfer", MovementReasonSign.BOTH),
    ]
    for code, name, allowed_sign in rows:
        existing = db.execute(select(MovementReason).where(MovementReason.code == code)).scalar_one_or_none()
        if existing:
            existing.name = name
            existing.allowed_sign = allowed_sign
            existing.active = True
        else:
            db.add(MovementReason(code=code, name=name, allowed_sign=allowed_sign, active=True))


def _upsert_default_shades(db: Session) -> None:
    system = db.execute(select(ShadeSystem).where(ShadeSystem.code == "VITA_CLASSICAL")).scalar_one_or_none()
    if not system:
        system = ShadeSystem(code="VITA_CLASSICAL", name="VITA Classical", active=True)
        db.add(system)
        db.flush()
    else:
        system.name = "VITA Classical"
        system.active = True

    for code in ["A1", "A2", "A3", "B1", "BL2"]:
        shade = db.execute(
            select(Shade).where(Shade.shade_system_id == system.id, Shade.code == code)
        ).scalar_one_or_none()
        if shade:
            shade.name = code
            shade.active = True
        else:
            db.add(Shade(shade_system_id=system.id, code=code, name=code, active=True))
