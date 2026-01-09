from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.api.pagination import normalize_pagination
from app.db.models import Item, ItemTemplate, UserRole
from app.schemas.item import ItemRead, ItemVariantCreate
from app.schemas.pagination import Page
from app.schemas.template import TemplateCreate, TemplateRead
from app.services.attributes import AttributeValidationError, TemplateSpecError
from app.services.items import (
    ItemVariantConflictError,
    MedicalTraceabilityError,
    TemplateNotFoundError,
    create_item_variant,
)
from app.services.sku import SKUGenerationError
from app.services.templates import (
    ManufacturerNotFoundError,
    TemplateConflictError,
    create_template as create_template_service,
)

router = APIRouter(prefix="/templates")


@router.post("/", response_model=TemplateRead, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: TemplateCreate,
    db: Session = Depends(get_db),
    _: UserRole = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> ItemTemplate:
    try:
        return create_template_service(db, payload)
    except ManufacturerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TemplateConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/", response_model=Page[TemplateRead])
def list_templates(
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(ItemTemplate)
    if search:
        stmt = stmt.where(ItemTemplate.name.ilike(f"%{search}%"))

    page, page_size, offset = normalize_pagination(page, page_size)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    items = (
        db.execute(stmt.order_by(ItemTemplate.name).offset(offset).limit(page_size))
        .scalars()
        .all()
    )
    return {"items": list(items), "page": page, "page_size": page_size, "total": total}


@router.get("/{template_id}", response_model=TemplateRead)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
) -> ItemTemplate:
    template = db.get(ItemTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found.")
    return template


@router.post(
    "/{template_id}/items",
    response_model=ItemRead,
    status_code=status.HTTP_201_CREATED,
)
def create_template_item(
    template_id: int,
    payload: ItemVariantCreate,
    response: Response,
    db: Session = Depends(get_db),
    _: UserRole = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> Item:
    try:
        item, created = create_item_variant(
            db,
            template_id,
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
    except MedicalTraceabilityError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not created:
        response.status_code = status.HTTP_200_OK
    return item
