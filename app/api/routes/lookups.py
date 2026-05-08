from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.db.models import (
    Manufacturer,
    MaterialClass,
    MovementReason,
    Shade,
    ShadeSystem,
    StockLocation,
    UnitOfMeasure,
    User,
    UserRole,
)
from app.schemas.lookups import LookupRead, MovementReasonRead, ShadeRead


router = APIRouter(prefix="/lookups")


@router.get("/manufacturers", response_model=list[LookupRead])
def list_manufacturers(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER)),
):
    return list(db.execute(select(Manufacturer).order_by(Manufacturer.code)).scalars())


@router.get("/shade-systems", response_model=list[LookupRead])
def list_shade_systems(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER)),
):
    return list(db.execute(select(ShadeSystem).order_by(ShadeSystem.code)).scalars())


@router.get("/shades", response_model=list[ShadeRead])
def list_shades(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER)),
):
    return list(db.execute(select(Shade).order_by(Shade.code)).scalars())


@router.get("/material-classes", response_model=list[LookupRead])
def list_material_classes(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER)),
):
    return list(db.execute(select(MaterialClass).order_by(MaterialClass.code)).scalars())


@router.get("/units", response_model=list[LookupRead])
def list_units(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER)),
):
    return list(db.execute(select(UnitOfMeasure).order_by(UnitOfMeasure.code)).scalars())


@router.get("/stock-locations", response_model=list[LookupRead])
def list_stock_locations(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER)),
):
    return list(db.execute(select(StockLocation).order_by(StockLocation.code)).scalars())


@router.get("/movement-reasons", response_model=list[MovementReasonRead])
def list_movement_reasons(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER)),
):
    return list(db.execute(select(MovementReason).order_by(MovementReason.code)).scalars())
