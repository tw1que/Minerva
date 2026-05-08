from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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
from app.schemas.lookups import (
    ManufacturerCreate,
    ManufacturerRead,
    MaterialClassCreate,
    MaterialClassRead,
    MovementReasonCreate,
    MovementReasonRead,
    ShadeCreate,
    ShadeRead,
    ShadeSystemCreate,
    ShadeSystemRead,
    StockLocationCreate,
    StockLocationRead,
    UnitOfMeasureCreate,
    UnitOfMeasureRead,
)


router = APIRouter(prefix="/lookups")


def _create_lookup(db: Session, instance, duplicate_message: str):
    db.add(instance)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=duplicate_message) from exc
    db.refresh(instance)
    return instance


@router.get("/manufacturers", response_model=list[ManufacturerRead])
def list_manufacturers(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER)),
):
    return list(db.execute(select(Manufacturer).order_by(Manufacturer.code)).scalars())


@router.post("/manufacturers", response_model=ManufacturerRead, status_code=status.HTTP_201_CREATED)
def create_manufacturer(
    payload: ManufacturerCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    return _create_lookup(
        db,
        Manufacturer(code=payload.code.strip(), name=payload.name.strip()),
        "Manufacturer code already exists.",
    )


@router.get("/shade-systems", response_model=list[ShadeSystemRead])
def list_shade_systems(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER)),
):
    return list(db.execute(select(ShadeSystem).order_by(ShadeSystem.code)).scalars())


@router.post("/shade-systems", response_model=ShadeSystemRead, status_code=status.HTTP_201_CREATED)
def create_shade_system(
    payload: ShadeSystemCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    return _create_lookup(
        db,
        ShadeSystem(code=payload.code.strip(), name=payload.name.strip()),
        "Shade system code already exists.",
    )


@router.get("/shades", response_model=list[ShadeRead])
def list_shades(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER)),
):
    return list(db.execute(select(Shade).order_by(Shade.code)).scalars())


@router.post("/shades", response_model=ShadeRead, status_code=status.HTTP_201_CREATED)
def create_shade(
    payload: ShadeCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    return _create_lookup(
        db,
        Shade(
            shade_system_id=payload.shade_system_id,
            code=payload.code.strip(),
            name=payload.name.strip(),
        ),
        "Shade code already exists for the selected shade system.",
    )


@router.get("/material-classes", response_model=list[MaterialClassRead])
def list_material_classes(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER)),
):
    return list(db.execute(select(MaterialClass).order_by(MaterialClass.code)).scalars())


@router.post("/material-classes", response_model=MaterialClassRead, status_code=status.HTTP_201_CREATED)
def create_material_class(
    payload: MaterialClassCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    return _create_lookup(
        db,
        MaterialClass(code=payload.code.strip(), name=payload.name.strip()),
        "Material class code already exists.",
    )


@router.get("/units", response_model=list[UnitOfMeasureRead])
def list_units(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER)),
):
    return list(db.execute(select(UnitOfMeasure).order_by(UnitOfMeasure.code)).scalars())


@router.post("/units", response_model=UnitOfMeasureRead, status_code=status.HTTP_201_CREATED)
def create_unit(
    payload: UnitOfMeasureCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    return _create_lookup(
        db,
        UnitOfMeasure(code=payload.code.strip(), name=payload.name.strip()),
        "Unit of measure code already exists.",
    )


@router.get("/stock-locations", response_model=list[StockLocationRead])
def list_stock_locations(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER)),
):
    return list(db.execute(select(StockLocation).order_by(StockLocation.code)).scalars())


@router.post("/stock-locations", response_model=StockLocationRead, status_code=status.HTTP_201_CREATED)
def create_stock_location(
    payload: StockLocationCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    return _create_lookup(
        db,
        StockLocation(code=payload.code.strip(), name=payload.name.strip()),
        "Stock location code already exists.",
    )


@router.get("/movement-reasons", response_model=list[MovementReasonRead])
def list_movement_reasons(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER)),
):
    return list(db.execute(select(MovementReason).order_by(MovementReason.code)).scalars())


@router.post("/movement-reasons", response_model=MovementReasonRead, status_code=status.HTTP_201_CREATED)
def create_movement_reason(
    payload: MovementReasonCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    return _create_lookup(
        db,
        MovementReason(
            code=payload.code.strip(),
            name=payload.name.strip(),
            allowed_sign=payload.allowed_sign,
        ),
        "Movement reason code already exists.",
    )
