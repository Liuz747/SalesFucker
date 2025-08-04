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

from typing import Dict, Any, Optional, List, Union

from ..agents.core.base import BaseAgent
from ..agents.core.message import AgentMessage, ConversationState
from .multi_llm_client import MultiLLMClient, get_multi_llm_client
from .intelligent_router import RoutingStrategy
from .provider_config import GlobalProviderConfig
from .enhanced_base_agent_modules.agent_config import AgentConfig
from .enhanced_base_agent_modules.llm_interface import LLMInterface
from src.utils import get_component_logger


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
        
        # 核心组件
        self.agent_config = AgentConfig(agent_id, tenant_id)
        self.llm_interface = LLMInterface(agent_id, tenant_id, llm_config)
        
        # 设置路由策略
        if routing_strategy:
            self.agent_config.update_routing_strategy(routing_strategy)
        
        self.logger.info(f"多LLM增强智能体初始化完成: {agent_id}, 类型: {self.agent_config.agent_type}")
    
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
        # 应用智能体偏好设置
        effective_strategy = strategy or self.agent_config.routing_strategy
        effective_temperature = self.agent_config.get_effective_temperature(temperature)
        effective_max_tokens = self.agent_config.get_effective_max_tokens(max_tokens)
        
        # 添加智能体上下文
        enhanced_kwargs = self.agent_config.get_enhanced_kwargs(**kwargs)
        
        # 执行请求
        return await self.llm_interface.chat_completion(
            messages=messages,
            agent_type=self.agent_config.agent_type,
            model=model,
            temperature=effective_temperature,
            max_tokens=effective_max_tokens,
            stream=stream,
            strategy=effective_strategy,
            **enhanced_kwargs
        )
    
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
        return await self.llm_interface.analyze_sentiment(text=text, **kwargs)
    
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
        return await self.llm_interface.classify_intent(
            text=text,
            conversation_history=conversation_history,
            **kwargs
        )
    
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
        return await self.llm_interface.generate_response(
            prompt=prompt,
            agent_type=self.agent_config.agent_type,
            context=context,
            **kwargs
        )
    
    def set_routing_strategy(self, strategy: RoutingStrategy):
        """设置路由策略"""
        self.agent_config.update_routing_strategy(strategy)
    
    def update_llm_preferences(self, preferences: Dict[str, Any]):
        """更新LLM偏好设置"""
        if self.agent_config.validate_preferences(preferences):
            self.agent_config.update_llm_preferences(preferences)
        else:
            raise ValueError("偏好设置验证失败")
    
    async def get_llm_stats(self) -> Dict[str, Any]:
        """获取LLM统计信息"""
        interface_stats = await self.llm_interface.get_llm_stats()
        config_summary = self.agent_config.get_config_summary()
        
        return {
            **interface_stats,
            "config": config_summary
        }
    
    async def get_cost_analysis(self) -> Dict[str, Any]:
        """获取成本分析"""
        return await self.llm_interface.get_cost_analysis()
    
    async def get_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """获取优化建议"""
        return await self.llm_interface.get_optimization_suggestions()
    
    def get_status(self) -> Dict[str, Any]:
        """获取智能体状态信息（重写父类方法）"""
        base_status = super().get_status()
        
        # 添加LLM相关状态
        base_status["data"]["llm_stats"] = self.llm_interface.llm_stats.copy()
        base_status["data"]["config"] = self.agent_config.get_config_summary()
        
        return base_status
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取智能体健康状态（重写父类方法）"""
        base_health = super().get_health_status()
        
        # 添加LLM相关健康指标
        llm_health = self.llm_interface.get_health_metrics()
        
        base_health["metrics"].update({
            "llm_error_rate": llm_health["error_rate"],
            "llm_avg_response_time": llm_health["avg_response_time"],
            "total_llm_requests": llm_health["total_requests"]
        })
        
        base_health["details"]["llm_health_status"] = llm_health["health_status"]
        
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