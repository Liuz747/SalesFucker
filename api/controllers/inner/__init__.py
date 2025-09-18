from .completion import router as completion_router
from .health import router as health_router

__all__ = [
    "completion_router",
    "health_router"
]