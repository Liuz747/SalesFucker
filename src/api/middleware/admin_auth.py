"""
Admin API key verification dependency

Used by admin endpoints (e.g., tenant sync) to authorize backend-to-backend calls.
Expects an admin API key via the `X-Admin-API-Key` header.
"""

from typing import Optional

from fastapi import Header, HTTPException, status

from config.settings import settings


def verify_admin_api_key(x_admin_api_key: Optional[str] = Header(None)) -> str:
    """
    Verify the admin API key provided in the `X-Admin-API-Key` header.

    Returns the key if valid; raises HTTP 401 if missing/invalid.
    Raises HTTP 500 if the server-side key is not configured.
    """
    configured_key = settings.admin_api_key
    if not configured_key:
        # Server misconfiguration; admin endpoints should be protected
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "ADMIN_KEY_NOT_CONFIGURED",
                "message": "Admin API key is not configured on the server",
            },
        )

    if not x_admin_api_key or x_admin_api_key != configured_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "INVALID_ADMIN_API_KEY",
                "message": "Admin API key is missing or invalid",
            },
        )

    return x_admin_api_key


