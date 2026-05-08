from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.db.models import StockMovement, User, UserRole
from app.schemas.stock import (
    AdjustStockRequest,
    ConsumeStockRequest,
    ReceiveStockRequest,
    StockBalanceRead,
    StockMovementRead,
)
from app.services.inventory import (
    AdjustStockInput,
    ConsumeStockInput,
    InsufficientStockError,
    InventoryValidationError,
    ReceiveStockInput,
    adjust_stock,
    consume_stock,
    list_item_balances,
    list_lot_balances,
    receive_stock,
)

router = APIRouter(prefix="/stock")


@router.post("/receive", response_model=StockMovementRead, status_code=status.HTTP_201_CREATED)
def receive_stock_route(
    payload: ReceiveStockRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    try:
        _, movement = receive_stock(
            db,
            ReceiveStockInput(
                item_id=payload.item_id,
                quantity=payload.quantity,
                movement_reason_id=payload.movement_reason_id,
                manufacturer_lot_code=payload.manufacturer_lot_code,
                manufacturer_id=payload.manufacturer_id,
                material_class_id=payload.material_class_id,
                shade_id=payload.shade_id,
                lot_code=payload.lot_code,
                to_location_id=payload.to_location_id,
                expires_at=payload.expires_at,
                certificate_ref=payload.certificate_ref,
                notes=payload.notes,
                ref_type=payload.ref_type,
                ref_id=payload.ref_id,
                moved_by=payload.moved_by,
                created_by=payload.created_by,
                comment=payload.comment,
            ),
        )
        return movement
    except InventoryValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/adjust", response_model=StockMovementRead, status_code=status.HTTP_201_CREATED)
def adjust_stock_route(
    payload: AdjustStockRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    try:
        return adjust_stock(
            db,
            AdjustStockInput(
                item_id=payload.item_id,
                qty_delta=payload.qty_delta,
                movement_reason_id=payload.movement_reason_id,
                comment=payload.comment,
                lot_id=payload.lot_id,
                from_location_id=payload.from_location_id,
                to_location_id=payload.to_location_id,
                ref_type=payload.ref_type,
                ref_id=payload.ref_id,
                moved_by=payload.moved_by,
                created_by=payload.created_by,
            ),
        )
    except InsufficientStockError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InventoryValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/consume", response_model=StockMovementRead, status_code=status.HTTP_201_CREATED)
def consume_stock_route(
    payload: ConsumeStockRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    try:
        movement, _ = consume_stock(
            db,
            ConsumeStockInput(
                order_id=payload.order_id,
                item_id=payload.item_id,
                lot_id=payload.lot_id,
                quantity=payload.quantity,
                movement_reason_id=payload.movement_reason_id,
                used_by=payload.used_by,
                created_by=payload.created_by,
                comment=payload.comment,
                from_location_id=payload.from_location_id,
                ref_type=payload.ref_type,
                ref_id=payload.ref_id,
            ),
        )
        return movement
    except InsufficientStockError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InventoryValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/movements", response_model=list[StockMovementRead])
def list_movements(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER)),
):
    return list(db.execute(select(StockMovement).order_by(StockMovement.id)).scalars())


@router.get("/balances/lots", response_model=list[StockBalanceRead])
def get_lot_balances(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER)),
):
    return [StockBalanceRead(key_id=lot_id, qty_on_hand=qty) for lot_id, qty in list_lot_balances(db)]


@router.get("/balances/items", response_model=list[StockBalanceRead])
def get_item_balances(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER)),
):
    return [StockBalanceRead(key_id=item_id, qty_on_hand=qty) for item_id, qty in list_item_balances(db)]
