from app.api.health import router as health_router
from app.api.setup import router as setup_router
from app.api.canvas import router as canvas_router
from app.api.notion import router as notion_router
from app.api.sync import router as sync_router

__all__ = [
    "health_router",
    "setup_router",
    "canvas_router",
    "notion_router",
    "sync_router",
]
