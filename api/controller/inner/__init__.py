from .completion import router as completion_router
from .service_auth import router as auth_router
from .health import router as health_router

__all__ = [
    "completion_router",
    "auth_router",
    "health_router"
]