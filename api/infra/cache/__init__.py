"""
Cache module

This module provides Redis-based caching functionality for the application.

Core Features:
- Redis client management
- Asynchronous client access
- Connection pooling
"""

from .redis_client import get_redis_client, close_redis_client, test_redis_connection

__all__ = [
    "get_redis_client",
    "close_redis_client",
    "test_redis_connection"
]