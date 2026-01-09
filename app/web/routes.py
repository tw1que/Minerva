from fastapi import APIRouter, Request

from app.core.config import settings
from fastapi.templating import Jinja2Templates

router = APIRouter()

templates = Jinja2Templates(directory="app/web/templates")


@router.get("/")
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "medical_traceability": settings.medical_traceability},
    )
