from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import api_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine, wait_for_db
from app.services.bootstrap import ensure_admin_user
from app.web.routes import router as web_router


app = FastAPI(title=settings.app_name, debug=settings.debug)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.api_prefix)
app.include_router(web_router)

app.mount("/static", StaticFiles(directory="app/web/static"), name="static")


@app.on_event("startup")
def on_startup() -> None:
    wait_for_db(settings.db_connect_retries, settings.db_connect_delay)
    if settings.auto_create_db and settings.app_env != "prod":
        Base.metadata.create_all(bind=engine)
    try:
        ensure_admin_user()
    except Exception:
        pass
