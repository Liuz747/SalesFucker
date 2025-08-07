"""
Optimized JWT Authentication Dependencies

Enhanced version of JWT dependencies with caching and performance optimizations
while maintaining the explicit dependency-based approach.
"""

import asyncio
from functools import lru_cache
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import time

from src.auth.jwt_auth import verify_jwt_token, JWTTenantContext
from src.utils import get_component_logger

logger = get_component_logger(__name__, "OptimizedAuth")

# HTTP Bearer scheme for automatic token extraction
security = HTTPBearer(auto_error=False)

# In-memory cache for JWT verification results (with TTL)
_jwt_cache: Dict[str, tuple] = {}
JWT_CACHE_TTL = 300  # 5 minutes cache


def _clean_expired_cache():
    """Remove expired JWT cache entries"""
    current_time = time.time()
    expired_keys = [
        token_hash for token_hash, (context, timestamp) in _jwt_cache.items()
        if current_time - timestamp > JWT_CACHE_TTL
    ]
    for key in expired_keys:
        del _jwt_cache[key]


def _get_token_hash(token: str) -> str:
    """Create a hash of the token for caching (avoid storing full JWT)"""
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()[:16]


async def get_jwt_tenant_context_cached(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> JWTTenantContext:
    """
    Optimized JWT tenant context extraction with caching
    
    Features:
    - Automatic token extraction via HTTPBearer
    - In-memory caching of verification results
    - Cache cleanup for expired entries
    - Comprehensive error handling
    """
    if not credentials:
        logger.warning("Missing JWT token in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "authentication_required",
                "message": "JWT token is required",
                "hint": "Include 'Authorization: Bearer <token>' header"
            }
        )
    
    token = credentials.credentials
    token_hash = _get_token_hash(token)
    
    # Check cache first
    current_time = time.time()
    if token_hash in _jwt_cache:
        cached_context, cached_time = _jwt_cache[token_hash]
        if current_time - cached_time < JWT_CACHE_TTL:
            logger.debug(f"JWT cache hit for tenant: {cached_context.tenant_id}")
            return cached_context
        else:
            # Remove expired entry
            del _jwt_cache[token_hash]
    
    # Verify JWT token
    try:
        tenant_context = await verify_jwt_token(token)
        
        # Cache the result
        _jwt_cache[token_hash] = (tenant_context, current_time)
        
        # Periodic cache cleanup (every 100 requests)
        if len(_jwt_cache) > 100:
            _clean_expired_cache()
        
        logger.debug(f"JWT verified and cached for tenant: {tenant_context.tenant_id}")
        return tenant_context
        
    except Exception as e:
        logger.error(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_jwt_token",
                "message": "JWT token verification failed",
                "details": str(e)
            }
        )


# Aliases for backward compatibility
get_jwt_tenant_context = get_jwt_tenant_context_cached


# Convenience functions for common use cases
async def get_tenant_id_only(
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context_cached)
) -> str:
    """Extract just the tenant_id for simple use cases"""
    return tenant_context.tenant_id


async def get_user_id_only(
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context_cached)
) -> str:
    """Extract just the user_id for simple use cases"""
    return tenant_context.user_id


def require_permissions(*required_permissions: str):
    """
    Dependency factory for permission-based access control
    
    Usage:
        @router.get("/admin")
        async def admin_endpoint(
            tenant_context: JWTTenantContext = Depends(require_permissions("admin", "read"))
        ):
            # Only users with 'admin' AND 'read' permissions can access
    """
    async def check_permissions(
        tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context_cached)
    ) -> JWTTenantContext:
        user_permissions = set(tenant_context.permissions or [])
        required_perms = set(required_permissions)
        
        if not required_perms.issubset(user_permissions):
            missing_perms = required_perms - user_permissions
            logger.warning(
                f"Permission denied for user {tenant_context.user_id}. "
                f"Missing: {missing_perms}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "insufficient_permissions",
                    "message": "Insufficient permissions to access this resource",
                    "required_permissions": list(required_permissions),
                    "missing_permissions": list(missing_perms)
                }
            )
        
        return tenant_context
    
    return check_permissions


def require_role(required_role: str):
    """
    Dependency factory for role-based access control
    
    Usage:
        @router.get("/admin")
        async def admin_endpoint(
            tenant_context: JWTTenantContext = Depends(require_role("admin"))
        ):
            # Only users with 'admin' role can access
    """
    async def check_role(
        tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context_cached)
    ) -> JWTTenantContext:
        if tenant_context.role != required_role:
            logger.warning(
                f"Role access denied for user {tenant_context.user_id}. "
                f"Required: {required_role}, Got: {tenant_context.role}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "insufficient_role",
                    "message": f"Access requires '{required_role}' role",
                    "user_role": tenant_context.role,
                    "required_role": required_role
                }
            )
        
        return tenant_context
    
    return check_role


# Health check for auth system
async def auth_health_check() -> Dict[str, Any]:
    """Health check for authentication system"""
    return {
        "status": "healthy",
        "cache_size": len(_jwt_cache),
        "cache_ttl_seconds": JWT_CACHE_TTL,
        "features": [
            "jwt_verification",
            "token_caching", 
            "permission_checking",
            "role_based_access"
        ]
    }