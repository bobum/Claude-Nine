from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import engine, get_db, Base
from .config import settings
from .routes import teams, agents, work_items

# Create tables (for development - use Alembic in production)
Base.metadata.create_all(bind=engine)

# Initialize FastAPI
app = FastAPI(
    title="Claude-Nine API",
    description="API for managing AI development teams",
    version="1.0.0",
    debug=settings.debug
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check
@app.get("/health")
def health_check():
    """Basic health check endpoint"""
    return {
        "status": "ok",
        "version": "1.0.0",
        "service": "claude-nine-api"
    }


# Database health check
@app.get("/health/db")
def db_health_check(db: Session = Depends(get_db)):
    """Database connectivity health check"""
    try:
        # Try to execute a simple query
        db.execute("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": str(e)}


# Root endpoint
@app.get("/")
def root():
    """API root with basic info"""
    return {
        "service": "Claude-Nine API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# Include routers
app.include_router(teams.router, prefix="/api/teams", tags=["teams"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(work_items.router, prefix="/api/work-items", tags=["work-items"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
