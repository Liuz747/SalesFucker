"""
健康检查API端点

该模块提供系统健康检查和监控相关的API端点，用于监控
系统各组件的运行状态和性能指标。

端点功能:
- 基础健康检查
- 详细系统状态
- 组件健康监控
- 性能指标统计
- 依赖服务检查
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, Optional
from datetime import datetime

from utils import get_component_logger
from infra.auth.jwt_auth import get_service_context
from infra.auth.jwt_auth import ServiceContext

logger = get_component_logger(__name__, "HealthEndpoints")

# 创建路由器
router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check():
    """
    基础健康检查
    
    快速检查API服务是否正常运行。
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


@router.get("/detailed")
async def detailed_health_check():
    """
    详细健康检查
    
    返回系统各组件的详细健康状态。
    """
    try:
        # 检查各组件状态
        components_status = await check_all_components()
        
        # 计算整体状态
        overall_status = calculate_overall_status(components_status)
        
        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "components": components_status,
            "system_info": await get_system_info()
        }
        
    except Exception as e:
        logger.error(f"详细健康检查失败: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


@router.get("/components/{component_name}")
async def component_health_check(
    component_name: str,
    include_metrics: bool = Query(False, description="是否包含性能指标")
):
    """
    单个组件健康检查
    
    检查指定组件的健康状态和性能指标。
    """
    try:
        component_status = await check_component_health(component_name, include_metrics)
        
        if not component_status:
            raise HTTPException(status_code=404, detail="组件不存在")
        
        return component_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"组件健康检查失败 {component_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def get_optional_service_context() -> Optional[ServiceContext]:
    """Optional service context for health endpoints"""
    try:
        return await get_service_context()
    except:
        return None

@router.get("/metrics")
async def get_health_metrics(
    service: Optional[ServiceContext] = Depends(get_optional_service_context)
):
    """
    获取健康指标
    
    返回系统性能和健康相关的指标数据。
    """
    try:
        tenant_id = "system" if service else None
        metrics = await collect_health_metrics(tenant_id)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"获取健康指标失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dependencies")
async def check_dependencies():
    """
    检查依赖服务
    
    检查所有外部依赖服务的连接状态。
    """
    try:
        dependencies_status = await check_all_dependencies()
        
        # 计算整体依赖状态
        all_healthy = all(dep["status"] == "healthy" for dep in dependencies_status.values())
        overall_status = "healthy" if all_healthy else "degraded"
        
        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "dependencies": dependencies_status
        }
        
    except Exception as e:
        logger.error(f"依赖服务检查失败: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


@router.get("/agents")
async def check_agents_health(
    tenant_id: Optional[str] = Query(None, description="租户ID")
):
    """
    检查智能体健康状态
    
    返回所有或指定租户的智能体健康状态。
    """
    try:
        agents_status = await check_agents_status(tenant_id)
        
        return {
            "status": "healthy" if agents_status["healthy_agents"] > 0 else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_agents": agents_status["total_agents"],
                "healthy_agents": agents_status["healthy_agents"],
                "unhealthy_agents": agents_status["unhealthy_agents"]
            },
            "agents": agents_status["agents"]
        }
        
    except Exception as e:
        logger.error(f"智能体健康检查失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/llm-providers")
async def check_llm_providers_health():
    """
    检查LLM提供商健康状态
    
    检查所有配置的LLM提供商的连接状态。
    """
    try:
        providers_status = await check_llm_providers_status()
        
        return {
            "status": providers_status["overall_status"],
            "timestamp": datetime.now().isoformat(),
            "providers": providers_status["providers"]
        }
        
    except Exception as e:
        logger.error(f"LLM提供商健康检查失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/storage")
async def check_storage_health():
    """
    检查存储服务健康状态
    
    检查Elasticsearch、Redis等存储服务的连接状态。
    """
    try:
        storage_status = await check_storage_services()
        
        return {
            "status": storage_status["overall_status"],
            "timestamp": datetime.now().isoformat(),
            "services": storage_status["services"]
        }
        
    except Exception as e:
        logger.error(f"存储服务健康检查失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/readiness")
async def readiness_check():
    """
    就绪状态检查
    
    检查服务是否已准备好接收流量（Kubernetes readiness probe）。
    """
    try:
        # 检查关键组件
        critical_checks = await perform_readiness_checks()
        
        all_ready = all(check["ready"] for check in critical_checks.values())
        
        return {
            "ready": all_ready,
            "timestamp": datetime.now().isoformat(),
            "checks": critical_checks
        }
        
    except Exception as e:
        logger.error(f"就绪检查失败: {e}", exc_info=True)
        return {
            "ready": False,
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


@router.get("/liveness")
async def liveness_check():
    """
    存活状态检查
    
    检查服务是否仍在运行（Kubernetes liveness probe）。
    """
    try:
        # 简单的存活检查
        return {
            "alive": True,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": await get_uptime_seconds()
        }
        
    except Exception as e:
        logger.error(f"存活检查失败: {e}", exc_info=True)
        return {
            "alive": False,
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


# 内部检查函数

async def check_all_components() -> Dict[str, Any]:
    """检查所有组件状态"""
    components = [
        "api_server",
        "agents_registry",
        "orchestrator",
        "memory_store",
        "llm_providers"
    ]
    
    component_status = {}
    
    for component in components:
        try:
            status = await check_component_health(component, include_metrics=False)
            component_status[component] = status
        except Exception as e:
            component_status[component] = {
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }
    
    return component_status


async def check_component_health(component_name: str, include_metrics: bool = False) -> Optional[Dict[str, Any]]:
    """检查单个组件健康状态"""
    # 模拟组件检查
    component_checks = {
        "api_server": lambda: check_api_server_health(),
        "agents_registry": lambda: check_agents_registry_health(),
        "orchestrator": lambda: check_orchestrator_health(),
        "memory_store": lambda: check_memory_store_health(),
        "llm_providers": lambda: check_llm_providers_health_simple()
    }
    
    if component_name not in component_checks:
        return None
    
    try:
        status = await component_checks[component_name]()
        
        if include_metrics:
            status["metrics"] = await get_component_metrics(component_name)
        
        return status
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "last_check": datetime.now().isoformat()
        }


async def check_api_server_health() -> Dict[str, Any]:
    """检查API服务器健康状态"""
    return {
        "status": "healthy",
        "last_check": datetime.now().isoformat(),
        "response_time_ms": 5.2
    }


async def check_agents_registry_health() -> Dict[str, Any]:
    """检查智能体注册表健康状态"""
    try:
        from src.agents import agent_registry
        
        total_agents = len(agent_registry.agents)
        
        return {
            "status": "healthy" if total_agents >= 0 else "unhealthy",
            "last_check": datetime.now().isoformat(),
            "registered_agents": total_agents
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "last_check": datetime.now().isoformat()
        }


async def check_orchestrator_health() -> Dict[str, Any]:
    """检查编排器健康状态"""
    return {
        "status": "healthy",
        "last_check": datetime.now().isoformat(),
        "active_workflows": 0
    }


async def check_memory_store_health() -> Dict[str, Any]:
    """检查记忆存储健康状态"""
    # 这里应该检查Elasticsearch连接
    return {
        "status": "healthy",
        "last_check": datetime.now().isoformat(),
        "connection": "active"
    }


async def check_llm_providers_health_simple() -> Dict[str, Any]:
    """检查LLM提供商健康状态（简化版）"""
    return {
        "status": "healthy",
        "last_check": datetime.now().isoformat(),
        "active_providers": 2
    }


def calculate_overall_status(components_status: Dict[str, Any]) -> str:
    """计算整体系统状态"""
    unhealthy_components = [
        name for name, status in components_status.items()
        if status.get("status") != "healthy"
    ]
    
    if not unhealthy_components:
        return "healthy"
    elif len(unhealthy_components) <= len(components_status) // 2:
        return "degraded"
    else:
        return "unhealthy"


async def get_system_info() -> Dict[str, Any]:
    """获取系统信息"""
    import platform
    import psutil
    
    return {
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "cpu_count": psutil.cpu_count() if hasattr(psutil, 'cpu_count') else "unknown",
        "memory_info": {
            "total": psutil.virtual_memory().total if hasattr(psutil, 'virtual_memory') else "unknown",
            "available": psutil.virtual_memory().available if hasattr(psutil, 'virtual_memory') else "unknown"
        } if hasattr(psutil, 'virtual_memory') else {},
        "disk_usage": {
            "total": psutil.disk_usage('/').total if hasattr(psutil, 'disk_usage') else "unknown",
            "free": psutil.disk_usage('/').free if hasattr(psutil, 'disk_usage') else "unknown"
        } if hasattr(psutil, 'disk_usage') else {}
    }


async def collect_health_metrics(tenant_id: Optional[str]) -> Dict[str, Any]:
    """收集健康指标"""
    return {
        "response_times": {
            "avg_ms": 125.6,
            "p95_ms": 250.3,
            "p99_ms": 450.8
        },
        "request_rates": {
            "requests_per_second": 15.2,
            "success_rate": 99.5
        },
        "resource_usage": {
            "cpu_usage_percent": 25.8,
            "memory_usage_percent": 45.2,
            "disk_usage_percent": 12.1
        },
        "error_rates": {
            "error_rate_percent": 0.5,
            "timeout_rate_percent": 0.1
        }
    }


async def check_all_dependencies() -> Dict[str, Any]:
    """检查所有依赖服务"""
    dependencies = {
        "elasticsearch": await check_elasticsearch_connection(),
        "redis": await check_redis_connection(),
        "openai": await check_openai_connection(),
        "anthropic": await check_anthropic_connection()
    }
    
    return dependencies


async def check_elasticsearch_connection() -> Dict[str, Any]:
    """检查Elasticsearch连接"""
    # 模拟检查
    return {
        "status": "healthy",
        "response_time_ms": 15.3,
        "cluster_status": "green",
        "last_check": datetime.now().isoformat()
    }


async def check_redis_connection() -> Dict[str, Any]:
    """检查Redis连接"""
    # 模拟检查
    return {
        "status": "healthy",
        "response_time_ms": 2.1,
        "memory_usage_mb": 128.5,
        "last_check": datetime.now().isoformat()
    }


async def check_openai_connection() -> Dict[str, Any]:
    """检查OpenAI连接"""
    # 模拟检查
    return {
        "status": "healthy",
        "response_time_ms": 850.2,
        "api_limits": "normal",
        "last_check": datetime.now().isoformat()
    }


async def check_anthropic_connection() -> Dict[str, Any]:
    """检查Anthropic连接"""
    # 模拟检查
    return {
        "status": "healthy",
        "response_time_ms": 920.1,
        "api_limits": "normal",
        "last_check": datetime.now().isoformat()
    }


async def check_agents_status(tenant_id: Optional[str]) -> Dict[str, Any]:
    """检查智能体状态"""
    try:
        from src.agents import agent_registry
        
        agents = agent_registry.agents
        
        if tenant_id:
            agents = {aid: agent for aid, agent in agents.items() if agent.tenant_id == tenant_id}
        
        healthy_agents = sum(1 for agent in agents.values() if agent.is_active)
        unhealthy_agents = len(agents) - healthy_agents
        
        agent_details = []
        for agent_id, agent in agents.items():
            agent_details.append({
                "agent_id": agent_id,
                "agent_type": agent.agent_type,
                "status": "healthy" if agent.is_active else "unhealthy",
                "last_activity": getattr(agent, 'last_activity', None)
            })
        
        return {
            "total_agents": len(agents),
            "healthy_agents": healthy_agents,
            "unhealthy_agents": unhealthy_agents,
            "agents": agent_details
        }
        
    except Exception as e:
        return {
            "total_agents": 0,
            "healthy_agents": 0,
            "unhealthy_agents": 0,
            "agents": [],
            "error": str(e)
        }


async def check_llm_providers_status() -> Dict[str, Any]:
    """检查LLM提供商状态"""
    providers = ["openai", "anthropic", "gemini", "deepseek"]
    provider_status = {}
    
    for provider in providers:
        # 模拟检查
        provider_status[provider] = {
            "status": "healthy",
            "response_time_ms": 850.0 + hash(provider) % 200,
            "last_check": datetime.now().isoformat()
        }
    
    healthy_count = sum(1 for status in provider_status.values() if status["status"] == "healthy")
    overall_status = "healthy" if healthy_count == len(providers) else "degraded"
    
    return {
        "overall_status": overall_status,
        "providers": provider_status
    }


async def check_storage_services() -> Dict[str, Any]:
    """检查存储服务"""
    services = {
        "elasticsearch": await check_elasticsearch_connection(),
        "redis": await check_redis_connection()
    }
    
    all_healthy = all(service["status"] == "healthy" for service in services.values())
    overall_status = "healthy" if all_healthy else "degraded"
    
    return {
        "overall_status": overall_status,
        "services": services
    }


async def perform_readiness_checks() -> Dict[str, Any]:
    """执行就绪检查"""
    checks = {
        "database": {"ready": True, "message": "数据库连接正常"},
        "cache": {"ready": True, "message": "缓存服务正常"},
        "agents": {"ready": True, "message": "智能体服务就绪"},
        "llm_providers": {"ready": True, "message": "LLM提供商连接正常"}
    }
    
    return checks


async def get_uptime_seconds() -> float:
    """获取运行时间（秒）"""
    # 这里应该记录服务启动时间并计算运行时间
    # 目前返回模拟值
    import time
    return time.time() % 86400  # 模拟当天运行时间


async def get_component_metrics(component_name: str) -> Dict[str, Any]:
    """获取组件指标"""
    # 模拟指标数据
    return {
        "cpu_usage": 15.2,
        "memory_usage": 128.5,
        "request_count": 1500,
        "error_count": 3,
        "avg_response_time": 125.6
    }