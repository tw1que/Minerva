from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.pagination import normalize_pagination
from app.db.models import Item, ItemTemplate, Manufacturer
from app.schemas.catalog import CatalogItemRead
from app.schemas.pagination import Page

router = APIRouter(prefix="/catalog")


@router.get("/items", response_model=Page[CatalogItemRead])
def list_catalog_items(
    search: str | None = None,
    manufacturer_id: int | None = None,
    attr_key: str | None = None,
    attr_val: str | None = None,
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(get_db),
) -> dict:
    stmt = (
        select(
            Item,
            ItemTemplate.name.label("template_name"),
            ItemTemplate.manufacturer_id.label("manufacturer_id"),
            Manufacturer.name.label("manufacturer_name"),
        )
        .join(ItemTemplate, Item.template_id == ItemTemplate.id)
        .outerjoin(Manufacturer, ItemTemplate.manufacturer_id == Manufacturer.id)
    )

    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Item.product_code.ilike(pattern),
                ItemTemplate.name.ilike(pattern),
                Manufacturer.name.ilike(pattern),
            )
        )

    if manufacturer_id:
        stmt = stmt.where(ItemTemplate.manufacturer_id == manufacturer_id)

    if attr_key and attr_val:
        stmt = stmt.where(Item.attributes[attr_key].astext.ilike(f"%{attr_val}%"))

    page, page_size, offset = normalize_pagination(page, page_size)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

    rows = (
        db.execute(stmt.order_by(Item.product_code).offset(offset).limit(page_size))
        .all()
    )

    items: list[CatalogItemRead] = []
    for item, template_name, manufacturer_id_value, manufacturer_name in rows:
        items.append(
            CatalogItemRead(
                id=item.id,
                product_code=item.product_code,
                template_id=item.template_id,
                template_name=template_name,
                manufacturer_id=manufacturer_id_value,
                manufacturer_name=manufacturer_name,
                uom=item.uom,
                attributes=item.attributes,
                track_lots=item.track_lots,
            )
        )

    return {"items": items, "page": page, "page_size": page_size, "total": total}
