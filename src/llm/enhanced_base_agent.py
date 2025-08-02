"""
增强基础智能体模块

该模块提供集成多LLM供应商支持的增强版BaseAgent，为现有智能体提供
无缝的多供应商LLM能力，同时保持向后兼容性。

核心功能:
- 继承原有BaseAgent接口
- 集成多LLM供应商支持
- 智能路由和故障转移
- 成本追踪和优化
- 性能监控和分析
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from ..agents.core.base import BaseAgent
from ..agents.core.message import AgentMessage, ConversationState
from .multi_llm_client import MultiLLMClient, get_multi_llm_client
from .intelligent_router import RoutingStrategy
from .provider_config import GlobalProviderConfig
from src.utils import get_component_logger, ErrorHandler


class MultiLLMBaseAgent(BaseAgent):
    """
    多LLM供应商增强版基础智能体
    
    继承原有BaseAgent的所有功能，并添加多LLM供应商支持。
    为子类提供智能LLM路由、故障转移和成本优化能力。
    """
    
    def __init__(
        self, 
        agent_id: str, 
        tenant_id: Optional[str] = None,
        llm_config: Optional[GlobalProviderConfig] = None,
        routing_strategy: Optional[RoutingStrategy] = None
    ):
        """
        初始化增强版智能体
        
        参数:
            agent_id: 智能体唯一标识符
            tenant_id: 租户标识符
            llm_config: LLM配置，None时使用全局配置
            routing_strategy: 默认路由策略
        """
        super().__init__(agent_id, tenant_id)
        
        # 多LLM配置
        self.llm_config = llm_config
        self.routing_strategy = routing_strategy or RoutingStrategy.AGENT_OPTIMIZED
        self._llm_client: Optional[MultiLLMClient] = None
        
        # 智能体特定配置
        self.agent_type = self._extract_agent_type(agent_id)
        self.llm_preferences = self._get_default_llm_preferences()
        
        # 性能统计
        self.llm_stats = {
            "total_llm_requests": 0,
            "successful_llm_requests": 0,
            "failed_llm_requests": 0,
            "total_llm_cost": 0.0,
            "avg_llm_response_time": 0.0,
            "provider_usage": {}
        }
        
        self.logger.info(f"多LLM增强智能体初始化完成: {agent_id}, 类型: {self.agent_type}")
    
    async def get_llm_client(self) -> MultiLLMClient:
        """获取多LLM客户端实例"""
        if self._llm_client is None:
            self._llm_client = await get_multi_llm_client(self.llm_config)
        return self._llm_client
    
    async def llm_chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        strategy: Optional[RoutingStrategy] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        """
        执行LLM聊天完成请求
        
        参数:
            messages: 消息列表
            model: 指定模型
            temperature: 温度参数
            max_tokens: 最大令牌数
            stream: 是否流式响应
            strategy: 路由策略
            **kwargs: 其他参数
            
        返回:
            Union[str, Dict[str, Any]]: 响应内容
        """
        start_time = time.time()
        
        try:
            # 获取LLM客户端
            llm_client = await self.get_llm_client()
            
            # 应用智能体偏好设置
            effective_strategy = strategy or self.routing_strategy
            effective_temperature = temperature or self.llm_preferences.get("temperature", 0.7)
            effective_max_tokens = max_tokens or self.llm_preferences.get("max_tokens", 4096)
            
            # 添加智能体上下文
            enhanced_kwargs = {
                **kwargs,
                "cost_priority": self.llm_preferences.get("cost_priority", 0.5),
                "quality_threshold": self.llm_preferences.get("quality_threshold", 0.8)
            }
            
            # 执行请求
            response = await llm_client.chat_completion(
                messages=messages,
                agent_type=self.agent_type,
                tenant_id=self.tenant_id,
                model=model,
                temperature=effective_temperature,
                max_tokens=effective_max_tokens,
                stream=stream,
                strategy=effective_strategy,
                **enhanced_kwargs
            )
            
            # 更新统计信息
            processing_time = time.time() - start_time
            self._update_llm_stats(processing_time, True)
            
            return response
            
        except Exception as e:
            processing_time = time.time() - start_time
            self._update_llm_stats(processing_time, False)
            
            # 使用错误处理器
            error_context = {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "tenant_id": self.tenant_id,
                "processing_time": processing_time
            }
            self.error_handler.handle_error(e, error_context)
            raise
    
    async def llm_analyze_sentiment(
        self,
        text: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        LLM情感分析
        
        参数:
            text: 要分析的文本
            **kwargs: 其他参数
            
        返回:
            Dict[str, Any]: 情感分析结果
        """
        try:
            llm_client = await self.get_llm_client()
            return await llm_client.analyze_sentiment(
                text=text,
                tenant_id=self.tenant_id,
                **kwargs
            )
        except Exception as e:
            self.logger.error(f"LLM情感分析失败: {str(e)}")
            # 返回默认结果
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.5,
                "error": str(e)
            }
    
    async def llm_classify_intent(
        self,
        text: str,
        conversation_history: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        LLM意图分类
        
        参数:
            text: 要分类的文本
            conversation_history: 对话历史
            **kwargs: 其他参数
            
        返回:
            Dict[str, Any]: 意图分类结果
        """
        try:
            llm_client = await self.get_llm_client()
            return await llm_client.classify_intent(
                text=text,
                conversation_history=conversation_history,
                tenant_id=self.tenant_id,
                **kwargs
            )
        except Exception as e:
            self.logger.error(f"LLM意图分类失败: {str(e)}")
            # 返回默认结果
            return {
                "intent": "browsing",
                "category": "general",
                "confidence": 0.5,
                "urgency": "medium",
                "error": str(e)
            }
    
    async def llm_generate_response(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        生成LLM响应
        
        参数:
            prompt: 提示文本
            context: 上下文信息
            **kwargs: 其他参数
            
        返回:
            str: 生成的响应
        """
        # 构建消息列表
        messages = [
            {
                "role": "system",
                "content": self._build_system_message(context)
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        return await self.llm_chat_completion(messages, **kwargs)
    
    def _extract_agent_type(self, agent_id: str) -> str:
        """从智能体ID提取类型"""
        # 假设agent_id格式为 "type_tenant_id" 或 "type"
        parts = agent_id.split('_')
        return parts[0] if parts else "unknown"
    
    def _get_default_llm_preferences(self) -> Dict[str, Any]:
        """获取智能体类型的默认LLM偏好"""
        preferences_map = {
            "compliance": {
                "temperature": 0.3,
                "max_tokens": 2048,
                "cost_priority": 0.3,  # 更重视质量
                "quality_threshold": 0.9
            },
            "sentiment": {
                "temperature": 0.4,
                "max_tokens": 1024,
                "cost_priority": 0.4,
                "quality_threshold": 0.85
            },
            "intent": {
                "temperature": 0.3,
                "max_tokens": 512,
                "cost_priority": 0.6,
                "quality_threshold": 0.8
            },
            "sales": {
                "temperature": 0.7,
                "max_tokens": 4096,
                "cost_priority": 0.4,
                "quality_threshold": 0.85
            },
            "product": {
                "temperature": 0.5,
                "max_tokens": 3072,
                "cost_priority": 0.3,
                "quality_threshold": 0.9
            },
            "memory": {
                "temperature": 0.2,
                "max_tokens": 1024,
                "cost_priority": 0.8,  # 更重视成本
                "quality_threshold": 0.7
            },
            "suggestion": {
                "temperature": 0.4,
                "max_tokens": 2048,
                "cost_priority": 0.5,
                "quality_threshold": 0.85
            }
        }
        
        return preferences_map.get(self.agent_type, {
            "temperature": 0.7,
            "max_tokens": 2048,
            "cost_priority": 0.5,
            "quality_threshold": 0.8
        })
    
    def _build_system_message(self, context: Optional[Dict[str, Any]] = None) -> str:
        """构建系统消息"""
        base_message = f"你是一个专业的{self.agent_type}智能体，负责处理美妆相关的客户咨询。"
        
        # 添加上下文信息
        if context:
            if context.get("customer_profile"):
                base_message += f"\n客户信息: {context['customer_profile']}"
            
            if context.get("conversation_history"):
                base_message += f"\n对话历史: {context['conversation_history']}"
            
            if context.get("product_context"):
                base_message += f"\n产品信息: {context['product_context']}"
        
        # 添加智能体特定指导
        agent_guidelines = {
            "compliance": "请确保所有回复符合相关法规要求，避免夸大宣传。",
            "sentiment": "请准确分析客户情感，关注情感变化和满意度。",
            "intent": "请准确识别客户意图，判断购买倾向和紧急程度。",
            "sales": "请提供专业的销售建议，关注客户需求匹配。",
            "product": "请基于产品知识库提供准确的产品信息和推荐。",
            "memory": "请帮助记录和整理重要的客户信息。",
            "suggestion": "请提供建设性的优化建议和改进方案。"
        }
        
        guideline = agent_guidelines.get(self.agent_type, "")
        if guideline:
            base_message += f"\n\n{guideline}"
        
        base_message += "\n\n请用中文回复，保持专业和友好的语调。"
        
        return base_message
    
    def _update_llm_stats(self, processing_time: float, success: bool):
        """更新LLM统计信息"""
        self.llm_stats["total_llm_requests"] += 1
        
        if success:
            self.llm_stats["successful_llm_requests"] += 1
            
            # 更新平均响应时间
            total_successful = self.llm_stats["successful_llm_requests"]
            current_avg = self.llm_stats["avg_llm_response_time"]
            self.llm_stats["avg_llm_response_time"] = (
                (current_avg * (total_successful - 1) + processing_time) / total_successful
            )
        else:
            self.llm_stats["failed_llm_requests"] += 1
    
    async def get_llm_stats(self) -> Dict[str, Any]:
        """获取LLM统计信息"""
        try:
            llm_client = await self.get_llm_client()
            global_stats = await llm_client.get_global_stats()
            
            return {
                "agent_stats": self.llm_stats.copy(),
                "global_stats": global_stats,
                "agent_type": self.agent_type,
                "tenant_id": self.tenant_id,
                "routing_strategy": self.routing_strategy.value if self.routing_strategy else None
            }
        except Exception as e:
            self.logger.error(f"获取LLM统计信息失败: {str(e)}")
            return {"error": str(e)}
    
    async def get_cost_analysis(self) -> Dict[str, Any]:
        """获取成本分析"""
        try:
            llm_client = await self.get_llm_client()
            return await llm_client.get_cost_analysis(tenant_id=self.tenant_id)
        except Exception as e:
            self.logger.error(f"获取成本分析失败: {str(e)}")
            return {"error": str(e)}
    
    async def get_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """获取优化建议"""
        try:
            llm_client = await self.get_llm_client()
            return await llm_client.get_optimization_suggestions(tenant_id=self.tenant_id)
        except Exception as e:
            self.logger.error(f"获取优化建议失败: {str(e)}")
            return []
    
    def set_routing_strategy(self, strategy: RoutingStrategy):
        """设置路由策略"""
        self.routing_strategy = strategy
        self.logger.info(f"智能体路由策略更新: {self.agent_id} -> {strategy.value}")
    
    def update_llm_preferences(self, preferences: Dict[str, Any]):
        """更新LLM偏好设置"""
        self.llm_preferences.update(preferences)
        self.logger.info(f"智能体LLM偏好更新: {self.agent_id}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取智能体状态信息（重写父类方法）"""
        base_status = super().get_status()
        
        # 添加LLM相关状态
        base_status["data"]["llm_stats"] = self.llm_stats.copy()
        base_status["data"]["agent_type"] = self.agent_type
        base_status["data"]["routing_strategy"] = self.routing_strategy.value if self.routing_strategy else None
        base_status["data"]["llm_preferences"] = self.llm_preferences.copy()
        
        return base_status
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取智能体健康状态（重写父类方法）"""
        base_health = super().get_health_status()
        
        # 添加LLM相关健康指标
        total_llm_requests = self.llm_stats["total_llm_requests"]
        llm_error_rate = 0.0
        
        if total_llm_requests > 0:
            llm_error_rate = (self.llm_stats["failed_llm_requests"] / total_llm_requests) * 100
        
        # 评估LLM健康状态
        llm_health_status = "healthy"
        if llm_error_rate > 20:  # 超过20%错误率
            llm_health_status = "critical"
        elif llm_error_rate > 10:  # 超过10%错误率
            llm_health_status = "warning"
        
        base_health["metrics"]["llm_error_rate"] = llm_error_rate
        base_health["metrics"]["llm_avg_response_time"] = self.llm_stats["avg_llm_response_time"]
        base_health["metrics"]["total_llm_requests"] = total_llm_requests
        
        base_health["details"]["llm_health_status"] = llm_health_status
        
        return base_health


class MultiLLMAgentMixin:
    """
    多LLM智能体混入类
    
    为现有智能体提供多LLM功能的混入类，可以轻松添加到现有智能体中。
    """
    
    def __init__(self, *args, **kwargs):
        """初始化混入类"""
        super().__init__(*args, **kwargs)
        
        # 添加LLM客户端支持
        if not hasattr(self, '_llm_client'):
            self._llm_client: Optional[MultiLLMClient] = None
        
        if not hasattr(self, 'agent_type'):
            self.agent_type = self._extract_agent_type(getattr(self, 'agent_id', 'unknown'))
        
        if not hasattr(self, 'routing_strategy'):
            self.routing_strategy = RoutingStrategy.AGENT_OPTIMIZED
    
    async def get_llm_client(self) -> MultiLLMClient:
        """获取多LLM客户端实例"""
        if self._llm_client is None:
            self._llm_client = await get_multi_llm_client()
        return self._llm_client
    
    async def llm_completion(
        self,
        messages: List[Dict[str, Any]],
        **kwargs
    ) -> str:
        """简化的LLM完成接口"""
        llm_client = await self.get_llm_client()
        return await llm_client.chat_completion(
            messages=messages,
            agent_type=self.agent_type,
            tenant_id=getattr(self, 'tenant_id', None),
            strategy=self.routing_strategy,
            **kwargs
        )
    
    def _extract_agent_type(self, agent_id: str) -> str:
        """从智能体ID提取类型"""
        parts = agent_id.split('_')
        return parts[0] if parts else "unknown"