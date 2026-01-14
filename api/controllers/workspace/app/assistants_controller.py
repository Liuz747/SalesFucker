"""
AI员工管理API端点

该模块提供AI员工管理的REST API端点，包括创建、查询、更新、
配置和统计等功能。支持完整的助理生命周期管理。

主要端点:
- POST /v1/assistants - 创建助理
- GET /v1/assistants/{assistant_id} - 获取助理详情
- POST /v1/assistants/{assistant_id} - 更新助理
- DELETE /v1/assistants/{assistant_id} - 删除助理（软删除）
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from libs.exceptions import (
    BaseHTTPException,
    AssistantCreationException,
    AssistantException,
    AssistantDeletionException,
    AssistantUpdateException
)
from models import TenantModel, AssistantModel
from schemas import (
    AssistantCreateRequest,
    AssistantCreateResponse,
    AssistantUpdateRequest,
    BaseResponse
)
from services import AssistantService
from utils import get_component_logger
from ..wraps import validate_and_get_tenant

logger = get_component_logger(__name__)


# 创建路由器
router = APIRouter()

@router.post("/", response_model=AssistantCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_assistant(
    request: AssistantCreateRequest,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    创建新的AI员工

    创建一个新的AI员工，包括个性配置、专业领域设置和权限分配。

    return:
        AssistantModel
    """
    try:
        logger.info(f"创建助理请求: tenant={tenant.tenant_id}")

        result = await AssistantService.create_assistant(request)

        logger.info(f"助理创建成功: {result.assistant_id}")

        return AssistantCreateResponse(
            message="助理创建成功",
            assistant_id=result.assistant_id
        )

    except BaseHTTPException:
        raise
    except Exception as e:
        logger.error(f"助理创建失败: {e}")
        raise AssistantCreationException(str(e))


@router.get("/{assistant_id}", response_model=AssistantModel)
async def get_assistant(assistant_id: UUID):
    """
    获取助理详细信息
    
    根据助理ID获取完整的助理信息。
    """
    try:
        logger.info(f"查询助理详情: assistant={assistant_id}")

        result = await AssistantService.get_assistant_by_id(assistant_id)

        logger.info(f"助理详情查询成功: {assistant_id}")
        return result

    except BaseHTTPException:
        raise
    except Exception as e:
        logger.error(f"助理详情查询失败: {e}")
        raise AssistantException()


@router.post("/{assistant_id}", response_model=BaseResponse)
async def update_assistant(
    assistant_id: UUID,
    request: AssistantUpdateRequest,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    更新助理信息
    
    更新指定助理的配置信息，支持部分字段更新。
    """
    try:
        logger.info(f"更新助理请求: assistant={assistant_id}")

        await AssistantService.update_assistant(tenant.tenant_id, assistant_id, request)

        logger.info(f"助理更新成功: {assistant_id}")
        return BaseResponse(message="助理更新成功")

    except BaseHTTPException:
        raise
    except Exception as e:
        logger.error(f"助理更新失败: {e}")
        raise AssistantUpdateException(assistant_id, str(e))


@router.delete("/{assistant_id}", response_model=BaseResponse)
async def delete_assistant(
    assistant_id: UUID,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)],
    force: bool = Query(False, description="是否强制删除（即使有活跃对话）")
):
    """
    删除助理
    
    删除指定的助理及其相关配置。如有活跃对话需要强制删除标志。
    """
    try:
        logger.info(f"删除助理请求: assistant={assistant_id}, force={force}")

        await AssistantService.delete_assistant(
            tenant.tenant_id,
            assistant_id,
            force
        )

        logger.info(f"助理删除成功: {assistant_id}")
        return BaseResponse(message="助理删除成功")

    except BaseHTTPException:
        raise
    except Exception as e:
        logger.error(f"助理删除失败: {e}")
        raise AssistantDeletionException(assistant_id, str(e))
