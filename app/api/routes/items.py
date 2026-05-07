from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.api.pagination import normalize_pagination
from app.db.models import Item, UserRole
from app.schemas.item import ItemCreate, ItemRead
from app.schemas.pagination import Page
from app.services.attributes import AttributeValidationError, TemplateSpecError
from app.services.items import (
    ItemVariantConflictError,
    ItemBlankPayload,
    ItemIvobaseCartridgePayload,
    ItemTypeMismatchError,
    MaterialClassNotFoundError,
    ManufacturerNotFoundError,
    MedicalTraceabilityError,
    ShadeNotFoundError,
    TemplateNotFoundError,
    UnitOfMeasureNotFoundError,
    create_relational_item,
    create_item_variant,
)
from app.services.sku import SKUGenerationError

router = APIRouter(prefix="/items")


@router.post("/", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ItemCreate,
    response: Response,
    db: Session = Depends(get_db),
    _: UserRole = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> Item:
    try:
        if payload.sku or payload.item_type or payload.blank_details or payload.ivobase_cartridge_details:
            item = create_relational_item(
                db,
                item_type=payload.item_type or "generic",
                sku=payload.sku or "",
                name=payload.name or payload.sku or "",
                unit_id=payload.unit_id,
                manufacturer_id=payload.manufacturer_id,
                template_id=payload.template_id,
                track_lots=payload.track_lots,
                metadata=payload.metadata,
                legacy_attributes=payload.attributes,
                blank_details=(
                    ItemBlankPayload(**payload.blank_details.model_dump())
                    if payload.blank_details
                    else None
                ),
                ivobase_cartridge_details=(
                    ItemIvobaseCartridgePayload(**payload.ivobase_cartridge_details.model_dump())
                    if payload.ivobase_cartridge_details
                    else None
                ),
            )
            created = True
        else:
            if payload.template_id is None or payload.uom is None:
                raise HTTPException(
                    status_code=422,
                    detail="template_id and uom are required for legacy template-driven item creation.",
                )
            item, created = create_item_variant(
                db,
                payload.template_id,
                payload.attributes,
                uom=payload.uom,
                track_lots=payload.track_lots,
                manufacturer_id=payload.manufacturer_id,
            )
    except TemplateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ManufacturerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (UnitOfMeasureNotFoundError, MaterialClassNotFoundError, ShadeNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (AttributeValidationError, TemplateSpecError, SKUGenerationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (ItemVariantConflictError, ItemTypeMismatchError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except MedicalTraceabilityError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not created:
        response.status_code = status.HTTP_200_OK
    return item


@router.get("/{item_id}", response_model=ItemRead)
def get_item(
    item_id: int,
    db: Session = Depends(get_db),
) -> Item:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")
    return item


@router.get("/", response_model=Page[ItemRead])
def list_items(
    template_id: int | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(Item)
    if template_id:
        stmt = stmt.where(Item.template_id == template_id)

    page, page_size, offset = normalize_pagination(page, page_size)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    items = (
        db.execute(stmt.order_by(Item.sku).offset(offset).limit(page_size))
        .scalars()
        .all()
    )
    return {"items": list(items), "page": page, "page_size": page_size, "total": total}
