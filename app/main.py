# app/main.py
# Entry point of the FastAPI application.
# Creates the FastAPI app, registers routers, and sets up the database on startup.

from fastapi import FastAPI

from app.database import engine, Base
from app.routers import certificates, jobs

# Import models so SQLAlchemy knows about them when creating tables.
# Without these imports, Base.metadata.create_all won't find the tables.
from app.models import job, certificate  # noqa: F401

# ---------------------------------------------------------------------------
# Create the FastAPI application instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Bulk Certificate Generator API",
    description=(
        "Generate PDF certificates in bulk for multiple recipients. "
        "Submit a list of recipients, track job progress, and download individual certificates."
    ),
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Database table creation
# ---------------------------------------------------------------------------
# This creates all tables defined in our models if they don't already exist.
# In production you would use Alembic migrations instead, but for development
# this is a quick way to get started.
@app.on_event("startup")
def create_tables():
    """Create database tables when the application starts.
    If the database is unavailable (e.g. local dev without Postgres),
    log a warning instead of crashing so Swagger still loads.
    """
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        print(
            f"⚠️  WARNING: Could not connect to the database on startup: {exc}\n"
            "   The API will start, but database operations will fail until\n"
            "   PostgreSQL is running and DATABASE_URL is correct."
        )


# ---------------------------------------------------------------------------
# Register routers
# ---------------------------------------------------------------------------
# Certificates router — /api/certificates
app.include_router(
    certificates.router,
    prefix="/api/certificates",
    tags=["Certificates"],
)

# Jobs router — /api/jobs  (Phase 2: bulk job creation)
app.include_router(
    jobs.router,
    prefix="/api/jobs",
    tags=["Jobs"],
)


# ---------------------------------------------------------------------------
# Health check endpoint
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
def health_check():
    """
    Simple health check endpoint.
    Returns 200 OK if the application is running.
    Used by Render (and other platforms) to verify the service is alive.
    """
    return {"status": "ok", "message": "Bulk Certificate Generator API is running"}
