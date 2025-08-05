"""
LLM集成混入类模块

该模块提供智能体的LLM功能集成，包括多LLM提供商支持、
智能路由和成本优化等功能。

核心功能:
- 多LLM提供商集成
- 智能路由策略
- 上下文感知的消息构建
- LLM调用统计追踪
"""

from typing import Dict, Any, Optional, List, Union
from abc import ABC

from .agent_preferences import get_agent_preferences, get_agent_system_guideline

from src.llm.multi_llm_client import MultiLLMClient, get_multi_llm_client
from src.llm.intelligent_router import RoutingStrategy
from src.llm.provider_config import GlobalProviderConfig


class LLMMixin(ABC):
    """
    LLM功能混入类
    
    为智能体提供多LLM提供商支持、智能路由和成本优化功能。
    当LLM模块不可用时，提供优雅的降级处理。
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        tenant_id: Optional[str] = None,
        llm_config: Optional[GlobalProviderConfig] = None,
        routing_strategy: Optional[RoutingStrategy] = None
    ):
        """
        初始化LLM混入功能
        
        参数:
            agent_id: 智能体唯一标识符
            agent_type: 智能体类型
            tenant_id: 租户标识符
            llm_config: LLM配置
            routing_strategy: 路由策略
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.tenant_id = tenant_id
        self._initialize_llm_features(llm_config, routing_strategy)
    
    def _initialize_llm_features(
        self, 
        llm_config: Optional[GlobalProviderConfig], 
        routing_strategy: Optional[RoutingStrategy]
    ):
        """初始化LLM功能"""
        # 获取智能体类型专用配置
        agent_preferences = get_agent_preferences(self.agent_type)
        
        # 配置管理
        self.routing_strategy = routing_strategy or agent_preferences.get("routing_strategy", RoutingStrategy.AGENT_OPTIMIZED)
        self.llm_preferences = agent_preferences
        
        # LLM接口
        self.llm_config = llm_config
        self._llm_client: Optional[MultiLLMClient] = None
    
    def _initialize_fallback_config(self):
        """初始化降级配置"""
        self.routing_strategy = None
        self.llm_preferences = {}
        self.llm_config = None
        self._llm_client = None
    
    def _get_effective_temperature(self, override_temperature: Optional[float] = None) -> float:
        """获取有效温度值"""
        return override_temperature if override_temperature is not None else self.llm_preferences.get("temperature", 0.7)
    
    def _get_effective_max_tokens(self, override_max_tokens: Optional[int] = None) -> int:
        """获取有效最大令牌数"""
        return override_max_tokens if override_max_tokens is not None else self.llm_preferences.get("max_tokens", 2048)
    
    def _get_enhanced_kwargs(self, **kwargs) -> Dict[str, Any]:
        """获取增强的请求参数"""
        enhanced = {
            **kwargs,
            "cost_priority": self.llm_preferences.get("cost_priority", 0.5),
            "quality_threshold": self.llm_preferences.get("quality_threshold", 0.8)
        }
        return enhanced
    
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
        guideline = get_agent_system_guideline(self.agent_type)
        if guideline:
            base_message += f"\n\n{guideline}"
        
        base_message += "\n\n请用中文回复，保持专业和友好的语调。"
        
        return base_message
    
    async def _get_llm_client(self) -> Optional[MultiLLMClient]:
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
    ) -> Optional[Union[str, Dict[str, Any]]]:
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
            Union[str, Dict[str, Any]]: 响应内容，如果LLM不可用则返回None
        """
        try:
            # 应用智能体偏好设置
            effective_strategy = strategy or self.routing_strategy
            effective_temperature = self._get_effective_temperature(temperature)
            effective_max_tokens = self._get_effective_max_tokens(max_tokens)
            
            # 添加智能体上下文
            enhanced_kwargs = self._get_enhanced_kwargs(**kwargs)
            
            # 获取LLM客户端
            llm_client = await self._get_llm_client()
            if not llm_client:
                raise RuntimeError("LLM客户端不可用")
            
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
            
            return response
            
        except Exception as e:
            # 由调用者处理错误统计
            raise
    
    async def llm_generate_response(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Optional[str]:
        """
        生成LLM响应
        
        参数:
            prompt: 提示文本
            context: 上下文信息
            **kwargs: 其他参数
            
        返回:
            str: 生成的响应，如果LLM不可用则返回None
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
        
        return await self.llm_chat_completion(
            messages=messages,
            **kwargs
        )
    
    def set_routing_strategy(self, strategy: RoutingStrategy):
        """设置路由策略"""
        self.routing_strategy = strategy
    
    def update_llm_preferences(self, preferences: Dict[str, Any]):
        """更新LLM偏好设置"""
        self.llm_preferences.update(preferences)
    
    async def get_llm_client_stats(self) -> Dict[str, Any]:
        """获取LLM客户端全局统计信息"""
        try:
            llm_client = await self._get_llm_client()
            if not llm_client:
                return {"error": "LLM客户端不可用"}
            
            return await llm_client.get_global_stats()
            
        except Exception as e:
            return {"error": str(e)}