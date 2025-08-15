"""
多LLM客户端模块

该模块提供统一的多LLM供应商客户端接口，集成智能路由、简单重试和成本优化功能。
为现有的BaseAgent架构提供无缝的多供应商LLM支持。

核心功能:
- 统一的LLM请求接口
- 智能供应商路由和选择
- 简单的重试机制
- 实时成本追踪和优化
- 多租户隔离和配置管理
"""

import time
import uuid
import json
from typing import Dict, Any, Optional, List, Union, AsyncGenerator
from datetime import datetime

from .base_provider import LLMRequest, LLMResponse, RequestType, ProviderError
from .provider_manager import ProviderManager
from .intelligent_router import IntelligentRouter, RoutingContext, RoutingStrategy
from .cost_optimizer import CostOptimizer
from .provider_config import GlobalProviderConfig, ProviderType
from .client_components import SessionManager, StatsCollector
from utils import get_component_logger, ErrorHandler


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
        self.cost_optimizer = CostOptimizer()
        
        # 专用组件
        self.session_manager = SessionManager()
        self.stats_collector = StatsCollector()
        
        # 设置组件引用
        self.session_manager.set_components(
            provider_manager=self.provider_manager,
            intelligent_router=self.intelligent_router,
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
            request = self._build_chat_request(
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
            routing_context = self._build_routing_context(
                agent_type, tenant_id, messages, **kwargs
            )
            
            # 执行带简单重试的请求
            response = await self._execute_with_retry(
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
            return self._process_chat_response(response, stream)
            
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
        messages = self._build_sentiment_messages(text)
        params = {"temperature": 0.3, "max_tokens": 512}
        strategy = RoutingStrategy.CHINESE_OPTIMIZED
        
        response = await self.chat_completion(
            messages=messages,
            agent_type="sentiment",
            tenant_id=tenant_id,
            strategy=strategy,
            **{**params, **kwargs}
        )
        
        return self._process_sentiment_response(response)
    
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
        messages = self._build_intent_messages(text, conversation_history)
        params = {"temperature": 0.3, "max_tokens": 512}
        strategy = RoutingStrategy.AGENT_OPTIMIZED
        
        response = await self.chat_completion(
            messages=messages,
            agent_type="intent",
            tenant_id=tenant_id,
            strategy=strategy,
            **{**params, **kwargs}
        )
        
        return self._process_intent_response(response)
    
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
            "cost_summary": self.cost_optimizer.get_cost_summary()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return await self.session_manager.health_check()
    
    # 集成的请求构建方法 (原 RequestBuilder)
    def _build_chat_request(
        self,
        messages: List[Dict[str, Any]],
        agent_type: Optional[str] = None,
        tenant_id: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> LLMRequest:
        """构建聊天完成请求"""
        request_id = str(uuid.uuid4())
        validated_messages = self._validate_messages(messages)
        effective_temperature = self._get_default_temperature(temperature, agent_type)
        effective_max_tokens = self._get_default_max_tokens(max_tokens, agent_type)
        
        return LLMRequest(
            request_id=request_id,
            request_type=RequestType.CHAT_COMPLETION,
            messages=validated_messages,
            model=model,
            temperature=effective_temperature,
            max_tokens=effective_max_tokens,
            stream=stream,
            tenant_id=tenant_id,
            agent_type=agent_type,
            metadata=kwargs
        )
    
    def _build_routing_context(
        self,
        agent_type: Optional[str],
        tenant_id: Optional[str],
        messages: List[Dict[str, Any]],
        **kwargs
    ) -> RoutingContext:
        """构建路由上下文"""
        content_language = self._detect_content_language(messages)
        has_multimodal = self._detect_multimodal_content(messages)
        
        return RoutingContext(
            agent_type=agent_type,
            tenant_id=tenant_id,
            content_language=content_language,
            has_multimodal=has_multimodal,
            urgency_level=kwargs.get("urgency", "medium"),
            cost_priority=kwargs.get("cost_priority", 0.5),
            quality_threshold=kwargs.get("quality_threshold", 0.8)
        )
    
    # 集成的响应处理方法 (原 ResponseProcessor)
    def _process_chat_response(
        self,
        response: Union[LLMResponse, AsyncGenerator[str, None]],
        stream: bool = False
    ) -> Union[str, LLMResponse, AsyncGenerator[str, None]]:
        """处理聊天完成响应"""
        if stream:
            return response
        elif isinstance(response, LLMResponse):
            return response.content
        else:
            return response
    
    def _build_sentiment_messages(self, text: str) -> list:
        """构建情感分析消息"""
        return [
            {
                "role": "system",
                "content": "分析给定文本的情感。用JSON格式回复，包含'sentiment'(positive/negative/neutral)、'score'(-1.0到1.0)和'confidence'(0.0到1.0)。"
            },
            {
                "role": "user",
                "content": text
            }
        ]
    
    def _build_intent_messages(self, text: str, conversation_history: Optional[list] = None) -> list:
        """构建意图分类消息"""
        context = ""
        if conversation_history:
            context = f"对话历史：\n{chr(10).join(conversation_history[-3:])}\n\n"
        
        return [
            {
                "role": "system",
                "content": "分类美妆咨询的客户意图。用JSON格式回复，包含'intent'(browsing/interested/ready_to_buy/support)、'category'(skincare/makeup/fragrance/general)、'confidence'(0.0-1.0)和'urgency'(low/medium/high)。"
            },
            {
                "role": "user",
                "content": f"{context}客户消息: {text}"
            }
        ]
    
    def _process_sentiment_response(self, response: str) -> Dict[str, Any]:
        """处理情感分析响应"""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.5,
                "fallback": True
            }
    
    def _process_intent_response(self, response: str) -> Dict[str, Any]:
        """处理意图分类响应"""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "intent": "browsing",
                "category": "general",
                "confidence": 0.5,
                "urgency": "medium",
                "fallback": True
            }
    
    # 辅助方法
    def _validate_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """验证消息格式"""
        if not messages:
            raise ValueError("消息列表不能为空")
        
        validated = []
        for i, message in enumerate(messages):
            if not isinstance(message, dict) or "role" not in message or "content" not in message:
                raise ValueError(f"消息 {i} 格式无效")
            validated.append(message)
        
        return validated
    
    def _get_default_temperature(self, temperature: Optional[float], agent_type: Optional[str]) -> float:
        """获取默认温度值"""
        if temperature is not None:
            return max(0.0, min(2.0, temperature))
        
        agent_defaults = {
            "compliance": 0.3, "sentiment": 0.4, "intent": 0.3, "sales": 0.7,
            "product": 0.5, "memory": 0.2, "suggestion": 0.4
        }
        return agent_defaults.get(agent_type, 0.7)
    
    def _get_default_max_tokens(self, max_tokens: Optional[int], agent_type: Optional[str]) -> int:
        """获取默认最大令牌数"""
        if max_tokens is not None:
            return max(1, min(32000, max_tokens))
        
        agent_defaults = {
            "compliance": 2048, "sentiment": 1024, "intent": 512, "sales": 4096,
            "product": 3072, "memory": 1024, "suggestion": 2048
        }
        return agent_defaults.get(agent_type, 2048)
    
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
                if "image_url" in msg:
                    return True
                if isinstance(msg.get("content"), list):
                    for content_item in msg["content"]:
                        if isinstance(content_item, dict) and content_item.get("type") == "image_url":
                            return True
        return False
    
    async def _execute_with_retry(
        self,
        request: LLMRequest,
        routing_context: RoutingContext,
        strategy: Optional[RoutingStrategy] = None,
        max_retries: int = 3
    ) -> LLMResponse:
        """
        执行带简单重试的LLM请求
        
        参数:
            request: LLM请求对象
            routing_context: 路由上下文
            strategy: 路由策略
            max_retries: 最大重试次数
            
        返回:
            LLMResponse: 成功的响应
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # 更新路由上下文
                routing_context.retry_count = attempt
                
                # 选择供应商
                provider = await self.intelligent_router.route_request(
                    request, routing_context, strategy
                )
                
                # 执行请求
                response = await provider.make_request(request)
                
                self.logger.info(f"请求成功，供应商: {provider.provider_type}, 尝试次数: {attempt + 1}")
                return response
                
            except Exception as e:
                last_error = e
                self.logger.warning(f"请求失败，尝试次数: {attempt + 1}, 错误: {str(e)}")
                
                # 更新上下文以排除失败的供应商
                if 'provider' in locals():
                    routing_context.previous_provider = provider.provider_type
                
                # 如果是最后一次尝试，抛出异常
                if attempt == max_retries - 1:
                    break
        
        # 所有重试都失败了
        self.logger.error(f"所有重试都失败，最大尝试次数: {max_retries}")
        raise last_error
    
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