from .health import router as health_router
from .service_auth import router as auth_router
from .tenant import router as tenant_router

__all__ = [
    "auth_router",
    "health_router",
    "tenant_router",
]