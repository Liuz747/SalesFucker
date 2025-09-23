"""
AI员工管理API端点

该模块提供AI员工管理的REST API端点，包括创建、查询、更新、
配置和统计等功能。支持完整的助理生命周期管理。

主要端点:
- POST /v1/assistants - 创建助理
- GET /v1/assistants - 获取助理列表  
- GET /v1/assistants/{assistant_id} - 获取助理详情
- PUT /v1/assistants/{assistant_id} - 更新助理
- POST /v1/assistants/{assistant_id}/config - 配置助理
- GET /v1/assistants/{assistant_id}/stats - 获取助理统计
"""

from fastapi import APIRouter, HTTPException, Query, Path, status
from typing import Optional

from ..schemas.assistants import (
    AssistantCreateRequest, AssistantUpdateRequest, AssistantConfigRequest,
    AssistantListRequest, AssistantListResponse,
    AssistantStatsResponse, AssistantOperationResponse, AssistantStatus
)
from ..services.assistant_service import AssistantService
from utils import get_component_logger
from models.assistant import AssistantModel
from ..schemas.responses import SimpleResponse

# 创建路由器
router = APIRouter()
logger = get_component_logger(__name__)

# 初始化处理器
assistant_service = AssistantService()


@router.post("/", response_model=SimpleResponse[AssistantModel], status_code=status.HTTP_201_CREATED)
async def create_assistant(
        request: AssistantCreateRequest,

) -> SimpleResponse[AssistantModel]:
    """
    创建新的AI员工
    
    创建一个新的AI员工，包括个性配置、专业领域设置和权限分配。
    """
    try:
        logger.info(f"创建助理请求: tenant={request.tenant_id}, assistant={request.assistant_id}")

        # JWT认证中已验证租户身份，无需重复检查

        result = await assistant_service.create_assistant(
            request
        )

        logger.info(f"助理创建成功: {request.assistant_id}")
        return result

    except ValueError as e:
        logger.warning(f"助理创建参数错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"助理创建失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="助理创建失败，请稍后重试"
        )


@router.get("/", response_model=AssistantListResponse)
async def list_assistants(
        tenant_id: str = Query(..., description="租户标识符"),
        status: Optional[AssistantStatus] = Query(None, description="助理状态筛选"),
        personality_type: Optional[str] = Query(None, description="个性类型筛选"),
        expertise_level: Optional[str] = Query(None, description="专业等级筛选"),
        specialization: Optional[str] = Query(None, description="专业领域筛选"),
        search: Optional[str] = Query(None, description="搜索关键词"),
        sort_by: str = Query("created_at", description="排序字段"),
        sort_order: str = Query("desc", description="排序方向"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(20, ge=1, le=100, description="每页大小"),
        include_stats: bool = Query(False, description="是否包含统计信息"),
        include_config: bool = Query(False, description="是否包含详细配置")
) -> AssistantListResponse:
    """
    获取助理列表
    
    支持多种筛选条件和排序选项的助理列表查询。
    """
    try:
        logger.info(f"查询助理列表: tenant={tenant_id}")

        # 构建查询请求
        list_request = AssistantListRequest(
            tenant_id=tenant_id,
            status=status,
            personality_type=personality_type,
            expertise_level=expertise_level,
            specialization=specialization,
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


@router.get("/{assistant_id}", response_model=Optional[SimpleResponse[AssistantModel]])
async def get_assistant(
        assistant_id: str = Path(..., description="助理ID"),
        tenant_id: str = Query(..., description="租户标识符"),
        include_stats: bool = Query(False, description="是否包含统计信息"),
        include_config: bool = Query(True, description="是否包含配置信息")
) -> Optional[SimpleResponse[AssistantModel]]:
    """
    获取助理详细信息
    
    根据助理ID获取完整的助理信息，包括配置和可选的统计数据。
    """
    try:
        logger.info(f"查询助理详情: tenant={tenant_id}, assistant={assistant_id}")

        result = await assistant_service.get_assistant(
            assistant_id, tenant_id, include_stats, include_config
        )

        if not result:
            logger.warning(f"助理不存在: {assistant_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="助理不存在"
            )

        logger.info(f"助理详情查询成功: {assistant_id} {type(result)}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"助理详情查询失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="助理详情查询失败，请稍后重试"
        )


@router.put("/{assistant_id}", response_model=SimpleResponse[AssistantModel])
async def update_assistant(
        assistant_id: str = Path(..., description="助理ID"),
        request: AssistantUpdateRequest = None,

) -> Optional[SimpleResponse[AssistantModel]]:
    """
    更新助理信息
    
    更新指定助理的配置信息，支持部分字段更新。
    """
    try:
        logger.info(f"更新助理请求: tenant={request.tenant_id}, assistant={assistant_id}")

        result = await assistant_service.update_assistant(
            assistant_id, request.tenant_id, request
        )

        if not result:
            logger.warning(f"助理不存在: {assistant_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="助理不存在"
            )

        logger.info(f"助理更新成功: {assistant_id}")
        return result

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"助理更新参数错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"助理更新失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="助理更新失败，请稍后重试"
        )


@router.delete("/{assistant_id}", response_model=SimpleResponse[AssistantOperationResponse])
async def delete_assistant(
        assistant_id: str = Path(..., description="助理ID"),
        tenant_id: str = Query(..., description="租户标识符"),
        force: bool = Query(False, description="是否强制删除（即使有活跃对话）")
) -> SimpleResponse[AssistantOperationResponse]:
    """
    删除助理
    
    删除指定的助理及其相关配置。如有活跃对话需要强制删除标志。
    """
    try:
        logger.info(f"删除助理请求: tenant={tenant_id}, assistant={assistant_id}, force={force}")

        result = await assistant_service.delete_assistant(assistant_id, tenant_id, force)

        if not result.success:
            logger.warning(f"助理删除失败: {assistant_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.result_data.get("error", "助理删除失败")
            )

        logger.info(f"助理删除成功: {assistant_id}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"助理删除失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="助理删除失败，请稍后重试"
        )
