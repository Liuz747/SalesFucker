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

import asyncio
import time
import uuid
from typing import Dict, Any, Optional, List, Union, AsyncGenerator
from datetime import datetime
from contextlib import asynccontextmanager

from .base_provider import LLMRequest, LLMResponse, RequestType, ProviderError
from .provider_manager import ProviderManager
from .intelligent_router import IntelligentRouter, RoutingContext, RoutingStrategy
from .failover_system import FailoverSystem
from .cost_optimizer import CostOptimizer
from .provider_config import GlobalProviderConfig, ProviderType
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
        
        # 客户端状态
        self.is_initialized = False
        self.is_shutting_down = False
        
        # 性能统计
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time": 0.0,
            "provider_usage": {},
            "cost_metrics": {}
        }
        
        self.logger.info("多LLM客户端初始化完成")
    
    async def initialize(self):
        """初始化客户端组件"""
        if self.is_initialized:
            return
        
        try:
            # 初始化供应商管理器
            await self.provider_manager.initialize()
            
            # 设置成本配置
            for tenant_id, tenant_config in self.config.tenant_configs.items():
                self.cost_optimizer.set_cost_config(tenant_id, tenant_config.cost_config)
            
            self.is_initialized = True
            self.logger.info("多LLM客户端初始化成功")
            
        except Exception as e:
            self.logger.error(f"多LLM客户端初始化失败: {str(e)}")
            raise
    
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
        if not self.is_initialized:
            await self.initialize()
        
        # 创建请求对象
        request = LLMRequest(
            request_id=str(uuid.uuid4()),
            request_type=RequestType.CHAT_COMPLETION,
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            tenant_id=tenant_id,
            agent_type=agent_type,
            metadata=kwargs
        )
        
        # 创建路由上下文
        routing_context = self._create_routing_context(
            agent_type, tenant_id, messages, **kwargs
        )
        
        try:
            # 执行带故障转移的请求
            response = await self.failover_system.execute_with_failover(
                request, routing_context, strategy
            )
            
            # 记录成本
            if isinstance(response, LLMResponse):
                await self.cost_optimizer.record_cost(
                    request, response, response.provider_type, agent_type
                )
            
            # 更新统计信息
            self._update_stats(request, response, True)
            
            # 返回兼容格式
            if stream:
                return response  # 流式响应返回生成器
            elif isinstance(response, LLMResponse):
                return response.content  # 兼容原有字符串返回格式
            else:
                return response
                
        except Exception as e:
            self._update_stats(request, None, False)
            self.logger.error(f"聊天完成请求失败: {request.request_id}, 错误: {str(e)}")
            raise
    
    async def process_request(
        self,
        request: LLMRequest,
        routing_context: Optional[RoutingContext] = None,
        strategy: Optional[RoutingStrategy] = None
    ) -> Union[LLMResponse, AsyncGenerator[str, None]]:
        """
        处理LLM请求的通用接口
        
        参数:
            request: LLM请求对象
            routing_context: 路由上下文
            strategy: 路由策略
            
        返回:
            Union[LLMResponse, AsyncGenerator]: 响应结果
        """
        if not self.is_initialized:
            await self.initialize()
        
        if not routing_context:
            routing_context = self._create_routing_context(
                request.agent_type, 
                request.tenant_id, 
                request.messages
            )
        
        try:
            response = await self.failover_system.execute_with_failover(
                request, routing_context, strategy
            )
            
            # 记录成本和统计
            if isinstance(response, LLMResponse):
                await self.cost_optimizer.record_cost(
                    request, response, response.provider_type, request.agent_type
                )
            
            self._update_stats(request, response, True)
            return response
            
        except Exception as e:
            self._update_stats(request, None, False)
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
        messages = [
            {
                "role": "system",
                "content": "分析给定文本的情感。用JSON格式回复，包含'sentiment'(positive/negative/neutral)、'score'(-1.0到1.0)和'confidence'(0.0到1.0)。"
            },
            {
                "role": "user",
                "content": text
            }
        ]
        
        response = await self.chat_completion(
            messages=messages,
            agent_type="sentiment",
            tenant_id=tenant_id,
            temperature=0.3,
            strategy=RoutingStrategy.CHINESE_OPTIMIZED,
            **kwargs
        )
        
        try:
            import json
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.5,
                "fallback": True
            }
    
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
        context = ""
        if conversation_history:
            context = f"对话历史：\n{chr(10).join(conversation_history[-3:])}\n\n"
        
        messages = [
            {
                "role": "system",
                "content": "分类美妆咨询的客户意图。用JSON格式回复，包含'intent'(browsing/interested/ready_to_buy/support)、'category'(skincare/makeup/fragrance/general)、'confidence'(0.0-1.0)和'urgency'(low/medium/high)。"
            },
            {
                "role": "user",
                "content": f"{context}客户消息: {text}"
            }
        ]
        
        response = await self.chat_completion(
            messages=messages,
            agent_type="intent",
            tenant_id=tenant_id,
            temperature=0.3,
            strategy=RoutingStrategy.AGENT_OPTIMIZED,
            **kwargs
        )
        
        try:
            import json
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "intent": "browsing",
                "category": "general",
                "confidence": 0.5,
                "urgency": "medium",
                "fallback": True
            }
    
    def _create_routing_context(
        self,
        agent_type: Optional[str],
        tenant_id: Optional[str],
        messages: List[Dict[str, Any]],
        **kwargs
    ) -> RoutingContext:
        """创建路由上下文"""
        # 检测内容语言
        content_language = self._detect_content_language(messages)
        
        # 检测多模态内容
        has_multimodal = self._detect_multimodal_content(messages)
        
        # 获取紧急程度
        urgency_level = kwargs.get("urgency", "medium")
        
        # 获取成本优先级
        cost_priority = kwargs.get("cost_priority", 0.5)
        
        # 获取质量阈值
        quality_threshold = kwargs.get("quality_threshold", 0.8)
        
        return RoutingContext(
            agent_type=agent_type,
            tenant_id=tenant_id,
            content_language=content_language,
            has_multimodal=has_multimodal,
            urgency_level=urgency_level,
            cost_priority=cost_priority,
            quality_threshold=quality_threshold
        )
    
    def _detect_content_language(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        """检测内容语言"""
        chinese_chars = set('的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成会可主发年动同工也能下过子说产种面而方后多定行学法所民得经十三之进着等部度家电力里如水化高自二理起小物现实加量都两体制机当使点从业本去把性好应开它合还因由其些然前外天政四日那社义事平形相全表间样与关各重新线内数正心反你明看原又么利比或但质气第向道命此变条只没结解问意建月公无系军很情者最立代想已通并提直题党程展五果料象员革位入常文总次品式活设及管特件长求老头基资边流路级少图山统接知较将组见计别她手角期根论运农指几九区强放决西被干做必战先回则任取据处队南给色光门即保治北造百规热领七海口东导器压志世金增争济阶油思术极交受联什认六共权收证改清己美再采转更单风切打白教速花带安场身车例真务具万每目至达走积示议声报斗完类八离华名确才科张信马节话米整空元况今集温传土许步群广石记需段研界拉林律叫且究观越织装影算低持音众书布复容儿须际商非验连断深难近矿千周委素技备半办青省列习响约支般史感劳便团往酸历市克何除消构府称太准精值号率族维划选标写存候毛亲快效斯院查江型眼王按格养易置派层片始却专状育厂京识适属圆包火住调满县局照参红细引听该铁价严')
        
        for msg in messages:
            if isinstance(msg, dict) and "content" in msg:
                content = str(msg["content"])
                if any(char in chinese_chars for char in content):
                    return "zh"
        
        return "en"
    
    def _detect_multimodal_content(self, messages: List[Dict[str, Any]]) -> bool:
        """检测多模态内容"""
        for msg in messages:
            if isinstance(msg, dict):
                # 检查图像URL
                if "image_url" in msg:
                    return True
                # 检查内容数组（GPT-4V格式）
                if isinstance(msg.get("content"), list):
                    for content_item in msg["content"]:
                        if isinstance(content_item, dict) and content_item.get("type") == "image_url":
                            return True
        
        return False
    
    def _update_stats(
        self,
        request: LLMRequest,
        response: Optional[Union[LLMResponse, AsyncGenerator]],
        success: bool
    ):
        """更新统计信息"""
        self.stats["total_requests"] += 1
        
        if success:
            self.stats["successful_requests"] += 1
            
            if isinstance(response, LLMResponse):
                self.stats["total_response_time"] += response.response_time
                
                # 供应商使用统计
                provider = response.provider_type.value
                self.stats["provider_usage"][provider] = self.stats["provider_usage"].get(provider, 0) + 1
        else:
            self.stats["failed_requests"] += 1
    
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
    
    async def get_routing_stats(self) -> Dict[str, Any]:
        """获取路由统计"""
        return self.intelligent_router.get_routing_stats()
    
    async def get_failover_stats(self) -> Dict[str, Any]:
        """获取故障转移统计"""
        return self.failover_system.get_failover_stats()
    
    async def get_global_stats(self) -> Dict[str, Any]:
        """获取全局统计信息"""
        return {
            "client_stats": self.stats.copy(),
            "provider_stats": self.provider_manager.get_global_stats(),
            "routing_stats": await self.get_routing_stats(),
            "failover_stats": await self.get_failover_stats(),
            "cost_summary": self.cost_optimizer.get_cost_summary()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            health_status = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "is_initialized": self.is_initialized,
                "provider_manager": "healthy",
                "intelligent_router": "healthy",
                "failover_system": "healthy",
                "cost_optimizer": "healthy"
            }
            
            # 检查供应商状态
            provider_status = await self.get_provider_status()
            healthy_providers = sum(
                1 for status in provider_status.values() 
                if status["is_healthy"]
            )
            
            health_status["available_providers"] = healthy_providers
            health_status["total_providers"] = len(provider_status)
            
            if healthy_providers == 0:
                health_status["status"] = "unhealthy"
                health_status["error"] = "没有可用的供应商"
            
            return health_status
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    @asynccontextmanager
    async def request_context(
        self,
        agent_type: Optional[str] = None,
        tenant_id: Optional[str] = None,
        strategy: Optional[RoutingStrategy] = None
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
            # 记录请求完成时间
            context["end_time"] = time.time()
            context["duration"] = context["end_time"] - context["start_time"]
            
            self.logger.debug(
                f"请求上下文完成: 智能体={agent_type}, "
                f"租户={tenant_id}, "
                f"耗时={context['duration']:.3f}s"
            )
    
    async def shutdown(self):
        """关闭客户端"""
        if self.is_shutting_down:
            return
        
        self.is_shutting_down = True
        
        try:
            # 关闭供应商管理器
            await self.provider_manager.shutdown()
            
            self.logger.info("多LLM客户端已关闭")
            
        except Exception as e:
            self.logger.error(f"关闭多LLM客户端时出错: {str(e)}")


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