"""
FastAPI Main Application Entry Point

Entry point for the MAS Cosmetic Agent System API.
Creates a minimal app for uvicorn while the full app is in src/api/main.py.
"""

import uvicorn
from config.settings import settings


def main():
    """Main entry point for the application."""
    uvicorn.run(
        "src.api.main:app",  # Point directly to src.api.main:app
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )


if __name__ == "__main__":
    main()