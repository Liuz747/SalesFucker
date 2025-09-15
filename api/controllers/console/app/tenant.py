"""
租户管理

这些端点由后端系统用于同步租户信息到AI服务。
仅允许使用管理API密钥访问。

流程:
后端系统 → POST /tenants/{tenant_id}/sync → AI服务
"""

from fastapi import APIRouter

from schemas.tenant_schema import (
    TenantSyncRequest,
    TenantSyncResponse,
    TenantStatusResponse,
    TenantUpdateRequest,
    TenantDeleteResponse
)
from ..error import (
    TenantNotFoundException,
    TenantSyncException
)
from models import TenantModel
from services import TenantService
from utils import get_component_logger, get_current_datetime

logger = get_component_logger(__name__, "TenantEndpoints")

router = APIRouter()

@router.post("/sync", response_model=TenantSyncResponse)
async def sync_tenant(request: TenantSyncRequest):
    """
    从后端系统同步租户到AI服务
    """
    try:
        logger.info(f"后端租户同步请求: {request.tenant_id}")

        tenant = TenantModel(
            tenant_id=request.tenant_id,
            tenant_name=request.tenant_name,
            industry=request.industry,
            area_id=request.area_id,
            creator=request.creator,
            company_size=request.company_size,
            feature_flags=request.features.model_dump()
        )
        flag = await TenantService.create_tenant(tenant)
        
        if not flag:
            logger.error(f"保存租户配置失败: {request.tenant_id}")
            raise TenantSyncException(request.tenant_id, "Failed to save tenant configuration")
        
        logger.info(f"租户配置已保存: {request.tenant_id}")

        return TenantSyncResponse(
            tenant_id=request.tenant_id,
            message="租户同步成功",
            synced_at=get_current_datetime(),
            features_enabled=request.features
        )

    except ValueError as e:
        logger.warning(f"无效的租户同步数据: {e}")
        raise TenantSyncException(request.tenant_id, f"验证错误: {str(e)}")
    except Exception as e:
        logger.error(f"租户同步失败 {request.tenant_id}: {e}", exc_info=True)
        raise TenantSyncException(request.tenant_id, str(e))


@router.get("/{tenant_id}/status", response_model=TenantStatusResponse)
async def get_tenant_status(tenant_id: str):
    """获取租户状态"""
    try:
        logger.info(f"租户状态请求: {tenant_id}")
        
        tenant = await TenantService.query_tenant(tenant_id)
        
        if tenant:
            return TenantStatusResponse(
                tenant_id=tenant.tenant_id,
                tenant_name=tenant.tenant_name,
                status=tenant.status,
                updated_at=tenant.updated_at,
                message="租户状态获取成功"
            )
        else:
            raise TenantNotFoundException(tenant_id)
    except Exception as e:
        logger.error(f"获取租户状态失败 {tenant_id}: {e}", exc_info=True)
        raise TenantSyncException(tenant_id, f"获取租户状态失败: {str(e)}")


@router.put("/{tenant_id}", response_model=TenantSyncResponse)
async def update_tenant(
    tenant_id: str,
    request: TenantUpdateRequest,
):
    """更新租户信息"""
    try:
        logger.info(f"租户更新请求: {tenant_id}")
        
        existing_tenant = await TenantService.query_tenant(tenant_id)
        if not existing_tenant:
            raise TenantNotFoundException(tenant_id)
        
        tenant = TenantModel(
            tenant_id=tenant_id,
            tenant_name=request.tenant_name,
            status=request.status,
            industry=request.industry,
            area_id=request.area_id,
            creator=request.creator,
            company_size=request.company_size,
            feature_flags=request.features.model_dump() if request.features else None
        )
        flag = await TenantService.update_tenant(tenant)
        
        if flag:
            logger.info(f"租户配置已更新: {tenant_id}")
        else:
            logger.error(f"保存租户配置失败: {tenant_id}")
            raise TenantSyncException(tenant_id, "更新租户配置失败")

        return TenantSyncResponse(
            tenant_id=tenant_id,
            message="租户更新成功",
            features_enabled=request.features,
            synced_at=get_current_datetime()
        )

    except ValueError as e:
        logger.warning(f"无效的租户更新数据: {e}")
        raise TenantSyncException(tenant_id, f"验证错误: {str(e)}")
    except Exception as e:
        logger.error(f"租户更新失败 {tenant_id}: {e}", exc_info=True)
        raise TenantSyncException(tenant_id, f"租户更新失败: {str(e)}")


@router.delete("/{tenant_id}", response_model=TenantDeleteResponse)
async def delete_tenant(tenant_id: str):
    """删除租户"""
    try:
        logger.info(f"租户删除请求: {tenant_id}")
        
        flag = await TenantService.delete_tenant(tenant_id)
        
        if not flag:
            logger.error(f"删除租户失败: {tenant_id}")
            raise TenantSyncException(tenant_id, "删除租户失败")
            
        return TenantDeleteResponse(
            tenant_id=tenant_id,
            deleted=True,
            message="租户删除成功"
        )

    except ValueError as e:
        logger.warning(f"租户删除验证错误: {e}")
        raise TenantSyncException(tenant_id, f"删除验证错误: {str(e)}")
    except Exception as e:
        logger.error(f"租户删除失败 {tenant_id}: {e}", exc_info=True)
        raise TenantSyncException(tenant_id, f"租户删除失败: {str(e)}")
