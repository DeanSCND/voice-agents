from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from .api import calls, webhooks, websockets
from .models.database import engine, Base

app = FastAPI(
    title="Archer Backend API",
    description="Cartesia Line SDK voice agent backend for banking collections",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(calls.router)
app.include_router(webhooks.router)
app.include_router(websockets.router)

@app.on_event("startup")
async def startup():
    """Initialize database and resources."""
    # Create tables if they don't exist (dev only - use Alembic in production)
    async with engine.begin() as conn:
        # In production, use Alembic migrations instead
        if os.getenv("ENVIRONMENT") == "development":
            await conn.run_sync(Base.metadata.create_all)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "archer-backend",
        "version": "0.1.0"
    }

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Archer Backend API",
        "docs": "/docs",
        "health": "/health"
    }
