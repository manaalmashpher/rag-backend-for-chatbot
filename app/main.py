"""
IonologyBot Backend API
Document Upload & Ingestion Pipeline
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.routes import upload, status, search, auth, health
from app.core.config import settings
from app.core.database import engine
from app.models import Base
# Import all models to ensure they're registered with Base
from app.models.database import Document, Ingestion, Chunk, SearchLog
from app.models.auth import User, Organization
from app.services.database_init import DatabaseInitService
from app.middleware.rate_limiting import RateLimitingMiddleware
from app.middleware.logging import StructuredLoggingMiddleware
from app.middleware.error_handling import ErrorHandlingMiddleware
import logging
import os

app = FastAPI(
    title="IonologyBot API",
    description="Document Upload & Ingestion Pipeline",
    version="1.0.0"
)

# Configure logging
logging.basicConfig(
    level=getattr(settings, 'log_level', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@app.on_event("startup")
async def startup_event():
    """Create database tables and initialize search infrastructure on startup"""
    try:
        logging.info("Starting database initialization...")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logging.info("Database tables created successfully")
        
        # Initialize search infrastructure
        DatabaseInitService.initialize_search_infrastructure()
        
        # Clear rate limiter on startup to reset any accumulated data
        from app.services.rate_limiter import rate_limiter
        rate_limiter.force_reset()
        logging.info("Rate limiter force reset on startup")
        
        logging.info("Database initialization completed successfully")
    except Exception as e:
        logging.error(f"Database initialization failed: {str(e)}")
        # Don't pass silently - this is important for production
        raise RuntimeError(f"Failed to initialize database: {str(e)}")

# Add middleware (order matters - last added is first executed)
# Error handling middleware (should be first to catch all errors)
app.add_middleware(ErrorHandlingMiddleware)

# Structured logging middleware
app.add_middleware(StructuredLoggingMiddleware)

# Rate limiting middleware
if getattr(settings, 'rate_limit_enabled', True):
    app.add_middleware(RateLimitingMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(status.router, prefix="/api", tags=["status"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(health.router, tags=["health"])

# Serve static files from the built frontend
if os.path.exists("dist"):
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")
    
    @app.get("/")
    async def serve_frontend():
        """Serve the React frontend"""
        return FileResponse("dist/index.html")
    
    @app.get("/{path:path}")
    async def serve_frontend_routes(path: str):
        """Serve React frontend for all routes (SPA routing)"""
        # Check if it's an API route
        if path.startswith("api/"):
            return {"error": "API route not found"}
        
        # Serve index.html for all other routes (React Router will handle them)
        if os.path.exists("dist/index.html"):
            return FileResponse("dist/index.html")
        else:
            return {"error": "Frontend not built"}
else:
    @app.get("/")
    async def root():
        return {"message": "IonologyBot API is running - Frontend not built"}

@app.get("/health")
async def health_check():
    """Simple health check endpoint (backward compatible)"""
    print("DEBUG: Health check endpoint called")
    try:
        from app.services.health_service import HealthService
        print("DEBUG: Creating HealthService")
        health_service = HealthService()
        print("DEBUG: Calling liveness_check")
        result = health_service.liveness_check()
        print(f"DEBUG: Liveness check result: {result}")
        return {"status": result["status"]}
    except Exception as e:
        print(f"DEBUG: Health check failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        # If health service fails, return basic health status
        return {"status": "healthy", "note": "Basic health check - some services may be unavailable"}
