"""
Rivet Pro Web API - FastAPI Application.

Run with:
    uvicorn rivet_pro.adapters.web.main:app --reload --port 8000

Docs at:
    http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from rivet_pro.config.settings import settings
from rivet_pro.infra.observability import get_logger
from rivet_pro.infra.database import db

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Rivet Pro Web API...")
    logger.info(f"Environment: {settings.environment}")

    # Connect to database
    await db.connect()
    logger.info("Database connected")

    # Run migrations (commented out - migrations already applied manually)
    # await db.run_migrations()
    # logger.info("Migrations complete")

    yield

    # Shutdown
    logger.info("Shutting down Rivet Pro Web API...")
    await db.disconnect()
    logger.info("Database disconnected")


# Create FastAPI app
app = FastAPI(
    title="Rivet Pro CMMS API",
    description="Equipment-first CMMS with AI-powered OCR and troubleshooting",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS configuration
allowed_origins = settings.allowed_origins.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from rivet_pro.adapters.web.routers import auth, equipment, work_orders, stats, upload, stripe

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(equipment.router, prefix="/api/equipment", tags=["Equipment"])
app.include_router(work_orders.router, prefix="/api/work-orders", tags=["Work Orders"])
app.include_router(stats.router, prefix="/api/stats", tags=["Statistics"])
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(stripe.router, prefix="/api/stripe", tags=["Payments"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_healthy = await db.health_check()

    status = "healthy" if db_healthy else "unhealthy"

    return {
        "status": status,
        "service": "rivet-pro-api",
        "version": "1.0.0",
        "environment": settings.environment,
        "database": {
            "healthy": db_healthy
        }
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Rivet Pro CMMS API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
