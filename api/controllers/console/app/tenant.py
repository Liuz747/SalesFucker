"""
Tenant Management Endpoints

These endpoints are used by the backend system to sync tenant information
and public keys to the AI service. Only accessible with admin API keys.

Flow:
Backend System → POST /tenants/{tenant_id}/sync → AI Service
"""

from fastapi import APIRouter

from legacy_api.schemas import resp_code, SimpleResponse
from models import TenantOrm
from services import TenantService
from utils import get_component_logger, get_current_datetime
from schemas.tenant_schema import TenantSyncRequest, TenantSyncResponse, TenantStatusResponse, TenantUpdateRequest

logger = get_component_logger(__name__, "TenantEndpoints")

# Create router with prefix
router = APIRouter(prefix="/tenants", tags=["tenant"])

@router.post("/{tenant_id}/sync", response_model=SimpleResponse[TenantSyncResponse])
async def sync_tenant(
    tenant_id: str,
    request: TenantSyncRequest
):
    """
    Sync tenant from backend system to AI service
    """
    try:
        logger.info(f"Backend tenant sync request: {tenant_id} \n param: {request}")

        # Validate tenant_id matches request
        if request.tenant_id != tenant_id:
            return SimpleResponse(
                code=resp_code.tenant_id_not_equal_resp.code,
                message=resp_code.tenant_id_not_equal_resp.message
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
            flag = await TenantService.create_tenant(tenant_orm)
            
            if flag:
                logger.info(f"租户配置已更新: {request.tenant_id}")
            else:
                logger.error(f"保存租户配置失败: {request.tenant_id}")
                raise ValueError(f"Failed to save tenant configuration for {request.tenant_id}")
            
            return SimpleResponse[TenantSyncResponse](
                code=0,
                message="success",
                data=TenantSyncResponse(
                    tenant_id=tenant_id,
                    message="Tenant synced successfully",
                    synced_at=get_current_datetime(),
                    features_enabled=request.features
                )
            )

        except Exception as e:
            logger.error(f"获取或保存租户配置失败: {request.tenant_id}, 错误: {e}")
            return SimpleResponse(
                code=resp_code.internal_server_error_resp.code,
                message=resp_code.internal_server_error_resp.message,
                request_id=""
            )

    except ValueError as e:
        logger.warning(f"Invalid tenant sync data: {e}")
        return SimpleResponse(
            code=resp_code.value_err_resp.code,
            message=str(e)
        )
    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"Tenant sync failed for {tenant_id}: {e}", exc_info=True)

        # Provide specific error messages for database issues
        if "connection" in error_msg or "database" in error_msg:
            return SimpleResponse(
                code=resp_code.database_not_available_resp.code,
                message=f"Database not available: {str(e)}"
            )
        else:
            return SimpleResponse(
                code=resp_code.internal_server_error_resp.code,
                message=f"Tenant sync failed: {str(e)}"
            )


@router.get("/{tenant_id}/status", response_model=SimpleResponse[TenantStatusResponse])
async def get_tenant_status(tenant_id: str):
    """
    Get tenant status
    """
    try:
        logger.info(f"Tenant status request: {tenant_id}")
        
        tenant_orm = await TenantService.query_tenant(tenant_id)
        
        if tenant_orm:
            return SimpleResponse[TenantStatusResponse](
                code=0,
                message="success",
                data=TenantStatusResponse(
                    tenant_id=tenant_orm.tenant_id,
                    tenant_name=tenant_orm.tenant_name,
                    status=tenant_orm.status,
                    updated_at=tenant_orm.updated_at
                )
            )
        else:
            return SimpleResponse(
                code=resp_code.missing_resp.code,
                message=f"Tenant {tenant_id} not found in AI service"
            )
    except Exception as e:
        logger.error(f"Get tenant status failed for {tenant_id}: {e}", exc_info=True)
        return SimpleResponse(
            code=resp_code.internal_server_error_resp.code,
            message="Failed to retrieve tenant status"
        )


@router.put("/{tenant_id}", response_model=SimpleResponse[TenantSyncResponse])
async def update_tenant(
    tenant_id: str,
    request: TenantUpdateRequest,
):
    """
    Update tenant information
    """
    try:
        logger.info(f"Tenant update request: {tenant_id}")
        
        tenant_orm = TenantOrm(
            tenant_id=tenant_id,
            tenant_name=request.tenant_name,
            status=request.status,
            industry=request.industry,
            area_id=request.area_id,
            creator=request.creator,
            company_size=request.company_size,
            feature_flags=request.features.model_dump()
        )
        flag = await TenantService.update_tenant(tenant_orm)
        
        if flag:
            logger.info(f"租户配置已更新: {tenant_id}")
        else:
            logger.error(f"保存租户配置失败: {tenant_id}")
            raise ValueError(f"获取或更新租户配置失败: {tenant_id}")

        return SimpleResponse[TenantSyncResponse](
            code=0,
            message="success",
            handler_process_time=get_current_datetime(),
            data=TenantSyncResponse(
                tenant_id=tenant_id,
                message="Tenant updated successfully",
                features_enabled=request.features,
                synced_at=get_current_datetime()
            )
        )

    except ValueError as e:
        logger.warning(f"Invalid tenant update data: {e}")
        return SimpleResponse(
            code=resp_code.value_err_resp.code,
            message=str(e)
        )
    except Exception as e:
        logger.error(f"Tenant update failed for {tenant_id}: {e}", exc_info=True)
        return SimpleResponse(
            code=resp_code.internal_server_error_resp.code,
            message="Tenant update failed"
        )


@router.delete("/{tenant_id}", response_model=SimpleResponse[bool])
async def delete_tenant(tenant_id: str):
    """
    Delete tenant from AI service
    """
    try:
        logger.info(f"Tenant deletion request: {tenant_id},")
        
        flag = await TenantService.delete_tenant(tenant_id)
        
        if not flag:
            logger.error(f"删除租户失败: {tenant_id}")
            return SimpleResponse[bool](
                code=resp_code.internal_server_error_resp.code,
                message=f"Failed to delete tenant: {tenant_id}",
                data=False,
            )
        return SimpleResponse[bool](
            code=0,
            message="success",
            data=True,
            handler_process_time=get_current_datetime().isoformat()
        )

    except ValueError as e:
        logger.warning(f"Tenant deletion validation error: {e}")
        return SimpleResponse[bool](
            code=resp_code.value_err_resp.code,
            message=f"Tenant deletion validation error: {e}",
        )
    except Exception as e:
        logger.error(f"Tenant deletion failed for {tenant_id}: {e}", exc_info=True)
        return SimpleResponse[bool](
            code=resp_code.internal_server_error_resp.code,
            message=f"Tenant deletion failed for {tenant_id}"
        )
