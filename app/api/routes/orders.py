from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.db.models import Order, OrderMaterial, User, UserRole
from app.schemas.order import OrderCreate, OrderMaterialRead, OrderRead

router = APIRouter()


@router.get("/orders", response_model=list[OrderRead])
def list_orders(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER)),
):
    return list(db.execute(select(Order).order_by(Order.id)).scalars())


@router.post("/orders", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    if db.execute(select(Order).where(Order.order_number == payload.order_number)).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Order number already exists.")
    order = Order(order_number=payload.order_number.strip(), status=payload.status, notes=payload.notes)
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.get("/orders/{order_id}", response_model=OrderRead)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER)),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    return order


@router.get("/order-materials", response_model=list[OrderMaterialRead])
def list_order_materials(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER)),
):
    return list(db.execute(select(OrderMaterial).order_by(OrderMaterial.id)).scalars())
