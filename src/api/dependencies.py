"""
FastAPI依赖项模块

该模块定义了API端点的共享依赖项，包括认证、权限验证、
参数验证和公共服务注入等。

核心功能:
- 租户ID验证和提取
- 请求参数验证
- 公共服务依赖注入
- 认证和授权（预留）
- 速率限制检查
"""

from fastapi import Header, HTTPException, Depends, Request
from typing import Optional, Dict, Any
import logging

from src.agents import agent_registry, get_orchestrator
from src.factories import create_agent_set
from src.utils import get_component_logger
from ..schemas.llm import LLMProviderType

logger = get_component_logger(__name__, "APIDependencies")


async def get_tenant_id(
    tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    fallback_tenant: str = "default"
) -> str:
    """
    从请求头获取租户ID，用于多租户隔离
    
    参数:
        tenant_id: 从请求头X-Tenant-ID获取的租户ID
        fallback_tenant: 默认租户ID
        
    返回:
        str: 验证后的租户ID
        
    异常:
        HTTPException: 租户ID无效时抛出
    """
    if not tenant_id:
        tenant_id = fallback_tenant
        logger.info(f"使用默认租户ID: {tenant_id}")
    
    # 租户ID验证
    if not tenant_id.isalnum() or len(tenant_id) < 3:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_TENANT_ID",
                "message": "租户ID必须是至少3个字符的字母数字组合"
            }
        )
    
    return tenant_id


async def get_request_context(
    request: Request,
    tenant_id: str = Depends(get_tenant_id)
) -> Dict[str, Any]:
    """
    获取请求上下文信息
    
    参数:
        request: FastAPI请求对象
        tenant_id: 租户ID（通过依赖注入获取）
        
    返回:
        Dict[str, Any]: 请求上下文信息
    """
    return {
        "tenant_id": tenant_id,
        "client_ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "request_id": request.headers.get("x-request-id", "unknown"),
        "method": request.method,
        "url": str(request.url)
    }


async def get_orchestrator_service(
    tenant_id: str = Depends(get_tenant_id)
):
    """
    获取租户的编排器服务
    
    参数:
        tenant_id: 租户ID
        
    返回:
        Orchestrator: 租户的编排器实例
    """
    try:
        orchestrator = get_orchestrator(tenant_id)
        return orchestrator
    except Exception as e:
        logger.error(f"获取编排器失败，租户: {tenant_id}, 错误: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ORCHESTRATOR_UNAVAILABLE",
                "message": "编排器服务暂时不可用"
            }
        )


async def get_agent_registry_service():
    """
    获取智能体注册中心服务
    
    返回:
        AgentRegistry: 全局智能体注册中心
    """
    return agent_registry


async def validate_agent_id(
    agent_id: str,
    tenant_id: str = Depends(get_tenant_id),
    registry = Depends(get_agent_registry_service)
) -> str:
    """
    验证智能体ID是否存在且属于指定租户
    
    参数:
        agent_id: 智能体ID
        tenant_id: 租户ID
        registry: 智能体注册中心
        
    返回:
        str: 验证后的智能体ID
        
    异常:
        HTTPException: 智能体不存在或不属于租户时抛出
    """
    agent = registry.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "AGENT_NOT_FOUND",
                "message": f"智能体 {agent_id} 不存在"
            }
        )
    
    if agent.tenant_id != tenant_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "AGENT_ACCESS_DENIED",
                "message": "无权访问该智能体"
            }
        )
    
    return agent_id


# 预留：认证和授权依赖项
async def get_current_user():
    """
    获取当前用户信息（预留接口）
    
    TODO: 实现JWT token验证和用户信息提取
    """
    # 暂时返回匿名用户
    return {"user_id": "anonymous", "role": "user"}


async def require_admin_role(current_user = Depends(get_current_user)):
    """
    要求管理员权限（预留接口）
    
    TODO: 实现基于角色的访问控制
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "ADMIN_REQUIRED",
                "message": "需要管理员权限"
            }
        )
    return current_user


# LLM相关依赖项

async def get_llm_service():
    """
    获取LLM管理服务
    
    TODO: 实现LLM服务的依赖注入
    
    返回:
        LLMService: LLM管理服务实例
    """
    # 暂时返回模拟服务
    class MockLLMService:
        def __init__(self):
            self.providers = {}
            self.configs = {}
    
    return MockLLMService()


async def validate_provider_access(
    tenant_id: str,
    provider: LLMProviderType
) -> None:
    """
    验证租户对LLM提供商的访问权限
    
    参数:
        tenant_id: 租户ID
        provider: LLM提供商类型
        
    异常:
        HTTPException: 访问权限不足时抛出
    """
    # TODO: 实现基于租户的提供商访问控制
    # 暂时允许所有访问
    if not tenant_id:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_TENANT",
                "message": "无效的租户ID"
            }
        )
    
    # 检查提供商是否支持
    supported_providers = [
        LLMProviderType.OPENAI,
        LLMProviderType.ANTHROPIC,
        LLMProviderType.GEMINI,
        LLMProviderType.DEEPSEEK
    ]
    
    if provider not in supported_providers:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "UNSUPPORTED_PROVIDER",
                "message": f"不支持的LLM提供商: {provider.value}"
            }
        )