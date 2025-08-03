"""
FastAPI Main Application

Entry point for the MAS Cosmetic Agent System API.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging

from config.settings import settings
from src.api import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-Agent System for Cosmetic Industry Digital Marketing",
    debug=settings.debug,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(api_router)

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "MAS Cosmetic Agent System",
        "version": settings.app_version,
        "status": "operational",
        "features": [
            "Multi-agent conversation processing",
            "Compliance review and content moderation", 
            "Sales agent with cosmetic expertise",
            "Multi-tenant support",
            "LangGraph orchestration",
            "Multi-LLM provider support",
            "Intelligent routing and failover",
            "Cost tracking and optimization",
            "Multi-modal input processing"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker and load balancers."""
    return {
        "status": "healthy",
        "service": "mas-agent",
        "version": settings.app_version
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


def main():
    """Main entry point for the application."""
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )


if __name__ == "__main__":
    main() 