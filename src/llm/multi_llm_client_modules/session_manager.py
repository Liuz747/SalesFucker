"""
会话管理器模块

该模块负责管理多LLM客户端的会话生命周期和上下文管理。
提供会话初始化、关闭和健康检查功能。

核心功能:
- 客户端生命周期管理
- 组件初始化协调
- 健康状态监控
- 优雅关闭处理
"""

import asyncio
import time
from typing import Dict, Any, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from ..provider_config import GlobalProviderConfig
from src.utils import get_component_logger, ErrorHandler


class SessionManager:
    """
    会话管理器
    
    负责管理多LLM客户端的生命周期和会话状态。
    """
    
    def __init__(self):
        """初始化会话管理器"""
        self.logger = get_component_logger(__name__, "SessionManager")
        self.error_handler = ErrorHandler("session_manager")
        
        # 会话状态
        self.is_initialized = False
        self.is_shutting_down = False
        self.initialization_time: Optional[datetime] = None
        
        # 组件引用
        self.components = {}
        
    def set_components(self, **components):
        """设置组件引用"""
        self.components.update(components)
        self.logger.debug(f"设置组件引用: {list(components.keys())}")
    
    async def initialize_client(self, config: GlobalProviderConfig):
        """
        初始化客户端
        
        参数:
            config: 全局配置
        """
        if self.is_initialized:
            self.logger.warning("客户端已初始化，跳过重复初始化")
            return
        
        try:
            # 初始化供应商管理器
            if "provider_manager" in self.components:
                await self.components["provider_manager"].initialize()
                self.logger.info("供应商管理器初始化完成")
            
            # 设置成本配置
            if "cost_optimizer" in self.components and config.tenant_configs:
                for tenant_id, tenant_config in config.tenant_configs.items():
                    self.components["cost_optimizer"].set_cost_config(
                        tenant_id, tenant_config.cost_config
                    )
                self.logger.info("成本配置设置完成")
            
            # 标记初始化完成
            self.is_initialized = True
            self.initialization_time = datetime.now()
            
            self.logger.info("多LLM客户端初始化成功")
            
        except Exception as e:
            self.logger.error(f"客户端初始化失败: {str(e)}")
            self.error_handler.handle_error(e, {"operation": "initialize_client"})
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        执行健康检查
        
        返回:
            Dict[str, Any]: 健康状态报告
        """
        try:
            health_status = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "is_initialized": self.is_initialized,
                "initialization_time": self.initialization_time.isoformat() if self.initialization_time else None,
                "uptime_seconds": self._get_uptime_seconds(),
                "components": {}
            }
            
            # 检查各组件状态
            component_checks = {
                "provider_manager": self._check_provider_manager_health,
                "intelligent_router": self._check_router_health,
                "failover_system": self._check_failover_health,
                "cost_optimizer": self._check_cost_optimizer_health
            }
            
            for component_name, check_func in component_checks.items():
                try:
                    if component_name in self.components:
                        component_health = await check_func()
                        health_status["components"][component_name] = component_health
                    else:
                        health_status["components"][component_name] = "not_configured"
                except Exception as e:
                    health_status["components"][component_name] = f"error: {str(e)}"
            
            # 检查供应商状态
            if "provider_manager" in self.components:
                try:
                    provider_status = await self.components["provider_manager"].get_provider_status()
                    healthy_providers = sum(
                        1 for status in provider_status.values() 
                        if isinstance(status, dict) and status.get("is_healthy")
                    )
                    
                    health_status["available_providers"] = healthy_providers
                    health_status["total_providers"] = len(provider_status)
                    
                    if healthy_providers == 0:
                        health_status["status"] = "unhealthy"
                        health_status["error"] = "没有可用的供应商"
                except Exception as e:
                    health_status["provider_status_error"] = str(e)
            
            return health_status
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    async def _check_provider_manager_health(self) -> str:
        """检查供应商管理器健康状态"""
        provider_manager = self.components.get("provider_manager")
        if not provider_manager:
            return "not_available"
        
        # 简单的健康检查
        return "healthy"
    
    async def _check_router_health(self) -> str:
        """检查路由器健康状态"""
        router = self.components.get("intelligent_router")
        if not router:
            return "not_available"
        
        return "healthy"
    
    async def _check_failover_health(self) -> str:
        """检查故障转移系统健康状态"""
        failover = self.components.get("failover_system")
        if not failover:
            return "not_available"
        
        return "healthy"
    
    async def _check_cost_optimizer_health(self) -> str:
        """检查成本优化器健康状态"""
        optimizer = self.components.get("cost_optimizer")
        if not optimizer:
            return "not_available"
        
        return "healthy"
    
    def _get_uptime_seconds(self) -> float:
        """获取运行时间（秒）"""
        if not self.initialization_time:
            return 0.0
        
        return (datetime.now() - self.initialization_time).total_seconds()
    
    @asynccontextmanager
    async def request_context(
        self,
        agent_type: Optional[str] = None,
        tenant_id: Optional[str] = None,
        strategy = None
    ):
        """
        请求上下文管理器
        
        参数:
            agent_type: 智能体类型
            tenant_id: 租户ID
            strategy: 路由策略
        """
        context = {
            "agent_type": agent_type,
            "tenant_id": tenant_id,
            "strategy": strategy,
            "start_time": time.time()
        }
        
        try:
            yield context
        finally:
            # 记录请求完成时间
            context["end_time"] = time.time()
            context["duration"] = context["end_time"] - context["start_time"]
            
            self.logger.debug(
                f"请求上下文完成: 智能体={agent_type}, "
                f"租户={tenant_id}, "
                f"耗时={context['duration']:.3f}s"
            )
    
    async def shutdown(self):
        """关闭会话管理器"""
        if self.is_shutting_down:
            return
        
        self.is_shutting_down = True
        
        try:
            # 关闭供应商管理器
            if "provider_manager" in self.components:
                await self.components["provider_manager"].shutdown()
                self.logger.info("供应商管理器已关闭")
            
            # 重置状态
            self.is_initialized = False
            self.initialization_time = None
            
            self.logger.info("会话管理器已关闭")
            
        except Exception as e:
            self.logger.error(f"关闭会话管理器时出错: {str(e)}")
            self.error_handler.handle_error(e, {"operation": "shutdown"})
    
    def get_session_info(self) -> Dict[str, Any]:
        """获取会话信息"""
        return {
            "is_initialized": self.is_initialized,
            "is_shutting_down": self.is_shutting_down,
            "initialization_time": self.initialization_time.isoformat() if self.initialization_time else None,
            "uptime_seconds": self._get_uptime_seconds(),
            "component_count": len(self.components)
        }