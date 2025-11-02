"""
IonologyBot Backend API
Document Upload & Ingestion Pipeline
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.routes import upload, status, search, auth, health, chat
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
import asyncio

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
        
        # Validate DeepSeek API key configuration (non-blocking warning)
        import os
        deepseek_key = settings.deepseek_api_key or os.getenv("DEEPSEEK_API_KEY")
        if not deepseek_key or deepseek_key.strip() == "":
            logging.warning(
                "DeepSeek API key is not configured. "
                "Please configure DEEPSEEK_API_KEY environment variable or Settings.deepseek_api_key. "
                "Chat functionality will not work without a valid API key."
            )
        else:
            logging.info("DeepSeek API key configuration validated")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logging.info("Database tables created successfully")
        
        # Initialize search infrastructure
        DatabaseInitService.initialize_search_infrastructure()
        
        # Pre-warm embedding model to avoid first-request delay
        try:
            from app.services.embeddings import EmbeddingService
            embedding_service = EmbeddingService()
            # Generate a test embedding to warm up the model
            embedding_service.generate_single_embedding("test")
            logging.info("Embedding model pre-warmed successfully")
        except Exception as e:
            logging.warning(f"Failed to pre-warm embedding model: {e}")
        
        # Add essential performance indexes if using PostgreSQL
        if settings.database_url.startswith('postgresql://'):
            try:
                from sqlalchemy import text
                with engine.connect() as conn:
                    # Add only essential indexes for search performance
                    essential_indexes = [
                        # Critical: Full-text search index for lexical search
                        "CREATE INDEX IF NOT EXISTS idx_chunk_text_fts ON chunks USING gin(to_tsvector('english', text));",
                        # Helpful: For batch fetching chunk text by hash
                        "CREATE INDEX IF NOT EXISTS idx_chunk_hash ON chunks(hash);",
                    ]
                    
                    for index_sql in essential_indexes:
                        try:
                            conn.execute(text(index_sql))
                            conn.commit()
                            logging.info(f"Created index: {index_sql.split('ON')[1].split('(')[0].strip()}")
                        except Exception as e:
                            logging.warning(f"Could not create index: {e}")
                    
                logging.info("Essential performance indexes added successfully")
            except Exception as e:
                logging.warning(f"Failed to add performance indexes: {e}")
        
        # Clear rate limiter on startup to reset any accumulated data
        from app.services.rate_limiter import rate_limiter
        rate_limiter.force_reset()
        logging.info("Rate limiter force reset on startup")
        
        # Start background processor for document ingestion
        from app.services.background_processor import background_processor
        asyncio.create_task(background_processor.start_processing())
        logging.info("Background document processor started")
        
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
app.include_router(chat.router, prefix="/api", tags=["chat"])
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
    return {"status": "healthy", "service": "ionologybot-api"}

@app.get("/status")
async def status_check():
    """Quick status check for monitoring"""
    try:
        from sqlalchemy import text
        from app.core.database import get_db
        
        db = next(get_db())
        db.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "database": "connected",
            "service": "ionologybot-api"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "service": "ionologybot-api"
        }
