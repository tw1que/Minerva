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
    TemplateNotFoundError,
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
        item, created = create_item_variant(
            db,
            payload.template_id,
            payload.attributes,
            uom=payload.uom,
            track_lots=payload.track_lots,
        )
    except TemplateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (AttributeValidationError, TemplateSpecError, SKUGenerationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ItemVariantConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

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
        db.execute(stmt.order_by(Item.product_code).offset(offset).limit(page_size))
        .scalars()
        .all()
    )
    return {"items": list(items), "page": page, "page_size": page_size, "total": total}
