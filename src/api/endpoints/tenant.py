"""
Admin Tenant Management Endpoints

These endpoints are used by the backend system to sync tenant information
and public keys to the AI service. Only accessible with admin API keys.

Flow:
Backend System → POST /tenants/{tenant_id}/sync → AI Service
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional

from ..schemas.tenant import (
    TenantSyncRequest,
    TenantSyncResponse, 
    TenantStatusResponse,
    TenantListResponse,
    TenantUpdateRequest
)
from ..handlers.tenant_handler import TenantHandler
from src.auth.jwt_auth import get_service_context
from src.auth.models import ServiceContext
from src.utils import get_component_logger, get_current_datetime, format_timestamp

logger = get_component_logger(__name__, "AdminTenantEndpoints")

# Create router with admin prefix
router = APIRouter(prefix="/tenants", tags=["tenant"])

# Initialize handler
tenant_handler = TenantHandler()


@router.post("/{tenant_id}/sync", response_model=TenantSyncResponse)
async def sync_tenant_from_backend(
    tenant_id: str,
    request: TenantSyncRequest,
    service: ServiceContext = Depends(get_service_context)
):
    """
    Sync tenant from backend system to AI service
    
    Called by backend when:
    - New company registers (creates tenant)
    - Company updates their information
    - Company changes status (active/inactive)
    
    This endpoint receives the tenant's PUBLIC key for JWT verification.
    """
    try:
        logger.info(f"Backend tenant sync request: {tenant_id} from service: {service.sub}")
        
        # Validate tenant_id matches request
        if request.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant ID in URL and request body must match"
            )
        
        # Sync tenant to AI service database
        result = await tenant_handler.sync_tenant(request)
        
        logger.info(f"Tenant sync successful: {tenant_id}")
        return TenantSyncResponse(
            tenant_id=tenant_id,
            sync_status="success",
            message="Tenant synced successfully",
            synced_at=get_current_datetime(),
            features_enabled=request.features,
            public_key_fingerprint=result["public_key_fingerprint"]
        )
        
    except ValueError as e:
        logger.warning(f"Invalid tenant sync data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Tenant sync failed for {tenant_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tenant sync failed"
        )


@router.get("/{tenant_id}/status", response_model=TenantStatusResponse)
async def get_tenant_status(
    tenant_id: str,
    service: ServiceContext = Depends(get_service_context)
):
    """
    Get tenant status from AI service
    
    Returns current tenant information stored in AI service,
    including sync status and JWT verification health.
    """
    try:
        logger.info(f"Tenant status request: {tenant_id}")
        
        status_info = await tenant_handler.get_tenant_status(tenant_id)
        
        if not status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant_id} not found in AI service"
            )
        
        return status_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get tenant status failed for {tenant_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tenant status"
        )


@router.put("/{tenant_id}", response_model=TenantSyncResponse)
async def update_tenant(
    tenant_id: str,
    request: TenantUpdateRequest,
    service: ServiceContext = Depends(get_service_context)
):
    """
    Update tenant information
    
    Update tenant features, status, or other metadata.
    Does not update JWT public key (use sync endpoint for that).
    """
    try:
        logger.info(f"Tenant update request: {tenant_id}")
        
        result = await tenant_handler.update_tenant(tenant_id, request)
        
        return TenantSyncResponse(
            tenant_id=tenant_id,
            sync_status="updated",
            message="Tenant updated successfully",
            synced_at=get_current_datetime(),
            features_enabled=result.get("features", []),
            public_key_fingerprint=result.get("public_key_fingerprint")
        )
        
    except ValueError as e:
        logger.warning(f"Invalid tenant update data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Tenant update failed for {tenant_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tenant update failed"
        )


@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    service: ServiceContext = Depends(get_service_context),
    force: bool = False
):
    """
    Delete tenant from AI service
    
    Called when company cancels their subscription or is deactivated.
    This removes tenant data from AI service but preserves in backend.
    """
    try:
        logger.info(f"Tenant deletion request: {tenant_id}, force={force}")
        
        result = await tenant_handler.delete_tenant(tenant_id, force=force)
        
        return {
            "tenant_id": tenant_id,
            "status": "deleted",
            "message": "Tenant removed from AI service",
            "deleted_at": get_current_datetime().isoformat(),
            "data_purged": result.get("data_purged", False)
        }
        
    except ValueError as e:
        logger.warning(f"Tenant deletion validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Tenant deletion failed for {tenant_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tenant deletion failed"
        )


@router.get("/", response_model=TenantListResponse)
async def list_tenants(
    service: ServiceContext = Depends(get_service_context),
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List all tenants in AI service
    
    Admin endpoint to view all synced tenants and their status.
    """
    try:
        logger.info(f"List tenants request: status={status_filter}, limit={limit}, offset={offset}")
        
        tenants = await tenant_handler.list_tenants(
            status_filter=status_filter,
            limit=limit,
            offset=offset
        )
        
        return tenants
        
    except Exception as e:
        logger.error(f"List tenants failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tenant list"
        )


@router.post("/bulk-sync")
async def bulk_sync_tenants(
    tenants: List[TenantSyncRequest],
    service: ServiceContext = Depends(get_service_context)
):
    """
    Bulk sync multiple tenants
    
    Used during initial deployment or bulk operations.
    Processes multiple tenant sync requests in parallel.
    """
    try:
        logger.info(f"Bulk sync request for {len(tenants)} tenants")
        
        results = await tenant_handler.bulk_sync_tenants(tenants)
        
        successful = sum(1 for r in results if r["status"] == "success")
        failed = len(results) - successful
        
        return {
            "total_tenants": len(tenants),
            "successful": successful,
            "failed": failed,
            "results": results,
            "synced_at": format_timestamp()
        }
        
    except Exception as e:
        logger.error(f"Bulk sync failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bulk tenant sync failed"
        )


# Health check for admin endpoints
@router.get("/health")
async def admin_tenant_health(
    service: ServiceContext = Depends(get_service_context)
):
    """
    Health check for admin tenant endpoints
    
    Verifies admin authentication and database connectivity.
    """
    try:
        health_status = await tenant_handler.health_check()
        
        return {
            "status": "healthy",
            "timestamp": format_timestamp(),
            "database_connected": health_status["database_connected"],
            "tenant_count": health_status["tenant_count"],
            "admin_auth": "valid"
        }
        
    except Exception as e:
        logger.error(f"Admin health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "timestamp": format_timestamp(),
            "error": str(e),
            "admin_auth": "valid"
        }