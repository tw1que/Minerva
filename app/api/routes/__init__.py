from fastapi import APIRouter

from app.api.routes import (
    auth,
    catalog,
    health,
    inventory,
    items,
    lots,
    manufacturers,
    orders,
    stock,
    templates,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(manufacturers.router, tags=["manufacturers"])
api_router.include_router(templates.router, tags=["templates"])
api_router.include_router(items.router, tags=["items"])
api_router.include_router(lots.router, tags=["lots"])
api_router.include_router(catalog.router, tags=["catalog"])
api_router.include_router(inventory.router, tags=["inventory"])
api_router.include_router(stock.router, tags=["movements"])
api_router.include_router(orders.router, tags=["orders"])
