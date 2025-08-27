from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.logging import setup_logging
from app.firebase import firebase_manager
from app.api import (
    health_router,
    setup_router,
    canvas_router,
    notion_router,
    sync_router,
)
from app.api.auth import router as auth_router

# Setup logging
setup_logging()

# Create FastAPI app
app = FastAPI(
    title="Canvas Sync with Firebase",
    description="Synchronize Canvas events with Notion using Firebase authentication",
    version="2.0.0",
)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize Firebase on startup."""
    try:
        # Firebase manager is already initialized in firebase.py
        # Just verify it's working
        if firebase_manager.db:
            print("✅ Firebase initialized successfully")
        else:
            print("❌ Firebase initialization failed")
    except Exception as e:
        print(f"❌ Firebase startup error: {e}")


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
        "message": "Canvas to Notion Sync API with Firebase",
        "version": "2.0.0",
        "features": [
            "Firebase Authentication with Google",
            "Canvas course synchronization",
            "Notion integration",
            "Assignment tracking",
            "Duplicate detection",
            "Audit logging",
        ],
        "auth": {"firebase_config": "/auth/firebase-config", "login": "/auth/login", "profile": "/auth/me"},
        "endpoints": {"setup": "/setup", "sync": "/sync", "canvas": "/canvas", "notion": "/notion"},
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
