"""
多LLM系统管理端点

提供系统管理、配置和测试相关的API端点。
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from src.api.multi_llm_handlers import MultiLLMAPIHandler
from src.utils import get_component_logger


logger = get_component_logger(__name__, "MultiLLMAdminEndpoints")

# 创建路由器
router = APIRouter(prefix="/multi-llm", tags=["multi-llm-admin"])

# 创建处理器实例
multi_llm_handler = MultiLLMAPIHandler()


class HealthCheckResponse(BaseModel):
    """健康检查响应模型"""
    status: str
    timestamp: str
    components: Dict[str, Any]
    multi_llm_ready: bool


@router.get("/health", response_model=HealthCheckResponse)
async def multi_llm_health_check():
    """
    多LLM系统健康检查
    
    Returns:
        系统健康状态
    """
    try:
        client = await multi_llm_handler.get_client()
        health_data = await client.health_check()
        
        response_data = {
            "status": "healthy" if health_data.get("status") == "ok" else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "components": health_data.get("components", {}),
            "multi_llm_ready": health_data.get("status") == "ok"
        }
        
        return HealthCheckResponse(**response_data)
        
    except Exception as e:
        logger.error(f"多LLM健康检查失败: {e}")
        # 返回不健康状态而不是抛出异常
        return HealthCheckResponse(
            status="unhealthy",
            timestamp=datetime.now().isoformat(),
            components={"error": str(e)},
            multi_llm_ready=False
        )


@router.post("/providers/{provider_type}/test")
async def test_provider_connection(
    provider_type: str,
    tenant_id: Optional[str] = Query(None, description="租户ID")
):
    """
    测试指定供应商的连接
    
    Args:
        provider_type: 供应商类型 (openai, anthropic, gemini, deepseek)
        tenant_id: 可选的租户ID
    
    Returns:
        连接测试结果
    """
    try:
        client = await multi_llm_handler.get_client()
        
        # 执行简单的测试请求
        test_messages = [{"role": "user", "content": "Hello, test connection"}]
        
        response = await client.chat_completion(
            messages=test_messages,
            tenant_id=tenant_id,
            max_tokens=10,
            temperature=0.1
        )
        
        return {
            "provider_type": provider_type,
            "tenant_id": tenant_id,
            "connection_status": "success",
            "test_response": response if isinstance(response, str) else "OK",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"供应商连接测试失败: {provider_type}, 错误: {e}")
        return {
            "provider_type": provider_type,
            "tenant_id": tenant_id,
            "connection_status": "failed",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/configuration/summary")
async def get_configuration_summary(
    tenant_id: Optional[str] = Query(None, description="租户ID")
):
    """
    获取多LLM配置摘要
    
    Args:
        tenant_id: 可选的租户ID
    
    Returns:
        配置摘要信息
    """
    try:
        client = await multi_llm_handler.get_client()
        
        # 获取供应商状态
        provider_status = await client.get_provider_status(tenant_id)
        
        # 获取全局统计
        global_stats = await client.get_global_stats()
        
        return {
            "tenant_id": tenant_id,
            "configured_providers": list(provider_status.keys()),
            "active_providers": [
                provider for provider, status in provider_status.items()
                if status.get("is_healthy", False)
            ],
            "routing_stats": global_stats.get("routing_stats", {}),
            "retry_stats": global_stats.get("retry_stats", {}),
            "cost_summary": global_stats.get("cost_summary", {}),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取配置摘要失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取配置摘要失败: {str(e)}"
        )


@router.post("/conversation/test-with-provider")
async def test_conversation_with_provider(
    tenant_id: str,
    message: str,
    preferred_provider: Optional[str] = None,
    model_name: Optional[str] = None,
    routing_strategy: Optional[str] = None
):
    """
    使用指定供应商测试对话
    
    Args:
        tenant_id: 租户ID
        message: 测试消息
        preferred_provider: 首选供应商
        model_name: 指定模型
        routing_strategy: 路由策略
    
    Returns:
        对话结果和供应商信息
    """
    try:
        client = await multi_llm_handler.get_client()
        
        # 构建测试消息
        messages = [
            {"role": "user", "content": message}
        ]
        
        # 设置路由策略
        strategy = None
        if routing_strategy:
            from src.llm.intelligent_router import RoutingStrategy
            strategy = getattr(RoutingStrategy, routing_strategy.upper(), None)
        
        # 执行对话
        response = await client.chat_completion(
            messages=messages,
            tenant_id=tenant_id,
            agent_type="test",
            model=model_name,
            strategy=strategy,
            temperature=0.7,
            max_tokens=500
        )
        
        # 获取使用的供应商信息
        provider_status = await client.get_provider_status(tenant_id)
        
        return {
            "tenant_id": tenant_id,
            "test_message": message,
            "response": response,
            "provider_used": multi_llm_handler._extract_used_provider(provider_status),
            "model_used": multi_llm_handler._extract_used_model(provider_status),
            "requested_provider": preferred_provider,
            "requested_model": model_name,
            "routing_strategy": routing_strategy,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"供应商测试对话失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"供应商测试对话失败: {str(e)}"
        )