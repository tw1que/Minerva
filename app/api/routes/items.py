from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import Item, ItemTemplate
from app.db.models import compute_attributes_hash
from app.schemas.item import ItemCreate, ItemRead
from app.services.attributes import AttributeValidationError, normalize_attributes, to_jsonable
from app.services.sku import SKUGenerationError, generate_sku

router = APIRouter(prefix="/items")


@router.post("/", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ItemCreate,
    db: Session = Depends(get_db),
) -> Item:
    template = db.get(ItemTemplate, payload.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found.")

    try:
        normalized = normalize_attributes(list(template.fields), payload.attributes)
    except AttributeValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    normalized = to_jsonable(normalized)
    attr_hash = compute_attributes_hash(normalized)

    existing = db.execute(
        select(Item).where(
            Item.template_id == template.id,
            Item.attributes_hash == attr_hash,
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Item variant already exists.")

    try:
        sku = generate_sku(db, template, normalized)
    except SKUGenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    item = Item(
        template_id=template.id,
        sku=sku,
        uom=payload.uom,
        attributes=normalized,
        attributes_hash=attr_hash,
        track_lots=payload.track_lots,
    )

    try:
        db.add(item)
        db.commit()
        db.refresh(item)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="SKU already exists.") from exc

    return item


@router.get("/", response_model=list[ItemRead])
def list_items(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> list[Item]:
    stmt = select(Item).offset(offset).limit(limit)
    return list(db.execute(stmt).scalars().all())


@router.get("/{item_id}", response_model=ItemRead)
def get_item(
    item_id: int,
    db: Session = Depends(get_db),
) -> Item:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")
    return item
