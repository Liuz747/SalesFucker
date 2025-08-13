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

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, Optional, List
import logging

from src.api.dependencies.llm import get_llm_service, validate_provider_access
from src.auth import get_jwt_tenant_context, JWTTenantContext
from ..schemas.llm import (
    LLMConfigRequest,
    ProviderStatusRequest,
    OptimizationRequest,
    RoutingConfigRequest,
    CostBudgetRequest,
    LLMStatusResponse,
    CostAnalysisResponse,
    OptimizationResponse,
    ProviderHealthResponse,
    ModelCapabilitiesResponse,
    RoutingStatsResponse,
    LLMProviderType
)
from ..schemas.requests import PaginationRequest
from ..exceptions import (
    LLMProviderException,
    ValidationException
)
from ..handlers.llm_handler import LLMHandler
from src.utils import get_component_logger

logger = get_component_logger(__name__, "LLMEndpoints")

# 创建路由器
router = APIRouter(prefix="/llm", tags=["llm-management"])

# 创建处理器实例
llm_handler = LLMHandler()


@router.get("/status", response_model=LLMStatusResponse)
async def get_llm_status(
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    provider: Optional[LLMProviderType] = Query(None, description="指定提供商"),
    include_metrics: bool = Query(True, description="是否包含性能指标"),
    llm_service = Depends(get_llm_service)
):
    """
    获取LLM提供商状态
    
    返回所有或指定提供商的状态信息，包括连接状态、配置信息和性能指标。
    """
    try:
        status_request = ProviderStatusRequest(
            provider=provider,
            include_metrics=include_metrics,
            time_range_hours=24
        )
        
        return await llm_handler.get_provider_status(
            tenant_id=tenant_context.tenant_id,
            status_request=status_request,
            llm_service=llm_service
        )
        
    except Exception as e:
        logger.error(f"获取LLM状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/providers/{provider}/config")
async def configure_provider(
    provider: LLMProviderType,
    config: LLMConfigRequest,
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    llm_service = Depends(get_llm_service)
):
    """
    配置LLM提供商
    
    添加或更新LLM提供商的配置信息，包括API密钥、模型参数、速率限制等。
    """
    try:
        # 验证租户对提供商的访问权限
        await validate_provider_access(provider, tenant_context)
        
        # 设置提供商类型
        config.provider = provider
        
        return await llm_handler.configure_provider(
            tenant_id=tenant_context.tenant_id,
            config_request=config,
            llm_service=llm_service
        )
        
    except Exception as e:
        logger.error(f"配置提供商失败 {provider}: {e}", exc_info=True)
        if "access denied" in str(e).lower():
            raise HTTPException(status_code=403, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers/{provider}/capabilities", response_model=ModelCapabilitiesResponse)
async def get_provider_capabilities(
    provider: LLMProviderType,
    model_name: Optional[str] = Query(None, description="指定模型名称"),
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    llm_service = Depends(get_llm_service)
):
    """
    获取提供商和模型能力信息
    
    返回指定提供商支持的模型列表、能力描述、限制条件和定价信息。
    """
    try:
        return await llm_handler.get_provider_capabilities(
            provider=provider,
            model_name=model_name,
            tenant_id=tenant_context.tenant_id,
            llm_service=llm_service
        )
        
    except Exception as e:
        logger.error(f"获取提供商能力失败 {provider}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers/health", response_model=ProviderHealthResponse)
async def get_providers_health(
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    time_range_hours: int = Query(24, ge=1, le=168, description="指标时间范围"),
    llm_service = Depends(get_llm_service)
):
    """
    获取所有提供商健康状况
    
    返回各提供商的健康状态、性能指标和告警信息。
    """
    try:
        return await llm_handler.get_providers_health(
            tenant_id=tenant_context.tenant_id,
            time_range_hours=time_range_hours,
            llm_service=llm_service
        )
        
    except Exception as e:
        logger.error(f"获取提供商健康状况失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cost-analysis", response_model=CostAnalysisResponse)
async def get_cost_analysis(
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    days: int = Query(30, ge=1, le=365, description="分析天数"),
    provider: Optional[LLMProviderType] = Query(None, description="指定提供商"),
    llm_service = Depends(get_llm_service)
):
    """
    获取成本分析报告
    
    提供详细的成本分析，包括总成本、提供商分解、趋势分析和优化建议。
    """
    try:
        return await llm_handler.get_cost_analysis(
            tenant_id=tenant_context.tenant_id,
            days=days,
            provider=provider,
            llm_service=llm_service
        )
        
    except Exception as e:
        logger.error(f"获取成本分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cost-budget", response_model=Dict[str, Any])
async def set_cost_budget(
    budget_request: CostBudgetRequest,
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    llm_service = Depends(get_llm_service)
):
    """
    设置成本预算
    
    配置月度预算限制、提供商分配比例和告警阈值。
    """
    try:
        return await llm_handler.set_cost_budget(
            tenant_id=tenant_context.tenant_id,
            budget_request=budget_request,
            llm_service=llm_service
        )
        
    except Exception as e:
        logger.error(f"设置成本预算失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/routing/stats", response_model=RoutingStatsResponse)
async def get_routing_stats(
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    days: int = Query(7, ge=1, le=30, description="统计天数"),
    agent_type: Optional[str] = Query(None, description="指定智能体类型"),
    llm_service = Depends(get_llm_service)
):
    """
    获取路由统计信息
    
    返回路由策略效果、提供商分布、智能体路由统计等信息。
    """
    try:
        return await llm_handler.get_routing_stats(
            tenant_id=tenant_context.tenant_id,
            days=days,
            agent_type=agent_type,
            llm_service=llm_service
        )
        
    except Exception as e:
        logger.error(f"获取路由统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/routing/config")
async def configure_routing(
    routing_config: RoutingConfigRequest,
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    llm_service = Depends(get_llm_service)
):
    """
    配置路由策略
    
    设置智能路由策略、智能体偏好、备用提供商和健康检查间隔。
    """
    try:
        return await llm_handler.configure_routing(
            tenant_id=tenant_context.tenant_id,
            routing_config=routing_config,
            llm_service=llm_service
        )
        
    except Exception as e:
        logger.error(f"配置路由策略失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize", response_model=OptimizationResponse)
async def optimize_llm_usage(
    optimization_request: OptimizationRequest,
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    llm_service = Depends(get_llm_service)
):
    """
    优化LLM使用策略
    
    基于指定的优化目标（成本、性能、质量、延迟）提供优化建议和自动应用。
    """
    try:
        return await llm_handler.optimize_usage(
            tenant_id=tenant_context.tenant_id,
            optimization_request=optimization_request,
            llm_service=llm_service
        )
        
    except Exception as e:
        logger.error(f"LLM使用优化失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/providers/{provider}/test")
async def test_provider(
    provider: LLMProviderType,
    test_message: str = Query("Hello, this is a test message.", description="测试消息"),
    model_name: Optional[str] = Query(None, description="指定测试模型"),
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    llm_service = Depends(get_llm_service)
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
            tenant_id=tenant_context.tenant_id,
            llm_service=llm_service
        )
        
    except Exception as e:
        logger.error(f"测试提供商失败 {provider}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/providers/{provider}/config")
async def remove_provider_config(
    provider: LLMProviderType,
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    llm_service = Depends(get_llm_service)
):
    """
    移除提供商配置
    
    删除指定提供商的配置信息，停用该提供商的使用。
    """
    try:
        return await llm_handler.remove_provider_config(
            provider=provider,
            tenant_id=tenant_context.tenant_id,
            llm_service=llm_service
        )
        
    except Exception as e:
        logger.error(f"移除提供商配置失败 {provider}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/providers/{provider}/toggle")
async def toggle_provider(
    provider: LLMProviderType,
    enabled: bool = Query(description="启用或禁用"),
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    llm_service = Depends(get_llm_service)
):
    """
    启用/禁用提供商
    
    快速启用或禁用指定的LLM提供商，不删除配置信息。
    """
    try:
        return await llm_handler.toggle_provider(
            provider=provider,
            enabled=enabled,
            tenant_id=tenant_context.tenant_id,
            llm_service=llm_service
        )
        
    except Exception as e:
        logger.error(f"切换提供商状态失败 {provider}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# 批量操作端点

@router.post("/batch/test")
async def batch_test_providers(
    providers: List[LLMProviderType] = Query(description="要测试的提供商列表"),
    test_message: str = Query("Hello, this is a batch test message.", description="测试消息"),
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    llm_service = Depends(get_llm_service)
):
    """
    批量测试多个提供商
    
    并行测试多个提供商的连接状态和响应性能。
    """
    try:
        return await llm_handler.batch_test_providers(
            providers=providers,
            test_message=test_message,
            tenant_id=tenant_context.tenant_id,
            llm_service=llm_service
        )
        
    except Exception as e:
        logger.error(f"批量测试提供商失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/comparison")
async def compare_models(
    providers: List[LLMProviderType] = Query(description="要比较的提供商"),
    criteria: List[str] = Query(["cost", "performance", "quality"], description="比较标准"),
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    llm_service = Depends(get_llm_service)
):
    """
    模型对比分析
    
    对比不同提供商的模型在成本、性能、质量等方面的表现。
    """
    try:
        return await llm_handler.compare_models(
            providers=providers,
            criteria=criteria,
            tenant_id=tenant_context.tenant_id,
            llm_service=llm_service
        )
        
    except Exception as e:
        logger.error(f"模型对比分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# 管理端点

@router.get("/admin/global-stats")
async def get_global_llm_stats(
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    llm_service = Depends(get_llm_service)
):
    """
    获取全局LLM使用统计
    
    管理员端点，返回系统范围的LLM使用统计和趋势分析。
    """
    try:
        return await llm_handler.get_global_stats(
            tenant_id=tenant_context.tenant_id,
            days=days,
            llm_service=llm_service
        )
        
    except Exception as e:
        logger.error(f"获取全局统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/maintenance")
async def perform_maintenance(
    maintenance_type: str = Query(description="维护类型", pattern="^(cleanup|optimize|reset)$"),
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    llm_service = Depends(get_llm_service)
):
    """
    执行系统维护操作
    
    管理员端点，执行清理、优化或重置等维护操作。
    """
    try:
        return await llm_handler.perform_maintenance(
            maintenance_type=maintenance_type,
            tenant_id=tenant_context.tenant_id,
            llm_service=llm_service
        )
        
    except Exception as e:
        logger.error(f"执行维护操作失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))