"""
Main application entry point for the Turing Project.
"""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import canvas_router, health_router, notion_router, setup_router, sync_router
from app.api.auth import router as auth_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.firebase import firebase_manager

# Setup logging
setup_logging(log_level=settings.log_level, log_file=settings.log_file)

# Get logger for this module
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown."""
    # Startup
    try:
        if firebase_manager.db:
            log.info("Firebase initialized successfully")
        else:
            log.warning("Firebase initialization failed")
    except Exception as e:
        log.error(f"Firebase startup error: {e}")
    yield

    # Shutdown (if needed)
    log.info("Shutting down application")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Turing Project",
        description="Have complete control over your course management",
        version="1.0.0",
        lifespan=lifespan,
        debug=settings.debug,
    )

    # Add CORS middleware for frontend integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routers
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(setup_router, prefix="/api/v1")
    app.include_router(canvas_router, prefix="/api/v1")
    app.include_router(notion_router, prefix="/api/v1")
    app.include_router(sync_router, prefix="/api/v1")
    return app


# Create FastAPI app
app = create_app()


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Turing Project",
        "version": "1.0.0",
        "environment": settings.app_env,
        "features": [
            "Work in progress",
        ],
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.app_env,
        "firebase_available": firebase_manager.firebase_available,
    }


if __name__ == "__main__":
    log.info(f"Starting Turing Project on {settings.host}:{settings.port}")
    uvicorn.run(app, host=settings.host, port=settings.port, log_level=settings.log_level.lower())
