from fastapi import FastAPI
from app.config import settings
from app.logging import setup_logging
from app.db import create_tables
from app.api import (
    health_router,
    setup_router,
    canvas_router,
    notion_router,
    sync_router,
)

# Import models to ensure they're registered with SQLAlchemy
import app.models

# Setup logging
setup_logging()

# Create FastAPI app
app = FastAPI(
    title="Canvas Sync", description="Synchronize Canvas events with Notion and Google Calendar", version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Create database tables on startup."""
    create_tables()


# Register API routers
app.include_router(health_router)
app.include_router(setup_router)
app.include_router(canvas_router)
app.include_router(notion_router)
app.include_router(sync_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
