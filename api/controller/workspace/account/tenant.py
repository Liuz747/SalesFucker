"""
Admin Tenant Management Endpoints

These endpoints are used by the backend system to sync tenant information
and public keys to the AI service. Only accessible with admin API keys.

Flow:
Backend System → POST /tenants/{tenant_id}/sync → AI Service
"""

from fastapi import APIRouter, HTTPException, status
from typing import Optional, Dict, Any, List

from .schema import TenantSyncRequest, TenantSyncResponse, TenantStatusResponse, TenantListResponse, TenantUpdateRequest
from models.tenant import TenantModel
from services.tenant_service import TenantService
from utils import get_component_logger, get_current_datetime

logger = get_component_logger(__name__, "TenantEndpoints")

# Create router with prefix
router = APIRouter(prefix="/tenants", tags=["tenant"])

@router.post("/{tenant_id}/sync", response_model=TenantSyncResponse)
async def sync_tenant(
    tenant_id: str,
    request: TenantSyncRequest
):
    """
    Sync tenant from backend system to AI service
    
    Called by backend when:
    - New company registers (creates tenant)
    - Company updates their information
    - Company changes status (active/inactive)
    """
    try:
        logger.info(f"Backend tenant sync request: {tenant_id} \n param: {request}")
        
        # Validate tenant_id matches request
        if request.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant ID in URL and request body must match"
            )
        
        # Sync tenant to AI service database
        try:
            exist = await TenantService.query(request.tenant_id)
        except Exception as e:
            logger.error(f"获取租户配置失败: {request.tenant_id}, 错误: {e}")
            raise
            
        if not exist:
            cfg = TenantModel(
                tenant_id=request.tenant_id,
                tenant_name=request.tenant_name,
                status=request.status,
                industry=request.industry,
                area_id=request.area_id,
                creator=request.creator,
                company_size=request.company_size,
            )
        else:
            cfg = exist
            cfg.status = request.status
            cfg.tenant_name = request.tenant_name
            cfg.industry = request.industry
            cfg.area_id = request.area_id
            cfg.company_size = request.company_size

        # Update features if provided
        if request.features:
            cfg.feature_flags = {feature: True for feature in request.features}

        flag = await TenantService.save(cfg)
        if flag:
            logger.info(f"租户配置已更新: {cfg.tenant_id}")
        else:
            logger.error(f"保存租户配置失败: {cfg.tenant_id}")
            raise ValueError(f"Failed to save tenant configuration for {cfg.tenant_id}")
        
        logger.info(f"Tenant sync successful: {tenant_id}")
        return TenantSyncResponse(
            tenant_id=tenant_id,
            message="Tenant synced successfully",
            synced_at=get_current_datetime(),
            features_enabled=request.features
        )
        
    except ValueError as e:
        logger.warning(f"Invalid tenant sync data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"Tenant sync failed for {tenant_id}: {e}", exc_info=True)
        
        # Provide specific error messages for database issues
        if "connection" in error_msg or "database" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Database not available: {str(e)}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Tenant sync failed: {str(e)}"
            )


@router.get("/{tenant_id}/status", response_model=TenantStatusResponse)
async def get_tenant_status(
    tenant_id: str,

):
    """
    Get tenant status from AI service
    
    Returns current tenant information stored in AI service,
    including sync status and JWT verification health.
    """
    try:
        logger.info(f"Tenant status request: {tenant_id}")
        
        try:
            cfg = await TenantService.query(tenant_id)
        except Exception as e:
            logger.error(f"获取租户配置失败: {tenant_id}, 错误: {e}")
            raise
            
        if not cfg:
            status_info = None
        else:
            status_info = TenantStatusResponse(
                tenant_id=cfg.tenant_id,
                tenant_name=cfg.tenant_name,
                status=cfg.status,
                updated_at=cfg.updated_at,
                last_access=cfg.last_access,
            )
        
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
    request: TenantUpdateRequest
):
    """
    Update tenant information
    
    Update tenant features, status, or other metadata.
    Does not update JWT public key (use sync endpoint for that).
    """
    try:
        logger.info(f"Tenant update request: {tenant_id}")
        
        try:
            cfg = await TenantService.query(tenant_id)
        except Exception as e:
            logger.error(f"获取租户配置失败: {tenant_id}, 错误: {e}")
            raise
            
        if not cfg:
            raise ValueError("Tenant not found")
        
        if request.status is not None:
            cfg.status = request.status
        
        if request.features:
            cfg.feature_flags = {feature: True for feature in request.features}
            
        flag = await TenantService.save(cfg)
        if flag:
            logger.info(f"租户配置已更新: {cfg.tenant_id}")
        else:
            logger.error(f"保存租户配置失败: {cfg.tenant_id}")
            
        result = {
            "status": "updated" if flag else "failed",
            "features": request.features or [],
        }
        
        return TenantSyncResponse(
            tenant_id=tenant_id,
            message="Tenant updated successfully",
            synced_at=get_current_datetime(),
            features_enabled=result.get("features", [])
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
    force: bool = False
):
    """
    Delete tenant from AI service
    
    Called when company cancels their subscription or is deactivated.
    This removes tenant data from AI service but preserves in backend.
    """
    try:
        logger.info(f"Tenant deletion request: {tenant_id}, force={force}")
        
        try:
            flag = await TenantService.delete(tenant_id)
            result = {"status": "deleted" if flag else "failed", "data_purged": force}
        except Exception as e:
            logger.error(f"删除租户失败: {tenant_id}, 错误: {e}")
            result = {"status": "failed", "error": str(e)}
        
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
        
        try:
            ids = await TenantService.get_all_tenants()
            items: List[Dict[str, Any]] = []
            for tid in ids:
                try:
                    cfg = await TenantService.query(tid)
                except Exception as e:
                    logger.error(f"获取租户配置失败: {tid}, 错误: {e}")
                    continue
                    
                if not cfg:
                    continue
                if status_filter == "active" and not cfg.status:
                    continue
                if status_filter == "inactive" and cfg.status:
                    continue
                items.append(
                    {
                        "tenant_id": cfg.tenant_id,
                        "tenant_name": cfg.tenant_name,
                        "status": cfg.status,
                        "updated_at": cfg.updated_at,
                        "features_enabled": list(cfg.feature_flags.keys()) if cfg.feature_flags else [],
                    }
                )
            total = len(items)
            tenants = TenantListResponse(total=total, tenants=items[offset : offset + limit])
        except Exception as e:
            logger.error(f"获取租户列表失败: {e}")
            tenants = TenantListResponse(total=0, tenants=[])
        
        return tenants
        
    except Exception as e:
        logger.error(f"List tenants failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tenant list"
        )
