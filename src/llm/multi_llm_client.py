"""
多LLM客户端模块

该模块提供统一的多LLM供应商客户端接口，集成智能路由、故障转移和成本优化功能。
为现有的BaseAgent架构提供无缝的多供应商LLM支持。

核心功能:
- 统一的LLM请求接口
- 智能供应商路由和选择
- 自动故障转移和恢复
- 实时成本追踪和优化
- 多租户隔离和配置管理
"""

import time
from typing import Dict, Any, Optional, List, Union, AsyncGenerator
from datetime import datetime

from .base_provider import LLMRequest, LLMResponse, RequestType, ProviderError
from .provider_manager import ProviderManager
from .intelligent_router import IntelligentRouter, RoutingContext, RoutingStrategy
from .failover_system import FailoverSystem
from .cost_optimizer import CostOptimizer
from .provider_config import GlobalProviderConfig, ProviderType
from .multi_llm_client_modules.request_builder import RequestBuilder
from .multi_llm_client_modules.response_processor import ResponseProcessor
from .multi_llm_client_modules.session_manager import SessionManager
from .multi_llm_client_modules.stats_collector import StatsCollector
from src.utils import get_component_logger, ErrorHandler


class MultiLLMClient:
    """
    多LLM供应商统一客户端
    
    提供统一的LLM服务接口，自动处理供应商选择、故障转移和成本优化。
    设计为BaseAgent架构的直接替代品，保持API兼容性。
    """
    
    def __init__(self, config: GlobalProviderConfig):
        """
        初始化多LLM客户端
        
        参数:
            config: 全局供应商配置
        """
        self.config = config
        self.logger = get_component_logger(__name__, "MultiLLMClient")
        self.error_handler = ErrorHandler("multi_llm_client")
        
        # 核心组件
        self.provider_manager = ProviderManager(config)
        self.intelligent_router = IntelligentRouter(self.provider_manager)
        self.failover_system = FailoverSystem(self.intelligent_router)
        self.cost_optimizer = CostOptimizer()
        
        # 专用组件
        self.request_builder = RequestBuilder()
        self.response_processor = ResponseProcessor()
        self.session_manager = SessionManager()
        self.stats_collector = StatsCollector()
        
        # 设置组件引用
        self.session_manager.set_components(
            provider_manager=self.provider_manager,
            intelligent_router=self.intelligent_router,
            failover_system=self.failover_system,
            cost_optimizer=self.cost_optimizer
        )
        
        self.logger.info("多LLM客户端初始化完成")
    
    async def initialize(self):
        """初始化客户端组件"""
        await self.session_manager.initialize_client(self.config)
    
    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        agent_type: Optional[str] = None,
        tenant_id: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        strategy: Optional[RoutingStrategy] = None,
        **kwargs
    ) -> Union[str, LLMResponse, AsyncGenerator[str, None]]:
        """
        聊天完成请求 - 兼容原有OpenAI客户端接口
        
        参数:
            messages: 消息列表
            agent_type: 智能体类型
            tenant_id: 租户ID
            model: 指定模型
            temperature: 温度参数
            max_tokens: 最大令牌数
            stream: 是否流式响应
            strategy: 路由策略
            **kwargs: 其他参数
            
        返回:
            Union[str, LLMResponse, AsyncGenerator]: 响应内容
        """
        # 检查初始化状态
        if not self.session_manager.is_initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            # 构建请求对象
            request = self.request_builder.build_chat_request(
                messages=messages,
                agent_type=agent_type,
                tenant_id=tenant_id,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                **kwargs
            )
            
            # 记录请求开始
            session_id = self.stats_collector.record_request_start(request)
            
            # 构建路由上下文
            routing_context = self.request_builder.build_routing_context(
                agent_type, tenant_id, messages, **kwargs
            )
            
            # 执行带故障转移的请求
            response = await self.failover_system.execute_with_failover(
                request, routing_context, strategy
            )
            
            # 记录成本
            if isinstance(response, LLMResponse):
                await self.cost_optimizer.record_cost(
                    request, response, response.provider_type, agent_type
                )
            
            # 记录成功统计
            processing_time = time.time() - start_time
            self.stats_collector.record_request_success(request, response, processing_time)
            
            # 处理响应格式
            return self.response_processor.process_chat_response(response, stream)
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.stats_collector.record_request_failure(request, e, processing_time)
            self.logger.error(f"聊天完成请求失败: {agent_type}, 错误: {str(e)}")
            raise
    
    async def analyze_sentiment(
        self,
        text: str,
        tenant_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        情感分析 - 兼容原有接口
        
        参数:
            text: 要分析的文本
            tenant_id: 租户ID
            **kwargs: 其他参数
            
        返回:
            Dict[str, Any]: 情感分析结果
        """
        messages = self.response_processor.build_sentiment_messages(text)
        params = self.response_processor.get_sentiment_params()
        strategy = self.response_processor.get_sentiment_strategy()
        
        response = await self.chat_completion(
            messages=messages,
            agent_type="sentiment",
            tenant_id=tenant_id,
            strategy=strategy,
            **{**params, **kwargs}
        )
        
        return self.response_processor.process_sentiment_response(response)
    
    async def classify_intent(
        self,
        text: str,
        conversation_history: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        意图分类 - 兼容原有接口
        
        参数:
            text: 要分类的文本
            conversation_history: 对话历史
            tenant_id: 租户ID
            **kwargs: 其他参数
            
        返回:
            Dict[str, Any]: 意图分类结果
        """
        messages = self.response_processor.build_intent_messages(text, conversation_history)
        params = self.response_processor.get_intent_params()
        strategy = self.response_processor.get_intent_strategy()
        
        response = await self.chat_completion(
            messages=messages,
            agent_type="intent",
            tenant_id=tenant_id,
            strategy=strategy,
            **{**params, **kwargs}
        )
        
        return self.response_processor.process_intent_response(response)
    
    async def get_provider_status(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """获取供应商状态"""
        available_providers = self.provider_manager.get_available_providers(tenant_id)
        
        provider_status = {}
        for provider in available_providers:
            provider_status[provider.provider_type.value] = {
                "is_healthy": provider.health.is_healthy,
                "avg_response_time": provider.health.avg_response_time,
                "error_rate": provider.health.error_rate,
                "rate_limit_remaining": provider.health.rate_limit_remaining,
                "last_check": provider.health.last_check.isoformat(),
                "stats": provider.get_stats()
            }
        
        return provider_status
    
    async def get_cost_analysis(
        self,
        tenant_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """获取成本分析"""
        analysis = await self.cost_optimizer.analyze_costs(
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time
        )
        
        return {
            "period_start": analysis.period_start.isoformat(),
            "period_end": analysis.period_end.isoformat(),
            "total_cost": analysis.total_cost,
            "total_requests": analysis.total_requests,
            "total_tokens": analysis.total_tokens,
            "avg_cost_per_request": analysis.avg_cost_per_request,
            "avg_cost_per_token": analysis.avg_cost_per_token,
            "provider_breakdown": analysis.provider_breakdown,
            "agent_breakdown": analysis.agent_breakdown,
            "tenant_breakdown": analysis.tenant_breakdown,
            "optimization_opportunities": analysis.optimization_opportunities
        }
    
    async def get_optimization_suggestions(
        self,
        tenant_id: Optional[str] = None,
        min_savings: float = 0.1
    ) -> List[Dict[str, Any]]:
        """获取优化建议"""
        suggestions = await self.cost_optimizer.get_optimization_suggestions(
            tenant_id=tenant_id,
            min_savings=min_savings
        )
        
        return [
            {
                "optimization_type": suggestion.optimization_type.value,
                "current_cost": suggestion.current_cost,
                "potential_savings": suggestion.potential_savings,
                "savings_percentage": suggestion.savings_percentage,
                "confidence": suggestion.confidence,
                "description": suggestion.description,
                "implementation_details": suggestion.implementation_details,
                "estimated_impact": suggestion.estimated_impact
            }
            for suggestion in suggestions
        ]
    
    async def get_global_stats(self) -> Dict[str, Any]:
        """获取全局统计信息"""
        return {
            "client_stats": self.stats_collector.get_full_stats(),
            "provider_stats": self.provider_manager.get_global_stats(),
            "routing_stats": await self.intelligent_router.get_routing_stats(),
            "failover_stats": await self.failover_system.get_failover_stats(),
            "cost_summary": self.cost_optimizer.get_cost_summary()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return await self.session_manager.health_check()
    
    async def shutdown(self):
        """关闭客户端"""
        await self.session_manager.shutdown()


# 全局客户端实例
_multi_llm_client: Optional[MultiLLMClient] = None


async def get_multi_llm_client(config: Optional[GlobalProviderConfig] = None) -> MultiLLMClient:
    """获取或创建全局多LLM客户端实例"""
    global _multi_llm_client
    
    if _multi_llm_client is None:
        if config is None:
            raise ValueError("首次创建客户端时必须提供配置")
        
        _multi_llm_client = MultiLLMClient(config)
        await _multi_llm_client.initialize()
    
    return _multi_llm_client


async def shutdown_multi_llm_client():
    """关闭全局多LLM客户端"""
    global _multi_llm_client
    
    if _multi_llm_client:
        await _multi_llm_client.shutdown()
        _multi_llm_client = None