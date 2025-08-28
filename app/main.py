import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import canvas_router, health_router, notion_router, setup_router, sync_router
from app.api.auth import router as auth_router
from app.firebase import firebase_manager
from app.logging import setup_logging

# Setup logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown."""
    # Startup
    try:
        if firebase_manager.db:
            print("✅ Firebase initialized successfully")
        else:
            print("❌ Firebase initialization failed")
    except Exception as e:
        print(f"❌ Firebase startup error: {e}")

    yield

    # Shutdown (if needed)
    pass


# Create FastAPI app
app = FastAPI(
    title="Turing Project",
    description="Have complete control over your course management",
    version="1.0.0",
    lifespan=lifespan,
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
app.include_router(health_router)
app.include_router(auth_router)  # New authentication router
app.include_router(setup_router)
app.include_router(canvas_router)
app.include_router(notion_router)
app.include_router(sync_router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Turing Project",
        "version": "1.0.0",
        "features": [
            "Work in progress",
        ],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
