"""
提示词管理API端点

该模块提供提示词管理的REST API端点，支持基于提示词的智能体
个性化定制，包括提示词配置、测试、验证和库管理等功能。

主要端点:
- POST /v1/prompts/{assistant_id} - 配置助理提示词
- GET /v1/prompts/{assistant_id} - 获取助理提示词配置
- PUT /v1/prompts/{assistant_id} - 更新助理提示词
- POST /v1/prompts/{assistant_id}/test - 测试提示词效果
- POST /v1/prompts/{assistant_id}/validate - 验证提示词
- GET /v1/prompts/library - 获取提示词库
- GET /v1/prompts/templates - 获取提示词模板
"""

from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional

from models.prompts import PromptsModel
from schemas.prompts_schema import (
    PromptCreateRequest, PromptUpdateRequest, PromptConfigResponse, AssistantPromptConfig
)
from services.prompts_services import PromptService
from utils import get_component_logger

logger = get_component_logger(__name__, "prompts_endpoints")

# 创建路由器
router = APIRouter()


@router.post("/{assistant_id}", response_model=PromptsModel)
async def create_assistant_prompts(
        request: PromptCreateRequest,
        assistant_id: str
) -> Optional[PromptsModel]:
    """
    为助理配置提示词
    
    创建或更新助理的完整提示词配置，定义其个性、行为和交互方式。
    """
    try:
        logger.info(f"配置助理提示词: request.tenant_id={request.tenant_id}, assistant={assistant_id}")

        # JWT认证中已验证租户身份，无需重复检查

        # 验证助理ID匹配
        if request.assistant_id != assistant_id:
            return PromptConfigResponse(
                code=1001,
                message="参数不正确，请检查 body 和 query 中的 assistant_id",
            )
            # raise HTTPException(
            #     status_code=status.HTTP_400_BAD_REQUEST,
            #     detail="请求中的助理ID与路径参数不匹配"
            # )
        prompts_service = PromptService()
        result = await prompts_service.create_assistant_prompts(request)
        logger.info(f"助理提示词配置成功: {assistant_id}")
        # return NewPromptResponse(result)
        return result

    except ValueError as e:
        logger.warning(f"提示词配置参数错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"提示词配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="提示词配置失败，请稍后重试"
        )


@router.get("/{assistant_id}", response_model=PromptsModel)
async def get_assistant_prompts(
        assistant_id: str,
        version: Optional[int] = None
) -> Optional[PromptsModel]:
    """
    获取助理提示词配置
    
    获取指定助理的提示词配置，包括所有个性化设置和交互规则。
    """
    try:
        logger.info(f"查询助理提示词: assistant={assistant_id} version={version}")

        prompts_service = PromptService()
        result = await prompts_service.get_assistant_prompts(
            assistant_id, version
        )
        if not result:
            logger.warning(f"助理提示词配置不存在: {assistant_id}")
            return None
        logger.info(f"助理提示词查询成功: {assistant_id}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"助理提示词查询失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="助理提示词查询失败，请稍后重试"
        )


@router.put("/{assistant_id}", response_model=PromptsModel)
async def update_assistant_prompts(
        request: PromptUpdateRequest,
        assistant_id: str
) -> Optional[PromptsModel]:
    """
    更新助理提示词配置
    
    部分或完整更新助理的提示词配置，支持渐进式优化和调整。
    """
    try:
        logger.info(f"更新助理提示词: assistant={assistant_id}")
        prompts_service = PromptService()
        result = await prompts_service.update_assistant_prompts(
            assistant_id, request
        )
        if not result:
            logger.warning(f"助理提示词配置不存在: {assistant_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="助理提示词配置不存在"
            )
        logger.info(f"助理提示词更新成功: {assistant_id}")
        return result

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"提示词更新参数错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"助理提示词更新失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="助理提示词更新失败，请稍后重试"
        )

#
# @router.post("/{assistant_id}/test", response_model=PromptTestResponse)
# async def test_assistant_prompts(
#         request: PromptTestRequest,
#         assistant_id: str
# ) -> PromptTestResponse:
#     """
#     测试助理提示词效果
#
#     在实际应用前测试提示词配置的效果，验证输出质量和行为一致性。
#     """
#     try:
#         logger.info(f"测试助理提示词:  assistant={assistant_id}")
#
#         result = await PromptService.test_assistant_prompts(
#             assistant_id, request
#         )
#
#         logger.info(f"助理提示词测试完成: {assistant_id}, 总体评分: {result.overall_score}")
#         return result
#
#     except ValueError as e:
#         logger.warning(f"提示词测试参数错误: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=str(e)
#         )
#     except Exception as e:
#         logger.error(f"助理提示词测试失败: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="助理提示词测试失败，请稍后重试"
#         )
#
#
# @router.post("/{assistant_id}/validate", response_model=PromptValidationResponse)
# async def validate_assistant_prompts(
#         request: AssistantPromptConfig,
#         assistant_id: str
# ) -> PromptValidationResponse:
#     """
#     验证助理提示词配置
#
#     检查提示词配置的有效性、安全性和合规性，提供优化建议。
#     """
#     try:
#         logger.info(f"验证助理提示词: tenant={request.tenant_id}, assistant={assistant_id}")
#
#         result = await PromptService.validate_assistant_prompts(
#             assistant_id, request
#         )
#
#         logger.info(f"助理提示词验证完成: {assistant_id}, 有效性: {result.is_valid}")
#         return PromptConfigResponse(
#             code=0,
#             message="请求成功",
#             data=result
#         )
#
#     except ValueError as e:
#         logger.warning(f"提示词验证参数错误: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=str(e)
#         )
#     except Exception as e:
#         logger.error(f"助理提示词验证失败: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="助理提示词验证失败，请稍后重试"
#         )
#
#
# @router.get("/library", response_model=PromptLibraryResponse)
# async def get_prompt_library(
#         category: Optional[PromptCategory] = Query(None, description="分类筛选"),
#         prompt_type: Optional[PromptType] = Query(None, description="类型筛选"),
#         language: Optional[PromptLanguage] = Query(PromptLanguage.CHINESE, description="语言筛选"),
#         search_text: Optional[str] = Query(None, description="搜索关键词"),
#         sort_by: str = Query("rating", description="排序字段"),
#         sort_order: str = Query("desc", description="排序方向"),
#         page: int = Query(1, ge=1, description="页码"),
#         page_size: int = Query(20, ge=1, le=100, description="每页大小"),
#         tenant_id: str = Query(..., description="租户标识符")
# ) -> PromptLibraryResponse:
#     """
#     获取提示词库
#
#     浏览和搜索提示词库，获取预设的提示词模板和示例。
#     """
#     try:
#         logger.info(f"查询提示词库: tenant={tenant_id}")
#
#         search_request = PromptLibrarySearchRequest(
#             category=category,
#             prompt_type=prompt_type,
#             language=language,
#             search_text=search_text,
#             sort_by=sort_by,
#             sort_order=sort_order,
#             page=page,
#             page_size=page_size
#         )
#
#         prompt_service = PromptService()
#         result = await prompt_service.get_prompt_library(search_request)
#
#         logger.info(f"提示词库查询成功: 返回{len(result.items)}条记录")
#         return result
#
#     except Exception as e:
#         logger.error(f"提示词库查询失败: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="提示词库查询失败，请稍后重试"
#         )
#
#
# @router.get("/templates/{category}", response_model=PromptLibraryResponse)
# async def get_prompt_templates_by_category(
#         category: PromptCategory,
#         language: PromptLanguage = Query(PromptLanguage.CHINESE, description="语言"),
#         tenant_id: str = Query(..., description="租户标识符")
# ) -> PromptLibraryResponse:
#     """
#     按分类获取提示词模板
#
#     获取特定分类的提示词模板，如销售、客服、咨询等。
#     """
#     try:
#         logger.info(f"查询分类提示词模板: tenant={tenant_id}, category={category}")
#
#         search_request = PromptLibrarySearchRequest(
#             category=category,
#             language=language,
#             sort_by="usage_count",
#             sort_order="desc",
#             page=1,
#             page_size=50
#         )
#         prompts_service = PromptService()
#         result = await prompts_service.get_prompt_library(search_request)
#
#         logger.info(f"分类提示词模板查询成功: {category}, 返回{len(result.items)}条记录")
#         return result
#
#     except Exception as e:
#         logger.error(f"分类提示词模板查询失败: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="分类提示词模板查询失败，请稍后重试"
#         )


@router.post("/{current_assistant_id}/clone", response_model=PromptsModel)
async def clone_assistant_prompts(
        current_assistant_id: str,  # 当前数字员工是需要克隆提示词的数字员工
        source_assistant_id: str = Query(..., description="目标助理ID"),
        target_assistant_id: str = Query(..., description="源助理ID"),
        target_tenant_id: str = Query(..., description="目标助理租户ID"),
        modify_personality: bool = Query(False, description="是否修改个性化部分")
) -> PromptsModel:
    """
    克隆助理提示词配置
    
    从一个助理克隆提示词配置到另一个助理，支持快速复制和批量配置。
    """
    try:
        logger.info(
            f"克隆助理提示词: current_assistant_id={current_assistant_id}, source_assistant_id={source_assistant_id} ->"
            f" target_assistant_id={target_assistant_id} target_tenant_id={target_tenant_id}")

        if current_assistant_id != target_assistant_id:
            raise Exception(f"需要克隆的数字员工必须是当前登录的数字员工")

        prompts_service = PromptService()
        result = await prompts_service.clone_assistant_prompts(
            source_assistant_id, target_assistant_id, target_tenant_id, modify_personality
        )

        if not result:
            logger.warning(f"源助理提示词配置不存在: {source_assistant_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="源助理提示词配置不存在"
            )

        logger.info(f"助理提示词克隆成功:  current_assistant_id={current_assistant_id}, "
                    f"source_assistant_id={source_assistant_id} -> target_assistant_id={target_assistant_id}"
                    f" target_tenant_id={target_tenant_id}")
        # return NewPromptResponse(result)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"助理提示词克隆失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="助理提示词克隆失败，请稍后重试"
        )


from pydantic import BaseModel, Field


class PromptsListResp(BaseModel):
    total: int
    prompts: List[PromptsModel]


@router.get("/{assistant_id}/history", response_model=PromptsListResp)
async def get_prompt_history(
        assistant_id: str,
        # todo 目前该接口不指定指定 limit，固定只支持获取最新的 10 个
        # limit: int = Query(10, ge=1, le=50, description="历史版本数量限制")
) -> PromptsListResp:
    """
    获取助理提示词历史版本
    
    查看助理提示词配置的历史版本，支持版本回退和对比。
    """
    try:
        limit = 10
        logger.info(f"查询助理提示词历史: assistant={assistant_id} limit={limit}")

        prompt_service = PromptService()
        result = await prompt_service.get_prompt_history(
            assistant_id, limit=10
        )

        logger.info(f"助理提示词历史查询成功: {assistant_id}, limit={limit}, 返回{len(result)}个版本")
        return PromptsListResp(
            total=len(result),
            prompts=result,
        )

    except Exception as e:
        logger.error(f"助理提示词历史查询失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="助理提示词历史查询失败，请稍后重试"
        )


@router.post("/{assistant_id}/rollback", response_model=PromptsModel)
async def rollback_assistant_prompts(
        assistant_id: str,
        version: int = Query(..., description="回退到的版本")
) -> Optional[PromptsModel]:
    """
    回退助理提示词配置
    
    将助理的提示词配置回退到指定的历史版本。
    """
    try:
        logger.info(f"回退助理提示词: assistant={assistant_id}, version={version}")

        prompt_service = PromptService()
        result = await prompt_service.rollback_assistant_prompts(
            assistant_id, version
        )

        if not result:
            logger.warning(f"指定版本不存在: {assistant_id}, version={version}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定版本不存在"
            )

        logger.info(f"助理提示词回退成功: {assistant_id} -> version {version}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"助理提示词回退失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="助理提示词回退失败，请稍后重试"
        )


def NewPromptResponse(result: PromptsModel) -> PromptConfigResponse:
    return PromptConfigResponse(
        code=0,
        message="查询成功",
        success=True,
        data=PromptConfigResponse(
            assistant_id=result.assistant_id,
            tenant_id=result.tenant_id,
            config=AssistantPromptConfig(
                assistant_id=result.assistant_id,
                tenant_id=result.tenant_id,
                personality_prompt=result.personality_prompt,
                greeting_prompt=result.greeting_prompt,
                product_recommendation_prompt=result.product_recommendation_prompt,
                objection_handling_prompt=result.tenant_id,
                closing_prompt=result.closing_prompt,
                context_instructions=result.context_instructions,
                llm_parameters=result.llm_parameters,
                safety_guidelines=result.safety_guidelines,
                forbidden_topics=result.forbidden_topics,
                brand_voice=result.brand_voice,
                product_knowledge=result.product_knowledge,
                version=result.version,
                is_active=result.is_active,
            ),
            created_at=result.created_at,
            updated_at=result.updated_at
        ),
    )
