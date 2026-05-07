from __future__ import annotations

import logging

from sqlalchemy import select

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.models import (
    MaterialClass,
    MovementReason,
    MovementReasonSign,
    Shade,
    ShadeSystem,
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


def ensure_reference_data() -> None:
    with SessionLocal() as db:
        _ensure_units(db)
        _ensure_movement_reasons(db)
        _ensure_shades(db)
        _ensure_material_classes(db)
        db.commit()


def _ensure_units(db) -> None:
    units = [
        ("pcs", "Pieces"),
        ("disc", "Disc"),
        ("ml", "Millilitre"),
        ("g", "Gram"),
    ]
    for code, name in units:
        existing = db.execute(select(UnitOfMeasure).where(UnitOfMeasure.code == code)).scalar_one_or_none()
        if existing:
            existing.name = name
            existing.active = True
        else:
            db.add(UnitOfMeasure(code=code, name=name, active=True))


def _ensure_movement_reasons(db) -> None:
    reasons = [
        ("RECEIPT", "receipt", MovementReasonSign.POSITIVE),
        ("CONSUME", "consume", MovementReasonSign.NEGATIVE),
        ("ADJUST", "adjustment", MovementReasonSign.BOTH),
        ("RETURN", "return", MovementReasonSign.POSITIVE),
        ("SCRAP", "scrap", MovementReasonSign.NEGATIVE),
        ("TRANSFER", "transfer", MovementReasonSign.BOTH),
    ]
    for code, name, allowed_sign in reasons:
        existing = db.execute(select(MovementReason).where(MovementReason.code == code)).scalar_one_or_none()
        if existing:
            existing.name = name
            existing.allowed_sign = allowed_sign
            existing.active = True
        else:
            db.add(MovementReason(code=code, name=name, allowed_sign=allowed_sign, active=True))


def _ensure_shades(db) -> None:
    systems = {
        "VITA Classical": ["A1", "A2", "A3", "B1", "BL2"],
        "VITA 3D-Master": ["2M2"],
    }
    for system_name, shade_codes in systems.items():
        system = db.execute(
            select(ShadeSystem).where(ShadeSystem.name == system_name)
        ).scalar_one_or_none()
        if not system:
            system = ShadeSystem(name=system_name, active=True)
            db.add(system)
            db.flush()
        else:
            system.active = True
        for code in shade_codes:
            shade = db.execute(
                select(Shade).where(
                    Shade.shade_system_id == system.id,
                    Shade.code == code,
                )
            ).scalar_one_or_none()
            if shade:
                shade.active = True
            else:
                db.add(Shade(shade_system_id=system.id, code=code, active=True))


def _ensure_material_classes(db) -> None:
    classes = [
        ("PMMA", "PMMA"),
        ("ZIRCONIA", "Zirconia"),
        ("PEEK", "PEEK"),
        ("COMPOSITE", "Composite"),
    ]
    for code, name in classes:
        existing = db.execute(select(MaterialClass).where(MaterialClass.code == code)).scalar_one_or_none()
        if existing:
            existing.name = name
            existing.active = True
        else:
            db.add(MaterialClass(code=code, name=name, active=True))
