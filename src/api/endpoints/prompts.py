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

from fastapi import APIRouter, HTTPException, Depends, Query, Path, status
from typing import List, Optional

from ..schemas.prompts import (
    PromptCreateRequest, PromptUpdateRequest, PromptTestRequest,
    PromptLibrarySearchRequest, PromptConfigResponse, PromptTestResponse,
    PromptLibraryResponse, PromptValidationResponse,
    AssistantPromptConfig, PromptCategory, PromptType, PromptLanguage
)
from ..handlers.prompt_handler import PromptHandler
from src.auth import get_jwt_tenant_context, JWTTenantContext
from src.utils import get_component_logger

# 创建路由器
router = APIRouter(prefix="/prompts", tags=["prompts"])
logger = get_component_logger(__name__)

# 初始化处理器
prompt_handler = PromptHandler()


@router.post("/{assistant_id}", response_model=PromptConfigResponse)
async def create_assistant_prompts(
    assistant_id: str = Path(..., description="助理ID"),
    request: PromptCreateRequest = None,
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context)
) -> PromptConfigResponse:
    """
    为助理配置提示词
    
    创建或更新助理的完整提示词配置，定义其个性、行为和交互方式。
    """
    try:
        logger.info(f"配置助理提示词: tenant={tenant_context.tenant_id}, assistant={assistant_id}")
        
        # JWT认证中已验证租户身份，无需重复检查
        
        # 验证助理ID匹配
        if request.assistant_id != assistant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请求中的助理ID与路径参数不匹配"
            )
        
        result = await prompt_handler.create_assistant_prompts(request)
        
        logger.info(f"助理提示词配置成功: {assistant_id}")
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


@router.get("/{assistant_id}", response_model=PromptConfigResponse)
async def get_assistant_prompts(
    assistant_id: str = Path(..., description="助理ID"),
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    version: Optional[str] = Query(None, description="配置版本")
) -> PromptConfigResponse:
    """
    获取助理提示词配置
    
    获取指定助理的提示词配置，包括所有个性化设置和交互规则。
    """
    try:
        logger.info(f"查询助理提示词: tenant={tenant_context.tenant_id}, assistant={assistant_id}")
        
        result = await prompt_handler.get_assistant_prompts(
            assistant_id, tenant_context.tenant_id, version
        )
        
        if not result:
            logger.warning(f"助理提示词配置不存在: {assistant_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="助理提示词配置不存在"
            )
        
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


@router.put("/{assistant_id}", response_model=PromptConfigResponse)
async def update_assistant_prompts(
    assistant_id: str = Path(..., description="助理ID"),
    request: PromptUpdateRequest = None,
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context)
) -> PromptConfigResponse:
    """
    更新助理提示词配置
    
    部分或完整更新助理的提示词配置，支持渐进式优化和调整。
    """
    try:
        logger.info(f"更新助理提示词: tenant={tenant_context.tenant_id}, assistant={assistant_id}")
        
        result = await prompt_handler.update_assistant_prompts(
            assistant_id, tenant_context.tenant_id, request
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


@router.post("/{assistant_id}/test", response_model=PromptTestResponse)
async def test_assistant_prompts(
    assistant_id: str = Path(..., description="助理ID"),
    request: PromptTestRequest = None,
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context)
) -> PromptTestResponse:
    """
    测试助理提示词效果
    
    在实际应用前测试提示词配置的效果，验证输出质量和行为一致性。
    """
    try:
        logger.info(f"测试助理提示词: tenant={tenant_context.tenant_id}, assistant={assistant_id}")
        
        result = await prompt_handler.test_assistant_prompts(
            assistant_id, tenant_context.tenant_id, request
        )
        
        logger.info(f"助理提示词测试完成: {assistant_id}, 总体评分: {result.overall_score}")
        return result
        
    except ValueError as e:
        logger.warning(f"提示词测试参数错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"助理提示词测试失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="助理提示词测试失败，请稍后重试"
        )


@router.post("/{assistant_id}/validate", response_model=PromptValidationResponse)
async def validate_assistant_prompts(
    assistant_id: str = Path(..., description="助理ID"),
    prompt_config: AssistantPromptConfig = None,
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context)
) -> PromptValidationResponse:
    """
    验证助理提示词配置
    
    检查提示词配置的有效性、安全性和合规性，提供优化建议。
    """
    try:
        logger.info(f"验证助理提示词: tenant={tenant_context.tenant_id}, assistant={assistant_id}")
        
        result = await prompt_handler.validate_assistant_prompts(
            assistant_id, tenant_context.tenant_id, prompt_config
        )
        
        logger.info(f"助理提示词验证完成: {assistant_id}, 有效性: {result.is_valid}")
        return result
        
    except ValueError as e:
        logger.warning(f"提示词验证参数错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"助理提示词验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="助理提示词验证失败，请稍后重试"
        )


@router.get("/library", response_model=PromptLibraryResponse)
async def get_prompt_library(
    category: Optional[PromptCategory] = Query(None, description="分类筛选"),
    prompt_type: Optional[PromptType] = Query(None, description="类型筛选"),
    language: Optional[PromptLanguage] = Query(PromptLanguage.CHINESE, description="语言筛选"),
    search_text: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: str = Query("rating", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context)
) -> PromptLibraryResponse:
    """
    获取提示词库
    
    浏览和搜索提示词库，获取预设的提示词模板和示例。
    """
    try:
        logger.info(f"查询提示词库: tenant={tenant_context.tenant_id}")
        
        search_request = PromptLibrarySearchRequest(
            category=category,
            prompt_type=prompt_type,
            language=language,
            search_text=search_text,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size
        )
        
        result = await prompt_handler.get_prompt_library(search_request)
        
        logger.info(f"提示词库查询成功: 返回{len(result.items)}条记录")
        return result
        
    except Exception as e:
        logger.error(f"提示词库查询失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="提示词库查询失败，请稍后重试"
        )


@router.get("/templates/{category}", response_model=PromptLibraryResponse)
async def get_prompt_templates_by_category(
    category: PromptCategory = Path(..., description="提示词分类"),
    language: PromptLanguage = Query(PromptLanguage.CHINESE, description="语言"),
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context)
) -> PromptLibraryResponse:
    """
    按分类获取提示词模板
    
    获取特定分类的提示词模板，如销售、客服、咨询等。
    """
    try:
        logger.info(f"查询分类提示词模板: tenant={tenant_context.tenant_id}, category={category}")
        
        search_request = PromptLibrarySearchRequest(
            category=category,
            language=language,
            sort_by="usage_count",
            sort_order="desc",
            page=1,
            page_size=50
        )
        
        result = await prompt_handler.get_prompt_library(search_request)
        
        logger.info(f"分类提示词模板查询成功: {category}, 返回{len(result.items)}条记录")
        return result
        
    except Exception as e:
        logger.error(f"分类提示词模板查询失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="分类提示词模板查询失败，请稍后重试"
        )


@router.post("/{assistant_id}/clone", response_model=PromptConfigResponse)
async def clone_assistant_prompts(
    assistant_id: str = Path(..., description="目标助理ID"),
    source_assistant_id: str = Query(..., description="源助理ID"),
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    modify_personality: bool = Query(False, description="是否修改个性化部分")
) -> PromptConfigResponse:
    """
    克隆助理提示词配置
    
    从一个助理克隆提示词配置到另一个助理，支持快速复制和批量配置。
    """
    try:
        logger.info(f"克隆助理提示词: tenant={tenant_context.tenant_id}, source={source_assistant_id} -> target={assistant_id}")
        
        result = await prompt_handler.clone_assistant_prompts(
            source_assistant_id, assistant_id, tenant_context.tenant_id, modify_personality
        )
        
        if not result:
            logger.warning(f"源助理提示词配置不存在: {source_assistant_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="源助理提示词配置不存在"
            )
        
        logger.info(f"助理提示词克隆成功: {source_assistant_id} -> {assistant_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"助理提示词克隆失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="助理提示词克隆失败，请稍后重试"
        )


@router.get("/{assistant_id}/history", response_model=List[PromptConfigResponse])
async def get_prompt_history(
    assistant_id: str = Path(..., description="助理ID"),
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    limit: int = Query(10, ge=1, le=50, description="历史版本数量限制")
) -> List[PromptConfigResponse]:
    """
    获取助理提示词历史版本
    
    查看助理提示词配置的历史版本，支持版本回退和对比。
    """
    try:
        logger.info(f"查询助理提示词历史: tenant={tenant_context.tenant_id}, assistant={assistant_id}")
        
        result = await prompt_handler.get_prompt_history(
            assistant_id, tenant_context.tenant_id, limit
        )
        
        logger.info(f"助理提示词历史查询成功: {assistant_id}, 返回{len(result)}个版本")
        return result
        
    except Exception as e:
        logger.error(f"助理提示词历史查询失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="助理提示词历史查询失败，请稍后重试"
        )


@router.post("/{assistant_id}/rollback", response_model=PromptConfigResponse)
async def rollback_assistant_prompts(
    assistant_id: str = Path(..., description="助理ID"),
    version: str = Query(..., description="回退到的版本"),
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context)
) -> PromptConfigResponse:
    """
    回退助理提示词配置
    
    将助理的提示词配置回退到指定的历史版本。
    """
    try:
        logger.info(f"回退助理提示词: tenant={tenant_context.tenant_id}, assistant={assistant_id}, version={version}")
        
        result = await prompt_handler.rollback_assistant_prompts(
            assistant_id, tenant_context.tenant_id, version
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