"""
多LLM系统专用API端点

该模块提供多LLM系统的专用API端点，包括供应商管理、成本追踪、
优化建议和性能监控等功能。
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from src.api.multi_llm_handlers import MultiLLMAPIHandler
from src.api.multi_llm_provider_handlers import (
    ProviderManagementHandler,
    OptimizationHandler
)
from src.utils import get_component_logger


logger = get_component_logger(__name__, "MultiLLMEndpoints")

# 创建路由器
router = APIRouter(prefix="/multi-llm", tags=["multi-llm"])

# 创建处理器实例
multi_llm_handler = MultiLLMAPIHandler()
provider_handler = ProviderManagementHandler(multi_llm_handler)
optimization_handler = OptimizationHandler(multi_llm_handler)


# 响应模型定义
class ProviderStatusResponse(BaseModel):
    """供应商状态响应模型"""
    tenant_id: Optional[str]
    providers: Dict[str, Any]
    healthy_providers: List[str]
    total_providers: int
    overall_health: str


class CostAnalysisResponse(BaseModel):
    """成本分析响应模型"""
    period_start: str
    period_end: str
    total_cost: float
    total_requests: int
    total_tokens: int
    avg_cost_per_request: float
    provider_breakdown: Dict[str, Any]
    analysis_period_hours: int
    efficiency_score: float


class OptimizationResponse(BaseModel):
    """优化建议响应模型"""
    tenant_id: Optional[str]
    total_suggestions: int
    potential_total_savings: float
    suggestions: List[Dict[str, Any]]
    priority_suggestions: List[Dict[str, Any]]


class PerformanceMetricsResponse(BaseModel):
    """性能指标响应模型"""
    global_stats: Dict[str, Any]
    performance_summary: Dict[str, Any]
    recommendations: List[Dict[str, Any]]




@router.get("/providers/status", response_model=ProviderStatusResponse)
async def get_all_providers_status(
    tenant_id: Optional[str] = Query(None, description="租户ID")
):
    """
    获取所有LLM供应商的状态信息
    
    Args:
        tenant_id: 可选的租户ID，用于获取租户特定的供应商状态
    
    Returns:
        供应商状态详情
    """
    try:
        status_data = await provider_handler.get_provider_status_all(tenant_id)
        return ProviderStatusResponse(**status_data)
        
    except Exception as e:
        logger.error(f"获取供应商状态失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取供应商状态失败: {str(e)}"
        )


@router.get("/cost/analysis", response_model=CostAnalysisResponse)
async def get_cost_analysis(
    tenant_id: Optional[str] = Query(None, description="租户ID"),
    hours: int = Query(24, description="分析时间段(小时)", ge=1, le=168)
):
    """
    获取多LLM系统的成本分析
    
    Args:
        tenant_id: 可选的租户ID
        hours: 分析时间段，默认24小时
    
    Returns:
        详细的成本分析数据
    """
    try:
        cost_data = await provider_handler.get_cost_analysis_detailed(
            tenant_id, hours
        )
        return CostAnalysisResponse(**cost_data)
        
    except Exception as e:
        logger.error(f"获取成本分析失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取成本分析失败: {str(e)}"
        )


@router.get("/optimization/suggestions", response_model=OptimizationResponse)
async def get_optimization_suggestions(
    tenant_id: Optional[str] = Query(None, description="租户ID"),
    min_savings: float = Query(0.1, description="最小节省阈值", ge=0.01, le=1.0)
):
    """
    获取LLM使用优化建议
    
    Args:
        tenant_id: 可选的租户ID
        min_savings: 最小节省阈值
    
    Returns:
        优化建议列表
    """
    try:
        optimization_data = await optimization_handler.get_optimization_recommendations(
            tenant_id, min_savings
        )
        return OptimizationResponse(**optimization_data)
        
    except Exception as e:
        logger.error(f"获取优化建议失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取优化建议失败: {str(e)}"
        )


@router.get("/performance/metrics", response_model=PerformanceMetricsResponse)
async def get_performance_metrics():
    """
    获取多LLM系统的性能指标
    
    Returns:
        性能指标和建议
    """
    try:
        metrics_data = await optimization_handler.get_performance_metrics()
        return PerformanceMetricsResponse(**metrics_data)
        
    except Exception as e:
        logger.error(f"获取性能指标失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取性能指标失败: {str(e)}"
        )








