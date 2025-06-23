"""
NBA Play-by-Play API
Main FastAPI application for serving NBA game data and analytics.
"""

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from datetime import datetime

from .routers import player_stats, team_stats, lineup_stats
from .utils.database import startup_db, shutdown_db

# Initialize FastAPI app
app = FastAPI(
    title="NBA Play-by-Play API",
    description="""
    Comprehensive NBA game data and analytics API providing access to:
    - Historical play-by-play data (1996-present)
    - Player and team statistics
    - Advanced analytics and shot charts
    - Lineup on/off court analysis
    
    Supports complex queries with statistical analysis, correlation, and regression capabilities.
    """,
    version="1.0.0",
    contact={
        "name": "NBA PBP API Support",
        "url": "https://nba-pbp-api.com/support",
        "email": "support@nba-pbp-api.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on deployment needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include routers
app.include_router(player_stats.router, prefix="/api/v1", tags=["player-stats"])
app.include_router(team_stats.router, prefix="/api/v1", tags=["team-stats"])
app.include_router(lineup_stats.router, prefix="/api/v1", tags=["lineup-stats"])

# Event handlers
@app.on_event("startup")
async def startup_event():
    """Initialize database connections on startup"""
    await startup_db()

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections on shutdown"""
    await shutdown_db()

# Health check endpoint
@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy", 
        "timestamp": datetime.utcnow(),
        "service": "NBA Play-by-Play API",
        "version": "1.0.0"
    }

# Metrics endpoint for monitoring
@app.get("/metrics")
async def metrics():
    """Basic metrics endpoint for monitoring"""
    return {
        "status": "operational",
        "timestamp": datetime.utcnow(),
        # TODO: Add actual metrics when implemented
        "placeholder": "Metrics will be implemented with Redis/Prometheus"
    }

# Root endpoint
@app.get("/")
async def root():
    """API root endpoint with basic information"""
    return {
        "message": "NBA Play-by-Play API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "description": "Comprehensive NBA data analytics API"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)