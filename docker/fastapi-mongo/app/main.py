"""FastAPI + MongoDB Application - Iquitos EV Infrastructure API."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import connect_db, close_db
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    await connect_db()
    yield
    await close_db()


app = FastAPI(
    title="Iquitos EV Infrastructure API",
    description="API para gestión de infraestructura de carga EV en Iquitos",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "Iquitos EV Infrastructure API",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": settings.DATABASE_NAME,
    }
