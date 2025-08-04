"""
多LLM客户端组件模块

该模块包含会话管理和统计收集等辅助组件。
从原 multi_llm_client_modules 目录合并而来。

核心组件:
- SessionManager: 会话生命周期管理
- StatsCollector: 性能统计收集
"""

import asyncio
import time
from typing import Dict, Any, Optional, Union, AsyncGenerator
from datetime import datetime
from contextlib import asynccontextmanager
from collections import defaultdict

from .base_provider import LLMRequest, LLMResponse
from .provider_config import GlobalProviderConfig
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
        """初始化客户端"""
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
        """执行健康检查"""
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
        return "healthy"
    
    async def _check_router_health(self) -> str:
        """检查路由器健康状态"""
        router = self.components.get("intelligent_router")
        if not router:
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
        """请求上下文管理器"""
        context = {
            "agent_type": agent_type,
            "tenant_id": tenant_id,
            "strategy": strategy,
            "start_time": time.time()
        }
        
        try:
            yield context
        finally:
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


class StatsCollector:
    """
    统计收集器
    
    负责收集和维护多LLM客户端的各种统计信息。
    """
    
    def __init__(self):
        """初始化统计收集器"""
        self.logger = get_component_logger(__name__, "StatsCollector")
        
        # 基础统计
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time": 0.0,
            "provider_usage": defaultdict(int),
            "cost_metrics": defaultdict(float)
        }
        
        # 详细统计
        self.detailed_stats = {
            "agent_type_usage": defaultdict(int),
            "tenant_usage": defaultdict(int),
            "model_usage": defaultdict(int),
            "error_types": defaultdict(int),
            "avg_response_times": defaultdict(list),
            "hourly_usage": defaultdict(int)
        }
    
    def record_request_start(self, request: LLMRequest) -> str:
        """记录请求开始"""
        session_id = f"{request.request_id}_{int(time.time())}"
        
        # 更新基础统计
        self.stats["total_requests"] += 1
        
        # 更新详细统计
        if request.agent_type:
            self.detailed_stats["agent_type_usage"][request.agent_type] += 1
        
        if request.tenant_id:
            self.detailed_stats["tenant_usage"][request.tenant_id] += 1
        
        # 小时级使用统计
        hour_key = datetime.now().strftime("%Y-%m-%d_%H")
        self.detailed_stats["hourly_usage"][hour_key] += 1
        
        self.logger.debug(f"记录请求开始: {request.request_id}")
        return session_id
    
    def record_request_success(
        self,
        request: LLMRequest,
        response: Union[LLMResponse, AsyncGenerator],
        processing_time: float
    ):
        """记录成功请求"""
        # 更新成功统计
        self.stats["successful_requests"] += 1
        self.stats["total_response_time"] += processing_time
        
        # 记录供应商使用
        if isinstance(response, LLMResponse):
            provider = response.provider_type.value
            self.stats["provider_usage"][provider] += 1
            
            # 记录模型使用
            if response.model:
                self.detailed_stats["model_usage"][response.model] += 1
            
            # 记录响应时间
            self.detailed_stats["avg_response_times"][provider].append(processing_time)
            
            # 保持响应时间列表大小
            if len(self.detailed_stats["avg_response_times"][provider]) > 1000:
                self.detailed_stats["avg_response_times"][provider] = \
                    self.detailed_stats["avg_response_times"][provider][-500:]
        
        self.logger.debug(f"记录成功请求: {request.request_id}, 耗时: {processing_time:.3f}s")
    
    def record_request_failure(
        self,
        request: LLMRequest,
        error: Exception,
        processing_time: float
    ):
        """记录失败请求"""
        # 更新失败统计
        self.stats["failed_requests"] += 1
        
        # 记录错误类型
        error_type = type(error).__name__
        self.detailed_stats["error_types"][error_type] += 1
        
        self.logger.debug(f"记录失败请求: {request.request_id}, 错误: {error_type}")
    
    def record_cost(
        self,
        provider_type: str,
        cost: float,
        agent_type: Optional[str] = None
    ):
        """记录成本"""
        self.stats["cost_metrics"][provider_type] += cost
        
        if agent_type:
            agent_cost_key = f"{agent_type}_{provider_type}"
            self.stats["cost_metrics"][agent_cost_key] += cost
    
    def get_basic_stats(self) -> Dict[str, Any]:
        """获取基础统计信息"""
        stats_copy = self.stats.copy()
        
        # 计算平均响应时间
        if stats_copy["successful_requests"] > 0:
            stats_copy["avg_response_time"] = (
                stats_copy["total_response_time"] / stats_copy["successful_requests"]
            )
        else:
            stats_copy["avg_response_time"] = 0.0
        
        # 计算成功率
        if stats_copy["total_requests"] > 0:
            stats_copy["success_rate"] = (
                stats_copy["successful_requests"] / stats_copy["total_requests"]
            )
        else:
            stats_copy["success_rate"] = 0.0
        
        return stats_copy
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        """获取详细统计信息"""
        detailed_copy = {}
        
        # 复制基础数据
        for key, value in self.detailed_stats.items():
            if isinstance(value, defaultdict):
                detailed_copy[key] = dict(value)
            else:
                detailed_copy[key] = value
        
        # 计算平均响应时间
        provider_avg_times = {}
        for provider, times in self.detailed_stats["avg_response_times"].items():
            if times:
                provider_avg_times[provider] = sum(times) / len(times)
            else:
                provider_avg_times[provider] = 0.0
        
        detailed_copy["provider_avg_response_times"] = provider_avg_times
        
        return detailed_copy
    
    def get_full_stats(self) -> Dict[str, Any]:
        """获取完整统计信息"""
        return {
            "basic_stats": self.get_basic_stats(),
            "detailed_stats": self.get_detailed_stats(),
            "collection_time": datetime.now().isoformat()
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time": 0.0,
            "provider_usage": defaultdict(int),
            "cost_metrics": defaultdict(float)
        }
        
        self.detailed_stats = {
            "agent_type_usage": defaultdict(int),
            "tenant_usage": defaultdict(int),
            "model_usage": defaultdict(int),
            "error_types": defaultdict(int),
            "avg_response_times": defaultdict(list),
            "hourly_usage": defaultdict(int)
        }
        
        self.logger.info("统计信息已重置")
    
    def get_usage_summary(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """获取使用摘要"""
        current_time = datetime.now()
        summary = {
            "time_window_hours": time_window_hours,
            "total_requests_in_window": 0,
            "top_agents": {},
            "top_tenants": {},
            "top_providers": {},
            "error_summary": {}
        }
        
        # 计算时间窗口内的请求数
        for i in range(time_window_hours):
            hour_time = current_time.replace(minute=0, second=0, microsecond=0)
            hour_time = hour_time.replace(hour=hour_time.hour - i)
            hour_key = hour_time.strftime("%Y-%m-%d_%H")
            
            summary["total_requests_in_window"] += self.detailed_stats["hourly_usage"].get(hour_key, 0)
        
        # 获取前5名
        summary["top_agents"] = dict(
            sorted(self.detailed_stats["agent_type_usage"].items(), 
                   key=lambda x: x[1], reverse=True)[:5]
        )
        
        summary["top_tenants"] = dict(
            sorted(self.detailed_stats["tenant_usage"].items(), 
                   key=lambda x: x[1], reverse=True)[:5]
        )
        
        summary["top_providers"] = dict(
            sorted(self.stats["provider_usage"].items(), 
                   key=lambda x: x[1], reverse=True)[:5]
        )
        
        summary["error_summary"] = dict(self.detailed_stats["error_types"])
        
        return summary