"""Enhanced FastAPI Application with Production Features."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.database import connect_db, close_db
from app.routes import router
from app.middleware import LoggingMiddleware, SecurityHeadersMiddleware

# Configure structured logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle with proper cleanup."""
    logger.info("Starting application...")
    await connect_db()
    logger.info("Database connected successfully")
    yield
    logger.info("Shutting down application...")
    await close_db()
    logger.info("Database connection closed")


app = FastAPI(
    title="Iquitos EV Infrastructure API",
    description="""
    API para gestión de infraestructura de carga de vehículos eléctricos en Iquitos, Perú.
    
    ## Características
    - Gestión de sesiones de carga
    - Almacenamiento de resultados de simulación RL
    - Comparación de agentes (SAC, PPO, A2C)
    - Métricas de emisiones CO₂
    
    ## Infraestructura
    - 128 cargadores (112 motos + 16 mototaxis)
    - 4,162 kWp capacidad solar
    - 2,000 kWh almacenamiento BESS
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middlewares
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Prometheus metrics
if settings.ENABLE_METRICS:
    Instrumentator().instrument(app).expose(app)

# Include routes
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "Iquitos EV Infrastructure API",
        "version": "1.0.0",
        "environment": "production" if not settings.DEBUG else "development",
    }


@app.get("/health")
async def health():
    """Detailed health check for load balancers."""
    from app.database import get_database
    
    try:
        db = get_database()
        await db.command("ping")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    health_status = {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "database_name": settings.DATABASE_NAME,
    }
    
    status_code = status.HTTP_200_OK if db_status == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(content=health_status, status_code=status_code)


@app.get("/ready")
async def readiness():
    """Kubernetes readiness probe."""
    return {"ready": True}


@app.get("/live")
async def liveness():
    """Kubernetes liveness probe."""
    return {"alive": True}


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )
