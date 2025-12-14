from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from api.routes import router as api_router
from auth.routes import router as auth_router
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


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from datetime import datetime
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


# Lambda handler
handler = Mangum(app, lifespan="off")
