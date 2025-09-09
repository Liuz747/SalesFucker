"""
Tenant Management Endpoints

These endpoints are used by the backend system to sync tenant information
and public keys to the AI service. Only accessible with admin API keys.

Flow:
Backend System → POST /tenants/{tenant_id}/sync → AI Service
"""

from fastapi import APIRouter, HTTPException, status, Depends

from .schema import TenantSyncRequest, TenantSyncResponse, TenantStatusResponse, TenantListResponse, TenantUpdateRequest
from services.tenant_service import TenantService
from models.tenant import TenantOrm
from utils import get_component_logger, get_current_datetime

logger = get_component_logger(__name__, "TenantEndpoints")

# Create router with prefix
router = APIRouter(prefix="/tenants", tags=["tenant"])

async def get_tenant_service() -> TenantService:
    service = TenantService()
    await service.dispatch()
    return service

@router.post("/{tenant_id}/sync", response_model=TenantSyncResponse)
async def sync_tenant(
    tenant_id: str,
    request: TenantSyncRequest,
    service = Depends(get_tenant_service)
):
    """
    Sync tenant from backend system to AI service
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
            tenant_orm = TenantOrm(
                tenant_id=request.tenant_id,
                tenant_name=request.tenant_name,
                status=request.status,
                industry=request.industry,
                area_id=request.area_id,
                creator=request.creator,
                company_size=request.company_size,
                feature_flags=request.features.model_dump()
            )
            flag = await service.create_tenant(tenant_orm)
            
            if flag:
                logger.info(f"租户配置已更新: {request.tenant_id}")
            else:
                logger.error(f"保存租户配置失败: {request.tenant_id}")
                raise ValueError(f"Failed to save tenant configuration for {request.tenant_id}")
                
        except Exception as e:
            logger.error(f"获取或保存租户配置失败: {request.tenant_id}, 错误: {e}")
            raise
        
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
    service = Depends(get_tenant_service)
):
    """
    Get tenant status
    """
    try:
        logger.info(f"Tenant status request: {tenant_id}")
        
        tenant_orm = await service.query_tenant(tenant_id)
            
        if tenant_orm:
            return TenantStatusResponse(
                tenant_id=tenant_orm.tenant_id,
                tenant_name=tenant_orm.tenant_name,
                status=tenant_orm.status,
                updated_at=tenant_orm.updated_at
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant_id} not found in AI service"
            )
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
    service = Depends(get_tenant_service)
):
    """
    Update tenant information
    """
    try:
        logger.info(f"Tenant update request: {tenant_id}")
        
        # Direct update using service method parameters
        tenant_orm = TenantOrm(
            tenant_id=tenant_id,
            tenant_name="",
            status=request.status,
            industry=1,
            area_id=1,
            creator=1,
            feature_flags=request.features
        )
        flag = await service.update_tenant(tenant_orm)
        
        if flag:
            logger.info(f"租户配置已更新: {tenant_id}")
        else:
            logger.error(f"保存租户配置失败: {tenant_id}")
            raise ValueError(f"获取或更新租户配置失败: {tenant_id}")
        
        return TenantSyncResponse(
            tenant_id=tenant_id,
            message="Tenant updated successfully",
            updated_at=get_current_datetime(),
            features_enabled=request.features
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
    service = Depends(get_tenant_service)
):
    """
    Delete tenant from AI service
    """
    try:
        logger.info(f"Tenant deletion request: {tenant_id},")
        
        flag = await service.delete_tenant(tenant_id)
        
        if not flag:
            logger.error(f"删除租户失败: {tenant_id}")
            raise ValueError(f"Failed to delete tenant: {tenant_id}")
        
        return {
            "tenant_id": tenant_id,
            "status": "deleted",
            "message": "Tenant removed from AI service",
            "deleted_at": get_current_datetime().isoformat()
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
