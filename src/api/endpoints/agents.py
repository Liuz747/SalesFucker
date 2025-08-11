"""
智能体管理API端点

该模块提供智能体相关的API端点，包括智能体测试、状态查询、
配置管理等功能。

端点功能:
- 智能体测试和验证
- 智能体状态查询
- 智能体列表和筛选
- 智能体配置管理
- 批量操作支持
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, Optional, List
import logging

from src.api.dependencies.orchestrator import get_orchestrator_service
from src.api.dependencies.agents import get_agent_registry_service, validate_agent_id
from src.auth import get_jwt_tenant_context, JWTTenantContext
from ..schemas.agents import (
    AgentTestRequest,
    AgentBatchTestRequest,
    AgentConfigUpdateRequest,
    AgentStatusResponse,
    AgentListResponse,
    AgentTestResponse,
    AgentBatchTestResponse,
    AgentOperationResponse
)
from ..schemas.requests import PaginationRequest
from ..exceptions import (
    AgentNotFoundException,
    AgentUnavailableException,
    ValidationException
)
from ..handlers.agent_handler import AgentHandler
from src.utils import get_component_logger

logger = get_component_logger(__name__, "AgentEndpoints")

# 创建路由器
router = APIRouter(prefix="/agents", tags=["agents"])

# 创建处理器实例
agent_handler = AgentHandler()


@router.get("/", response_model=AgentListResponse)
async def list_agents(
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    pagination: PaginationRequest = Depends(),
    agent_type: Optional[str] = Query(None, description="按智能体类型筛选"),
    status: Optional[str] = Query(None, description="按状态筛选"),
    registry = Depends(get_agent_registry_service)
):
    """
    获取智能体列表
    
    支持分页、筛选和排序功能。
    """
    try:
        return await agent_handler.list_agents(
            tenant_id=tenant_context.tenant_id,
            pagination=pagination,
            filters={"agent_type": agent_type, "status": status},
            registry=registry
        )
    except Exception as e:
        logger.error(f"获取智能体列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}", response_model=AgentStatusResponse)
async def get_agent_status(
    agent_id: str = Depends(validate_agent_id),
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    registry = Depends(get_agent_registry_service)
):
    """
    获取特定智能体的状态信息
    
    包括健康状态、性能指标和最近错误信息。
    """
    try:
        return await agent_handler.get_agent_status(
            agent_id=agent_id,
            tenant_id=tenant_context.tenant_id,
            registry=registry
        )
    except Exception as e:
        logger.error(f"获取智能体状态失败 {agent_id}: {e}", exc_info=True)
        if "not found" in str(e).lower():
            raise AgentNotFoundException(agent_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_id}/test", response_model=AgentTestResponse)
async def test_agent(
    request: AgentTestRequest,
    agent_id: str = Depends(validate_agent_id),
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    registry = Depends(get_agent_registry_service)
):
    """
    测试特定智能体
    
    支持功能测试、性能测试和集成测试。
    """
    try:
        return await agent_handler.test_agent(
            agent_id=agent_id,
            test_request=request,
            tenant_id=tenant_context.tenant_id,
            registry=registry
        )
    except Exception as e:
        logger.error(f"智能体测试失败 {agent_id}: {e}", exc_info=True)
        if "unavailable" in str(e).lower():
            raise AgentUnavailableException(agent_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-test", response_model=AgentBatchTestResponse)
async def batch_test_agents(
    request: AgentBatchTestRequest,
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    registry = Depends(get_agent_registry_service)
):
    """
    批量测试多个智能体
    
    支持并行执行和详细的测试报告。
    """
    try:
        return await agent_handler.batch_test_agents(
            batch_request=request,
            tenant_id=tenant_context.tenant_id,
            registry=registry
        )
    except Exception as e:
        logger.error(f"批量测试失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{agent_id}/config", response_model=AgentOperationResponse)
async def update_agent_config(
    request: AgentConfigUpdateRequest,
    agent_id: str = Depends(validate_agent_id),
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    registry = Depends(get_agent_registry_service)
):
    """
    更新智能体配置
    
    支持增量更新和完全替换两种模式。
    """
    try:
        return await agent_handler.update_agent_config(
            agent_id=agent_id,
            config_request=request,
            tenant_id=tenant_context.tenant_id,
            registry=registry
        )
    except Exception as e:
        logger.error(f"更新智能体配置失败 {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_id}/activate", response_model=AgentOperationResponse)
async def activate_agent(
    agent_id: str = Depends(validate_agent_id),
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    registry = Depends(get_agent_registry_service)
):
    """
    激活智能体
    
    使智能体开始处理消息。
    """
    try:
        return await agent_handler.activate_agent(
            agent_id=agent_id,
            tenant_id=tenant_context.tenant_id,
            registry=registry
        )
    except Exception as e:
        logger.error(f"激活智能体失败 {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_id}/deactivate", response_model=AgentOperationResponse)
async def deactivate_agent(
    agent_id: str = Depends(validate_agent_id),
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    registry = Depends(get_agent_registry_service)
):
    """
    停用智能体
    
    停止智能体处理新消息。
    """
    try:
        return await agent_handler.deactivate_agent(
            agent_id=agent_id,
            tenant_id=tenant_context.tenant_id,
            registry=registry
        )
    except Exception as e:
        logger.error(f"停用智能体失败 {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_id}/restart", response_model=AgentOperationResponse)
async def restart_agent(
    agent_id: str = Depends(validate_agent_id),
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    registry = Depends(get_agent_registry_service)
):
    """
    重启智能体
    
    停用后重新激活智能体，用于应用配置更改。
    """
    try:
        return await agent_handler.restart_agent(
            agent_id=agent_id,
            tenant_id=tenant_context.tenant_id,
            registry=registry
        )
    except Exception as e:
        logger.error(f"重启智能体失败 {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# 已废弃的不安全端点 - 使用JWT认证替代
# 这些端点存在安全风险，应使用新的JWT认证端点

@router.post("/tenant/{tenant_id}/compliance/test")
async def test_compliance_agent_legacy(
    tenant_id: str,
    test_message: str,
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    registry = Depends(get_agent_registry_service)
):
    """
    测试合规智能体（已废弃的不安全端点）
    
    警告: 此端点已废弃，存在安全风险。请使用 /agents/{agent_id}/test 端点。
    """
    logger.warning(
        f"使用已废弃的不安全端点: /tenant/{tenant_id}/compliance/test, "
        f"实际租户: {tenant_context.tenant_id}"
    )
    
    # 验证JWT中的租户ID与URL中的匹配
    if tenant_context.tenant_id != tenant_id:
        raise HTTPException(
            status_code=403, 
            detail=f"租户ID不匹配，拒绝访问。请使用新的安全端点。"
        )
    
    try:
        agent_id = f"compliance_{tenant_context.tenant_id}"
        request = AgentTestRequest(test_message=test_message)
        
        return await agent_handler.test_agent(
            agent_id=agent_id,
            test_request=request,
            tenant_id=tenant_context.tenant_id,
            registry=registry
        )
    except Exception as e:
        logger.error(f"合规测试失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"合规测试失败: {str(e)}")


@router.post("/tenant/{tenant_id}/sales/test")
async def test_sales_agent_legacy(
    tenant_id: str,
    test_message: str,
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    registry = Depends(get_agent_registry_service)
):
    """
    测试销售智能体（已废弃的不安全端点）
    
    警告: 此端点已废弃，存在安全风险。请使用 /agents/{agent_id}/test 端点。
    """
    logger.warning(
        f"使用已废弃的不安全端点: /tenant/{tenant_id}/sales/test, "
        f"实际租户: {tenant_context.tenant_id}"
    )
    
    # 验证JWT中的租户ID与URL中的匹配
    if tenant_context.tenant_id != tenant_id:
        raise HTTPException(
            status_code=403, 
            detail=f"租户ID不匹配，拒绝访问。请使用新的安全端点。"
        )
    
    try:
        agent_id = f"sales_{tenant_context.tenant_id}"
        request = AgentTestRequest(test_message=test_message)
        
        return await agent_handler.test_agent(
            agent_id=agent_id,
            test_request=request,
            tenant_id=tenant_context.tenant_id,
            registry=registry
        )
    except Exception as e:
        logger.error(f"销售测试失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"销售测试失败: {str(e)}")


@router.post("/tenant/{tenant_id}/sentiment/test")
async def test_sentiment_agent_legacy(
    tenant_id: str,
    test_message: str,
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    registry = Depends(get_agent_registry_service)
):
    """
    测试情感分析智能体（已废弃的不安全端点）
    
    警告: 此端点已废弃，存在安全风险。请使用 /agents/{agent_id}/test 端点。
    """
    logger.warning(
        f"使用已废弃的不安全端点: /tenant/{tenant_id}/sentiment/test, "
        f"实际租户: {tenant_context.tenant_id}"
    )
    
    # 验证JWT中的租户ID与URL中的匹配
    if tenant_context.tenant_id != tenant_id:
        raise HTTPException(
            status_code=403, 
            detail=f"租户ID不匹配，拒绝访问。请使用新的安全端点。"
        )
    
    try:
        agent_id = f"sentiment_{tenant_context.tenant_id}"
        request = AgentTestRequest(test_message=test_message)
        
        return await agent_handler.test_agent(
            agent_id=agent_id,
            test_request=request,
            tenant_id=tenant_context.tenant_id,
            registry=registry
        )
    except Exception as e:
        logger.error(f"情感分析测试失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"情感分析测试失败: {str(e)}")


@router.get("/tenant/{tenant_id}/registry/status")
async def get_tenant_registry_status_legacy(
    tenant_id: str,
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    registry = Depends(get_agent_registry_service)
):
    """
    获取租户智能体注册状态（已废弃的不安全端点）
    
    警告: 此端点已废弃，存在安全风险。请使用 /agents/ 端点。
    """
    logger.warning(
        f"使用已废弃的不安全端点: /tenant/{tenant_id}/registry/status, "
        f"实际租户: {tenant_context.tenant_id}"
    )
    
    # 验证JWT中的租户ID与URL中的匹配
    if tenant_context.tenant_id != tenant_id:
        raise HTTPException(
            status_code=403, 
            detail=f"租户ID不匹配，拒绝访问。请使用新的安全端点。"
        )
    
    try:
        return await agent_handler.get_tenant_registry_status(
            tenant_id=tenant_context.tenant_id,
            registry=registry
        )
    except Exception as e:
        logger.error(f"获取注册状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))