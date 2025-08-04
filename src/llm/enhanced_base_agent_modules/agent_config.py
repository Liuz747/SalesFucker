"""
智能体配置管理器模块

该模块负责管理智能体的LLM配置、偏好设置和优化参数。
提供智能体类型特化的配置和动态配置更新功能。

核心功能:
- 智能体类型识别
- LLM偏好配置管理
- 系统消息构建
- 配置更新和验证
"""

from typing import Dict, Any, Optional
from ..intelligent_router import RoutingStrategy
from src.utils import get_component_logger


class AgentConfig:
    """
    智能体配置管理器
    
    负责管理智能体的LLM相关配置和偏好设置。
    """
    
    def __init__(self, agent_id: str, tenant_id: Optional[str] = None):
        """
        初始化智能体配置
        
        参数:
            agent_id: 智能体唯一标识符
            tenant_id: 租户标识符
        """
        self.agent_id = agent_id
        self.tenant_id = tenant_id
        self.logger = get_component_logger(__name__, "AgentConfig")
        
        # 智能体类型识别
        self.agent_type = self._extract_agent_type(agent_id)
        
        # 默认配置
        self.routing_strategy = RoutingStrategy.AGENT_OPTIMIZED
        self.llm_preferences = self._get_default_llm_preferences()
        
        self.logger.debug(f"智能体配置初始化: {agent_id}, 类型: {self.agent_type}")
    
    def _extract_agent_type(self, agent_id: str) -> str:
        """
        从智能体ID提取类型
        
        参数:
            agent_id: 智能体ID
            
        返回:
            str: 智能体类型
        """
        # 假设agent_id格式为 "type_tenant_id" 或 "type"
        parts = agent_id.split('_')
        return parts[0] if parts else "unknown"
    
    def _get_default_llm_preferences(self) -> Dict[str, Any]:
        """
        获取智能体类型的默认LLM偏好
        
        返回:
            Dict[str, Any]: LLM偏好配置
        """
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
    
    def get_effective_temperature(self, override_temperature: Optional[float] = None) -> float:
        """
        获取有效温度值
        
        参数:
            override_temperature: 覆盖温度值
            
        返回:
            float: 有效温度值
        """
        return override_temperature if override_temperature is not None else self.llm_preferences.get("temperature", 0.7)
    
    def get_effective_max_tokens(self, override_max_tokens: Optional[int] = None) -> int:
        """
        获取有效最大令牌数
        
        参数:
            override_max_tokens: 覆盖最大令牌数
            
        返回:
            int: 有效最大令牌数
        """
        return override_max_tokens if override_max_tokens is not None else self.llm_preferences.get("max_tokens", 2048)
    
    def get_enhanced_kwargs(self, **kwargs) -> Dict[str, Any]:
        """
        获取增强的请求参数
        
        参数:
            **kwargs: 其他参数
            
        返回:
            Dict[str, Any]: 增强的参数字典
        """
        enhanced = {
            **kwargs,
            "cost_priority": self.llm_preferences.get("cost_priority", 0.5),
            "quality_threshold": self.llm_preferences.get("quality_threshold", 0.8)
        }
        return enhanced
    
    def build_system_message(self, context: Optional[Dict[str, Any]] = None) -> str:
        """
        构建系统消息
        
        参数:
            context: 上下文信息
            
        返回:
            str: 系统消息
        """
        base_message = f"你是一个专业的{self.agent_type}智能体，负责处理美妆相关的客户咨询。"
        
        # 添加上下文信息
        if context:
            if context.get("customer_profile"):
                base_message += f"\\n客户信息: {context['customer_profile']}"
            
            if context.get("conversation_history"):
                base_message += f"\\n对话历史: {context['conversation_history']}"
            
            if context.get("product_context"):
                base_message += f"\\n产品信息: {context['product_context']}"
        
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
            base_message += f"\\n\\n{guideline}"
        
        base_message += "\\n\\n请用中文回复，保持专业和友好的语调。"
        
        return base_message
    
    def update_routing_strategy(self, strategy: RoutingStrategy):
        """
        更新路由策略
        
        参数:
            strategy: 新的路由策略
        """
        self.routing_strategy = strategy
        self.logger.info(f"智能体路由策略更新: {self.agent_id} -> {strategy.value}")
    
    def update_llm_preferences(self, preferences: Dict[str, Any]):
        """
        更新LLM偏好设置
        
        参数:
            preferences: 新的偏好设置
        """
        self.llm_preferences.update(preferences)
        self.logger.info(f"智能体LLM偏好更新: {self.agent_id}")
    
    def validate_preferences(self, preferences: Dict[str, Any]) -> bool:
        """
        验证偏好设置
        
        参数:
            preferences: 要验证的偏好设置
            
        返回:
            bool: 验证是否通过
        """
        try:
            # 验证温度范围
            if "temperature" in preferences:
                temp = preferences["temperature"]
                if not isinstance(temp, (int, float)) or temp < 0 or temp > 2:
                    return False
            
            # 验证最大令牌数
            if "max_tokens" in preferences:
                tokens = preferences["max_tokens"]
                if not isinstance(tokens, int) or tokens < 1 or tokens > 32000:
                    return False
            
            # 验证成本优先级
            if "cost_priority" in preferences:
                priority = preferences["cost_priority"]
                if not isinstance(priority, (int, float)) or priority < 0 or priority > 1:
                    return False
            
            # 验证质量阈值
            if "quality_threshold" in preferences:
                threshold = preferences["quality_threshold"]
                if not isinstance(threshold, (int, float)) or threshold < 0 or threshold > 1:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"偏好设置验证失败: {str(e)}")
            return False
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        获取配置摘要
        
        返回:
            Dict[str, Any]: 配置摘要
        """
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tenant_id": self.tenant_id,
            "routing_strategy": self.routing_strategy.value if self.routing_strategy else None,
            "llm_preferences": self.llm_preferences.copy()
        }
    
    def reset_to_defaults(self):
        """重置到默认配置"""
        self.routing_strategy = RoutingStrategy.AGENT_OPTIMIZED
        self.llm_preferences = self._get_default_llm_preferences()
        self.logger.info(f"智能体配置已重置为默认值: {self.agent_id}")