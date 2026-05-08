from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.db.models import UserRole
from app.schemas.base import ORMBase


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(ORMBase):
    id: int
    username: str
    role: UserRole
    active: bool
    created_at: datetime
    updated_at: datetime
