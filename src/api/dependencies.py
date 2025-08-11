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

from fastapi import HTTPException, Depends, Request
from typing import Optional, Dict, Any
import logging

from src.agents import agent_registry, get_orchestrator
from src.factories import create_agent_set
from src.utils import get_component_logger
from src.external import DeviceClient, get_external_config
from src.auth import get_jwt_tenant_context, JWTTenantContext
from .schemas.llm import LLMProviderType

logger = get_component_logger(__name__, "APIDependencies")


async def get_tenant_id(
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context)
) -> str:
    """
    从JWT token中获取验证的租户ID
    
    参数:
        tenant_context: JWT验证后的租户上下文
        
    返回:
        str: 验证后的租户ID
    """
    return tenant_context.tenant_id


async def get_request_context(
    request: Request,
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context)
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
        "tenant_id": tenant_context.tenant_id,
        "tenant_context": tenant_context,
        "client_ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "request_id": request.headers.get("x-request-id", "unknown"),
        "method": request.method,
        "url": str(request.url)
    }


async def get_orchestrator_service(
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context)
):
    """
    获取租户的编排器服务
    
    参数:
        tenant_id: 租户ID
        
    返回:
        Orchestrator: 租户的编排器实例
    """
    try:
        orchestrator = get_orchestrator(tenant_context.tenant_id)
        return orchestrator
    except Exception as e:
        logger.error(f"获取编排器失败，租户: {tenant_context.tenant_id}, 错误: {e}")
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
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    registry = Depends(get_agent_registry_service)
) -> str:
    """
    验证智能体ID是否存在且属于指定租户
    
    参数:
        agent_id: 智能体ID
        tenant_context: JWT验证的租户上下文
        registry: 智能体注册中心
        
    返回:
        str: 验证后的智能体ID
        
    异常:
        HTTPException: 智能体不存在或不属于租户时抛出
    """
    # 检查智能体访问权限
    if not tenant_context.can_access_agent(agent_id):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "AGENT_ACCESS_DENIED",
                "message": f"租户无权访问智能体 {agent_id}"
            }
        )
    
    agent = registry.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "AGENT_NOT_FOUND",
                "message": f"智能体 {agent_id} 不存在"
            }
        )
    
    if agent.tenant_id != tenant_context.tenant_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "AGENT_ACCESS_DENIED",
                "message": "智能体不属于当前租户"
            }
        )
    
    return agent_id


# JWT认证和授权依赖项
async def get_current_user(
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context)
):
    """
    获取当前用户信息（从JWT token中提取）
    """
    return {
        "user_id": tenant_context.sub,
        "tenant_id": tenant_context.tenant_id,
        "roles": [role.value for role in tenant_context.roles],
        "permissions": tenant_context.permissions
    }


async def require_admin_role(
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context)
):
    """
    要求管理员权限
    """
    from src.auth.models import TenantRole
    
    if not tenant_context.has_role(TenantRole.ADMIN):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "ADMIN_REQUIRED",
                "message": "需要管理员权限"
            }
        )
    return tenant_context


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
    provider: LLMProviderType,
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context)
) -> None:
    """
    验证租户对LLM提供商的访问权限
    
    参数:
        provider: LLM提供商类型
        tenant_context: JWT验证的租户上下文
        
    异常:
        HTTPException: 访问权限不足时抛出
    """
    # 检查LLM提供商访问权限
    llm_permission = f"llm.use.{provider.value.lower()}"
    if not tenant_context.has_permission(llm_permission):
        # 如果没有特定权限，检查通用LLM权限
        if not tenant_context.has_permission("llm.use.*"):
            logger.warning(f"租户 {tenant_context.tenant_id} 无权访问LLM提供商 {provider.value}")
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "LLM_PROVIDER_ACCESS_DENIED",
                    "message": f"无权访问LLM提供商 {provider.value}"
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


# 设备相关依赖项

async def get_device_client() -> DeviceClient:
    """
    获取设备客户端实例
    
    返回:
        DeviceClient: 设备查询客户端
    """
    try:
        config = get_external_config()
        return DeviceClient(config)
    except Exception as e:
        logger.error(f"获取设备客户端失败: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DEVICE_CLIENT_UNAVAILABLE",
                "message": "设备查询服务暂时不可用"
            }
        )


async def validate_device_access(
    device_id: str,
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    device_client: DeviceClient = Depends(get_device_client)
) -> str:
    """
    验证设备是否存在且属于指定租户
    
    参数:
        device_id: 设备ID
        tenant_context: JWT验证的租户上下文
        device_client: 设备客户端
        
    返回:
        str: 验证后的设备ID
        
    异常:
        HTTPException: 设备不存在或不属于租户时抛出
    """
    # 检查设备访问权限
    if not tenant_context.can_access_device(device_id):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "DEVICE_ACCESS_DENIED",
                "message": f"租户无权访问设备 {device_id}"
            }
        )
    
    try:
        # 查询设备信息
        device_info = await device_client.get_device(device_id, tenant_context.tenant_id)
        
        if not device_info:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "DEVICE_NOT_FOUND",
                    "message": f"设备 {device_id} 不存在或不属于租户 {tenant_context.tenant_id}"
                }
            )
        
        logger.debug(f"设备验证成功: {device_id}")
        return device_id
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设备验证失败: device_id={device_id}, error={e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DEVICE_VALIDATION_FAILED",
                "message": "设备验证失败，请稍后重试"
            }
        )