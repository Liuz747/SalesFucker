"""
Tenant Management Endpoints

These endpoints are used by the backend system to sync tenant information
and public keys to the AI service. Only accessible with admin API keys.

Flow:
Backend System → POST /tenants/{tenant_id}/sync → AI Service
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status

from .schema import TenantSyncRequest, TenantSyncResponse, TenantStatusResponse, TenantListResponse, TenantUpdateRequest
from api.schemas.schema_tenant import TenantSyncRequest, TenantSyncResponse, TenantStatusResponse, TenantListResponse, TenantUpdateRequest
from models.tenant import TenantModel
from services.tenant_service import TenantService
from utils import get_component_logger, get_current_datetime
from ...schemas import SuccessResponse
from ...schemas import resp_code

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
            flag = await TenantService.upsert(
                tenant_id=request.tenant_id,
                tenant_name=request.tenant_name,
                status=request.status,
                industry=request.industry,
                area_id=request.area_id,
                creator=request.creator,
                company_size=request.company_size,
                feature_flags=request.features
            )

            if flag:
                logger.info(f"租户配置已更新: {request.tenant_id}")
            else:
                logger.error(f"保存租户配置失败: {request.tenant_id}")
                raise ValueError(f"Failed to save tenant configuration for {request.tenant_id}")

        except Exception as e:
            logger.error(f"获取或保存租户配置失败: {request.tenant_id}, 错误: {e}")
            raise

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


@router.post("/{tenant_id}/synclgp", response_model=SuccessResponse[TenantSyncResponse])
async def sync_tenant_lgp(
        tenant_id: str,
        request: TenantSyncRequest
) -> SuccessResponse[TenantSyncResponse]:
    """
    Sync tenant from backend system to AI service

    Called by backend when:
    - New company registers (creates tenant)
    - Company updates their information
    - Company changes status (active/inactive)
    """
    logger.info(f"Backend tenant sync request: {tenant_id} \n param: {request}")

    # Validate tenant_id matches request
    if request.tenant_id != tenant_id:
        return SuccessResponse(
            code=resp_code.tenant_id_not_equal_resp.code,
            message=resp_code.tenant_id_not_equal_resp.code,
        )
    # Sync tenant to AI service database
    try:
        model = await TenantService.sync_tenant(request.tenant_id, request)
        return SuccessResponse(
            code=0,
            message="success",
            data=TenantSyncResponse(
                tenant_id=tenant_id,
                message="Tenant synced successfully",
                synced_at=get_current_datetime(),
                features_enabled=request.features
            ),
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
            return SuccessResponse(
                code=resp_code.database_not_available_resp.code,
                message=resp_code.database_not_available_resp.message,
            )
        else:
            return SuccessResponse(
                code=resp_code.internal_server_error_resp.code,
                message=f"Tenant sync failed: {str(e)}",
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
        
        tenant_orm = await TenantService.query(tenant_id)
            
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
    request: TenantUpdateRequest
):
    """
    Update tenant information
    
    Update tenant features, status, or other metadata.
    Does not update JWT public key (use sync endpoint for that).
    """
    try:
        logger.info(f"Tenant update request: {tenant_id}")
        
        # Direct update using service method parameters
        flag = await TenantService.update_tenant(
            tenant_id=tenant_id,
            status=request.status,
            feature_flags=request.features
        )

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
            tenant_orms = await TenantService.get_all_tenants(status_filter, limit, offset)

            # Convert ORM objects to response format
            items = []
            for tenant in tenant_orms:
                items.append({
                    "tenant_id": tenant.tenant_id,
                    "tenant_name": tenant.tenant_name,
                    "status": tenant.status,
                    "updated_at": tenant.updated_at
                })

            total = len(items)
            tenants = TenantListResponse(total=total, tenants=items)
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
