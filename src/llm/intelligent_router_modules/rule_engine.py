"""
规则引擎模块

负责应用路由规则和过滤逻辑。
"""

from typing import List
from datetime import datetime

from ..base_provider import BaseProvider, LLMRequest
from ..provider_config import GlobalProviderConfig, RoutingRule
from .models import RoutingContext


class RuleEngine:
    """规则引擎类"""
    
    def __init__(self):
        """初始化规则引擎"""
        pass
    
    async def apply_routing_rules(
        self,
        providers: List[BaseProvider],
        request: LLMRequest,
        context: RoutingContext,
        config: GlobalProviderConfig
    ) -> List[BaseProvider]:
        """应用路由规则过滤供应商"""
        tenant_config = config.get_tenant_config(context.tenant_id)
        if not tenant_config:
            return providers
        
        filtered_providers = []
        for provider in providers:
            # 检查是否有匹配的规则
            matching_rules = []
            for rule in tenant_config.routing_rules:
                if rule.is_active and await self._rule_matches(rule, request, context):
                    matching_rules.append(rule)
            
            # 按优先级排序
            matching_rules.sort(key=lambda r: r.priority)
            
            # 应用最高优先级规则
            if matching_rules:
                highest_priority_rule = matching_rules[0]
                if provider.provider_type == highest_priority_rule.target_provider:
                    filtered_providers.append(provider)
            else:
                # 没有匹配规则，包含该供应商
                filtered_providers.append(provider)
        
        return filtered_providers or providers  # 确保至少有一个供应商
    
    async def _rule_matches(
        self, 
        rule: RoutingRule, 
        request: LLMRequest, 
        context: RoutingContext
    ) -> bool:
        """检查路由规则是否匹配"""
        conditions = rule.conditions
        
        # 检查智能体类型
        if "agent_type" in conditions:
            if context.agent_type != conditions["agent_type"]:
                return False
        
        # 检查内容语言
        if "language" in conditions:
            if context.content_language != conditions["language"]:
                return False
        
        # 检查时间条件
        if "time_range" in conditions:
            current_hour = datetime.now().hour
            time_range = conditions["time_range"]
            if not (time_range.get("start", 0) <= current_hour <= time_range.get("end", 23)):
                return False
        
        # 检查多模态条件
        if "requires_multimodal" in conditions:
            if context.has_multimodal != conditions["requires_multimodal"]:
                return False
        
        return True