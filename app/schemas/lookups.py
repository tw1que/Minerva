from __future__ import annotations

from app.db.models import MovementReasonSign
from app.schemas.base import ORMBase


class LookupRead(ORMBase):
    id: int
    code: str
    name: str
    active: bool


class ShadeRead(LookupRead):
    shade_system_id: int


class MovementReasonRead(LookupRead):
    allowed_sign: MovementReasonSign
