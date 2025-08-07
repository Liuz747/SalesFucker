"""
JWT Authentication Middleware

Centralized JWT token verification middleware that processes authentication
for all API requests and populates request.state with tenant context.
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import logging
from typing import Callable, List, Optional

from src.auth.jwt_auth import verify_jwt_token, JWTTenantContext
from src.utils import get_component_logger

logger = get_component_logger(__name__, "JWTMiddleware")


class JWTMiddleware:
    """
    JWT Authentication Middleware
    
    Processes JWT tokens for all requests and populates request.state
    with authenticated tenant context.
    """
    
    def __init__(
        self,
        exclude_paths: Optional[List[str]] = None,
        exclude_prefixes: Optional[List[str]] = None
    ):
        """
        Initialize JWT middleware
        
        Args:
            exclude_paths: Exact paths to exclude from JWT verification
            exclude_prefixes: Path prefixes to exclude from JWT verification
        """
        self.exclude_paths = exclude_paths or [
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc"
        ]
        self.exclude_prefixes = exclude_prefixes or [
            "/static/",
            "/assets/"
        ]
    
    def should_exclude_path(self, path: str) -> bool:
        """Check if path should be excluded from JWT verification"""
        # Exact path matches
        if path in self.exclude_paths:
            return True
            
        # Prefix matches
        for prefix in self.exclude_prefixes:
            if path.startswith(prefix):
                return True
                
        return False
    
    async def __call__(self, request: Request, call_next: Callable) -> JSONResponse:
        """
        Process JWT authentication for the request
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response from next handler or JWT error response
        """
        try:
            # Skip JWT verification for excluded paths
            if self.should_exclude_path(request.url.path):
                logger.debug(f"Skipping JWT verification for: {request.url.path}")
                return await call_next(request)
            
            # Extract JWT token from Authorization header
            authorization = request.headers.get("Authorization")
            if not authorization:
                logger.warning(f"Missing Authorization header: {request.url.path}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "authentication_required",
                        "message": "Missing Authorization header",
                        "details": "Please provide a valid JWT token in the Authorization header"
                    }
                )
            
            # Validate Bearer token format
            try:
                scheme, token = authorization.split(" ", 1)
                if scheme.lower() != "bearer":
                    raise ValueError("Invalid authorization scheme")
            except ValueError:
                logger.warning(f"Invalid Authorization header format: {request.url.path}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "invalid_token_format",
                        "message": "Invalid Authorization header format",
                        "details": "Use 'Bearer <token>' format"
                    }
                )
            
            # Verify JWT token
            try:
                tenant_context = await verify_jwt_token(token)
                logger.debug(f"JWT verified for tenant: {tenant_context.tenant_id}")
                
                # Store tenant context in request state
                request.state.tenant_context = tenant_context
                request.state.authenticated = True
                
                # Add tenant_id to request for backward compatibility
                request.state.tenant_id = tenant_context.tenant_id
                
            except Exception as jwt_error:
                logger.error(f"JWT verification failed: {jwt_error}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "invalid_token",
                        "message": "JWT token verification failed",
                        "details": str(jwt_error)
                    }
                )
            
            # Process request with authenticated context
            response = await call_next(request)
            
            # Add security headers to response
            response.headers["X-Tenant-ID"] = tenant_context.tenant_id
            response.headers["X-Auth-Method"] = "JWT"
            
            return response
            
        except Exception as e:
            logger.error(f"JWT middleware error: {e}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "authentication_error",
                    "message": "Authentication processing failed",
                    "details": "Please try again or contact support"
                }
            )


def get_tenant_context(request: Request) -> JWTTenantContext:
    """
    Helper function to extract tenant context from request state
    
    Args:
        request: FastAPI request object with authenticated state
        
    Returns:
        JWTTenantContext from the authenticated JWT token
        
    Raises:
        HTTPException: If no authenticated context found
    """
    if not hasattr(request.state, 'tenant_context'):
        logger.error("No tenant context found in request state")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required but no tenant context found"
        )
    
    return request.state.tenant_context


def get_tenant_id(request: Request) -> str:
    """
    Helper function to extract tenant ID from request state
    
    Args:
        request: FastAPI request object with authenticated state
        
    Returns:
        Tenant ID string from the authenticated JWT token
    """
    tenant_context = get_tenant_context(request)
    return tenant_context.tenant_id