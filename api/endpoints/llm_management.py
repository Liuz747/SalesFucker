"""
LLM管理API端点

该模块提供多LLM提供商管理相关的API端点，包括提供商配置、
状态监控、成本分析、路由优化等功能。

端点功能:
- LLM提供商配置管理
- 提供商状态和健康监控
- 成本分析和预算管理
- 路由策略配置和优化
- 性能指标和统计分析
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from ..schemas.llm import (
    LLMConfigRequest,
    ProviderStatusRequest,
    LLMStatusResponse,
    CostAnalysisResponse
)
from ..handlers.llm_handler import LLMHandler
from utils import get_component_logger
from infra.runtimes import ProviderType

logger = get_component_logger(__name__, "LLMEndpoints")

# 创建路由器
router = APIRouter(prefix="/llm", tags=["llm-management"])

# 创建处理器实例
llm_handler = LLMHandler()


@router.get("/status", response_model=LLMStatusResponse)
async def get_llm_status(

    tenant_id: str = Query(..., description="租户标识符"),
    provider: Optional[ProviderType] = Query(None, description="指定提供商"),
    include_metrics: bool = Query(True, description="是否包含性能指标"),
):
    """
    获取LLM提供商状态
    
    返回所有或指定提供商的状态信息，包括连接状态、配置信息和性能指标。
    """
    try:
        status_request = ProviderStatusRequest(
            tenant_id=tenant_id,
            provider=provider,
            include_metrics=include_metrics,
            time_range_hours=24
        )
        
        return await llm_handler.get_provider_status(
            tenant_id=tenant_id,
            status_request=status_request,
        )
        
    except Exception as e:
        logger.error(f"获取LLM状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{provider}/config")
async def configure_provider(
    provider: ProviderType,
    config: LLMConfigRequest,

):
    """
    配置LLM提供商
    
    添加或更新LLM提供商的配置信息，包括API密钥、模型参数、速率限制等。
    """
    try:
        # 设置提供商类型
        config.provider = provider
        
        return await llm_handler.configure_provider(
            tenant_id=config.tenant_id,
            config_request=config,
        )
        
    except Exception as e:
        logger.error(f"配置提供商失败 {provider}: {e}", exc_info=True)
        if "access denied" in str(e).lower():
            raise HTTPException(status_code=403, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cost-analysis", response_model=CostAnalysisResponse)
async def get_cost_analysis(

    days: int = Query(30, ge=1, le=365, description="分析天数"),
    provider: Optional[ProviderType] = Query(None, description="指定提供商"),
):
    """
    获取成本分析报告
    
    提供详细的成本分析，包括总成本、提供商分解、趋势分析和优化建议。
    """
    try:
        return await llm_handler.get_cost_analysis(
            tenant_id=tenant_id,
            days=days,
            provider=provider,
        )
        
    except Exception as e:
        logger.error(f"获取成本分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{provider}/test")
async def test_provider(
    provider: ProviderType,
    test_message: str = Query("Hello, this is a test message.", description="测试消息"),
    model_name: Optional[str] = Query(None, description="指定测试模型"),

):
    """
    测试LLM提供商连接
    
    发送测试消息验证提供商连接状态、响应时间和输出质量。
    """
    try:
        return await llm_handler.test_provider(
            provider=provider,
            test_message=test_message,
            model_name=model_name,
            tenant_id=tenant_id,
        )
        
    except Exception as e:
        logger.error(f"测试提供商失败 {provider}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{provider}/toggle")
async def toggle_provider(
    provider: ProviderType,
    enabled: bool = Query(description="启用或禁用"),

):
    """
    启用/禁用提供商
    
    快速启用或禁用指定的LLM提供商，不删除配置信息。
    """
    try:
        return await llm_handler.toggle_provider(
            provider=provider,
            enabled=enabled,
            tenant_id=tenant_id,
        )
        
    except Exception as e:
        logger.error(f"切换提供商状态失败 {provider}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
