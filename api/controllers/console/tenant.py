"""
租户管理

这些端点由后端系统用于同步租户信息到AI服务。
仅允许使用管理API密钥访问。

流程:
后端系统 → POST /tenants/{tenant_id}/sync → AI服务
"""

from fastapi import APIRouter

from libs.exceptions import (
    BaseHTTPException,
    TenantManagementException,
    TenantNotFoundException,
    TenantSyncException,
    TenantAlreadyExistsException
)
from libs.types import AccountStatus
from models import TenantModel
from schemas import (
    BaseResponse,
    TenantSyncRequest,
    TenantUpdateRequest,
)
from services import TenantService
from utils import get_component_logger

logger = get_component_logger(__name__, "TenantEndpoints")

router = APIRouter()


@router.post("/sync", response_model=BaseResponse)
async def sync_tenant(request: TenantSyncRequest):
    """
    从后端系统同步租户到AI服务
    """
    try:
        logger.info(f"后端租户同步请求: {request.tenant_id}")

        tenant = TenantModel(
            tenant_id=request.tenant_id,
            tenant_name=request.tenant_name,
            status=request.status if request.status else AccountStatus.ACTIVE,
            industry=request.industry,
            creator=request.creator
        )
        tenant_model = await TenantService.create_tenant(tenant)

        if not tenant_model:
            logger.error(f"保存租户配置失败: {request.tenant_id}")
            raise TenantSyncException(request.tenant_id, "Failed to save tenant configuration")

        logger.info(f"租户配置已保存: {tenant.tenant_id}")

        return BaseResponse(message="租户同步成功")

    except TenantAlreadyExistsException:
        raise
    except Exception as e:
        logger.error(f"租户同步失败 {request.tenant_id}: {e}", exc_info=True)
        raise TenantSyncException(request.tenant_id, str(e))


@router.get("/{tenant_id}/status", response_model=TenantModel)
async def get_tenant_status(tenant_id: str):
    """获取租户状态"""
    try:
        logger.info(f"租户状态请求: {tenant_id}")

        tenant = await TenantService.query_tenant(tenant_id)

        if tenant:
            return tenant
        else:
            raise TenantNotFoundException(tenant_id)
    except TenantNotFoundException:
        raise
    except Exception as e:
        logger.error(f"获取租户状态失败 {tenant_id}: {e}", exc_info=True)
        raise TenantManagementException


@router.post("/{tenant_id}", response_model=BaseResponse)
async def update_tenant(
    tenant_id: str,
    request: TenantUpdateRequest,
):
    """更新租户信息"""
    try:
        logger.info(f"租户更新请求: {tenant_id}")

        if not request.status:
            raise ValueError

        await TenantService.update_tenant(
            tenant_id,
            request.status
        )

        logger.info(f"租户配置已更新: {tenant_id}")

        return BaseResponse(message="租户更新成功")

    except ValueError as e:
        logger.warning(f"租户更新参数错误: {e}")
        raise TenantSyncException(tenant_id, f"租户更新参数错误: {str(e)}")
    except Exception as e:
        logger.error(f"租户更新失败 {tenant_id}: {e}", exc_info=True)
        raise TenantSyncException(tenant_id, f"租户更新失败: {str(e)}")


@router.delete("/{tenant_id}", response_model=BaseResponse)
async def delete_tenant(tenant_id: str):
    """删除租户"""
    try:
        logger.info(f"租户删除请求: {tenant_id}")

        await TenantService.delete_tenant(tenant_id)

        return BaseResponse(message="租户删除成功")

    except BaseHTTPException:
        raise
    except Exception as e:
        logger.error(f"租户删除失败 {tenant_id}: {e}", exc_info=True)
        raise TenantSyncException(tenant_id, f"租户删除失败: {str(e)}")
