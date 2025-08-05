"""
编排器工厂模块

该模块提供编排器创建和租户系统初始化的工厂函数。

核心功能:
- 编排器实例创建
- 完整租户系统初始化
- 工作流配置管理
"""

from typing import Dict, Any
from src.core import Orchestrator
from .agent_factory import create_agent_set


def get_orchestrator(tenant_id: str) -> Orchestrator:
    """
    获取或创建指定租户的智能体编排器
    
    创建LangGraph工作流的编排器实例，用于协调多智能体处理流程。
    
    参数:
        tenant_id: 租户标识符
        
    返回:
        Orchestrator: 多智能体编排器实例
    """
    return Orchestrator(tenant_id)


def create_tenant_system(
    tenant_id: str, 
    create_agents: bool = True,
    auto_register: bool = True
) -> Dict[str, Any]:
    """
    创建完整的租户多智能体系统
    
    一次性创建智能体集合和编排器，提供开箱即用的完整系统。
    
    参数:
        tenant_id: 租户标识符
        create_agents: 是否创建智能体集合，默认True
        auto_register: 是否自动注册智能体，默认True
        
    返回:
        Dict[str, Any]: 完整系统配置
        {
            "tenant_id": str,
            "orchestrator": Orchestrator,
            "agents": Dict[str, BaseAgent],
            "agent_count": int,
            "system_ready": bool
        }
    """
    system_info = {
        "tenant_id": tenant_id,
        "orchestrator": None,
        "agents": {},
        "agent_count": 0,
        "system_ready": False
    }
    
    try:
        # 创建编排器
        orchestrator = get_orchestrator(tenant_id)
        system_info["orchestrator"] = orchestrator
        
        # 可选：创建智能体集合
        if create_agents:
            agents = create_agent_set(tenant_id, auto_register=auto_register)
            system_info["agents"] = agents
            system_info["agent_count"] = len(agents)
        
        # 检查系统是否准备就绪
        system_info["system_ready"] = (
            system_info["orchestrator"] is not None and 
            (not create_agents or system_info["agent_count"] > 0)
        )
        
        return system_info
        
    except Exception as e:
        print(f"错误: 创建租户系统失败 {tenant_id}: {e}")
        system_info["error"] = str(e)
        return system_info


def get_system_status(tenant_id: str) -> Dict[str, Any]:
    """
    获取租户系统状态
    
    参数:
        tenant_id: 租户标识符
        
    返回:
        Dict[str, Any]: 系统状态信息
    """
    try:
        # 创建编排器实例以获取状态
        orchestrator = get_orchestrator(tenant_id)
        
        # 获取工作流状态
        workflow_status = orchestrator.get_workflow_status()
        
        # 获取系统健康状态
        health_status = orchestrator.get_system_health()
        
        return {
            "tenant_id": tenant_id,
            "workflow_status": workflow_status,
            "health_status": health_status,
            "timestamp": workflow_status.get("timestamp")
        }
        
    except Exception as e:
        return {
            "tenant_id": tenant_id,
            "error": str(e),
            "status": "unavailable"
        }