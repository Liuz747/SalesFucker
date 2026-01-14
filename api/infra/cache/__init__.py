"""
Cache module

This module provides Redis-based caching functionality for the application.

Core Features:
- Redis client management
- Asynchronous client access
- Connection pooling
"""

from .redis_client import (
    create_redis_client,
    test_redis_connection,
    close_redis_client
)

__all__ = [
    "create_redis_client",
    "test_redis_connection",
    "close_redis_client"
]
