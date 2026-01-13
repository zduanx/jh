from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from api.routes import router as api_router
from api.ingestion_routes import router as ingestion_router
from api.jobs_routes import router as jobs_router
from auth.routes import router as auth_router
from sourcing.routes import router as sourcing_router
from config.settings import settings

app = FastAPI(
    title="Job Hunt Tracker API",
    description="Backend API for job application tracking",
    version="1.0.0",
    root_path="/prod"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(api_router, prefix="/api", tags=["API"])
app.include_router(ingestion_router, prefix="/api/ingestion", tags=["Ingestion Workflow"])
app.include_router(jobs_router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(sourcing_router, prefix="/api/sourcing", tags=["Job URL Sourcing"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from datetime import datetime
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.get("/debug/db")
async def debug_db():
    """Debug endpoint to check which database is being used"""
    import re
    from db.session import DATABASE_URL
    masked = re.sub(r':[^:@]*@', ':***@', DATABASE_URL)

    db_type = "UNKNOWN"
    if 'ep-aged-darkness' in DATABASE_URL:
        db_type = "TEST"
    elif 'ep-quiet-hat' in DATABASE_URL:
        db_type = "PRODUCTION"

    return {
        "database_url": masked,
        "database_type": db_type
    }


# Lambda handler
handler = Mangum(app, lifespan="off")
