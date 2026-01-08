from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.api.pagination import normalize_pagination
from app.db.models import ItemTemplate, Manufacturer, TemplateField, UserRole
from app.schemas.pagination import Page
from app.schemas.template import TemplateCreate, TemplateRead

router = APIRouter(prefix="/templates")


@router.post("/", response_model=TemplateRead, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: TemplateCreate,
    db: Session = Depends(get_db),
    _: UserRole = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> ItemTemplate:
    if payload.manufacturer_id is not None:
        manufacturer = db.get(Manufacturer, payload.manufacturer_id)
        if not manufacturer:
            raise HTTPException(status_code=404, detail="Manufacturer not found.")

    template = ItemTemplate(
        name=payload.name,
        manufacturer_id=payload.manufacturer_id,
        sku_prefix=payload.sku_prefix,
        sku_pattern=payload.sku_pattern,
        seq_scope=payload.seq_scope,
    )

    for field in payload.fields:
        template.fields.append(
            TemplateField(
                field_key=field.field_key,
                field_type=field.field_type,
                required=field.required,
                include_in_sku=field.include_in_sku,
                sku_order=field.sku_order,
                default_value=field.default_value,
                enum_values=field.enum_values,
                format=field.format,
            )
        )

    try:
        db.add(template)
        db.commit()
        db.refresh(template)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Template already exists.") from exc

    return template


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
