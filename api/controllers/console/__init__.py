from .app.tenant import router as tenant_router
from .service_auth import router as auth_router

__all__ = [
    "tenant_router",
    "auth_router"
]