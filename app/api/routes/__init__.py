from fastapi import APIRouter

from app.api.routes import auth, health, items, lookups, lots, orders, stock

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(lookups.router, tags=["lookups"])
api_router.include_router(items.router, tags=["items"])
api_router.include_router(lots.router, tags=["lots"])
api_router.include_router(stock.router, tags=["stock"])
api_router.include_router(orders.router, tags=["orders"])
