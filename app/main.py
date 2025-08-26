from fastapi import FastAPI
from app.config import settings
from app.logging import setup_logging
from app.routes.setup import router as setup_router
from app.db import create_tables
import app.models  # Import models to ensure tables are created

# Setup logging
setup_logging()

app = FastAPI(
    title="Canvas Sync", description="Synchronize Canvas events with Notion and Google Calendar", version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Create database tables on startup"""
    create_tables()


# Register routers
app.include_router(setup_router)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
