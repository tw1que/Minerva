from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import settings
from app.db.session import wait_for_db
from app.services.bootstrap import ensure_admin_user, ensure_reference_data


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


@app.on_event("startup")
def on_startup() -> None:
    wait_for_db(settings.db_connect_retries, settings.db_connect_delay)
    ensure_admin_user()
    ensure_reference_data()
