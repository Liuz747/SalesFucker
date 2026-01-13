"""
AI员工管理API端点

该模块提供AI员工管理的REST API端点，包括创建、查询、更新、
配置和统计等功能。支持完整的助理生命周期管理。

主要端点:
- POST /v1/assistants - 创建助理
- GET /v1/assistants/{assistant_id} - 获取助理详情
- PUT /v1/assistants/{assistant_id} - 更新助理
- DELETE /v1/assistants/{assistant_id} - 删除助理（软删除）
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from models import TenantModel, AssistantModel
from schemas import AssistantCreateRequest, AssistantCreateResponse, AssistantUpdateRequest, BaseResponse
from libs.exceptions import (
    BaseHTTPException,
    AssistantCreationException,
    AssistantException,
    AssistantNotFoundException,
    AssistantDeletionException,
    AssistantUpdateException
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


"""
@router.get("/", response_model=AssistantListResponse)
async def list_assistants(
        tenant_id: str = Query(..., description="租户标识符"),
        status: Optional[AssistantStatus] = Query(None, description="助理状态筛选"),
        personality: Optional[str] = Query(None, description="个性类型筛选"),
        occupation: Optional[str] = Query(None, description="数字员工职业"),
        industry: Optional[str] = Query(None, description="专业领域筛选"),
        search: Optional[str] = Query(None, description="搜索关键词"),
        sort_by: str = Query("created_at", description="排序字段"),
        sort_order: str = Query("desc", description="排序方向"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(20, ge=1, le=100, description="每页大小"),
        include_stats: bool = Query(False, description="是否包含统计信息"),
        include_config: bool = Query(False, description="是否包含详细配置")
) -> AssistantListResponse:
    
    # 获取助理列表
    # 
    # 支持多种筛选条件和排序选项的助理列表查询。
    
    try:
        logger.info(f"查询助理列表: tenant={tenant_id}")

        # 构建查询请求
        list_request = AssistantListRequest(
            tenant_id=tenant_id,
            status=status,
            personality=personality,
            occupation=occupation,
            industry=industry,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
            include_stats=include_stats,
            include_config=include_config
        )

        result = await assistant_service.list_assistants(list_request)

        logger.info(f"助理列表查询成功: 返回{len(result.assistants)}条记录")
        return result

    except Exception as e:
        logger.error(f"助理列表查询失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="助理列表查询失败，请稍后重试"
        )
"""


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

        is_delete = await AssistantService.delete_assistant(assistant_id, force)

        if is_delete:
            logger.info(f"助理删除成功: {assistant_id}")
            return BaseResponse(message="助理删除成功")
        else:
            raise AssistantNotFoundException(assistant_id)

    except BaseHTTPException:
        raise
    except Exception as e:
        logger.error(f"助理删除失败: {e}")
        raise AssistantDeletionException(assistant_id, str(e))
