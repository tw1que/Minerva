from fastapi import APIRouter

from app.api.routes import health, items, lots, manufacturers, orders, stock, templates

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(manufacturers.router, tags=["manufacturers"])
api_router.include_router(templates.router, tags=["templates"])
api_router.include_router(items.router, tags=["items"])
api_router.include_router(lots.router, tags=["lots"])
api_router.include_router(stock.router, tags=["stock"])
api_router.include_router(orders.router, tags=["orders"])
