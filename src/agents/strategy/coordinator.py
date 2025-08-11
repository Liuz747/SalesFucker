"""
Market Strategy Coordinator

Coordinates different market strategy approaches for customer segments.
Selects and applies Premium, Budget, Youth, or Mature strategies.
"""

from typing import Dict, Any
from ..base import BaseAgent, AgentMessage, ThreadState
from ..sales.sales_strategies import analyze_customer_segment, get_strategy_for_segment, adapt_strategy_to_context
from src.llm import get_llm_client, get_prompt_manager
from src.llm.intelligent_router import RoutingStrategy
from src.utils import get_current_datetime, get_processing_time_ms


class MarketStrategyCoordinator(BaseAgent):
    """
    市场策略协调器
    
    根据客户细分选择和应用不同的营销策略。
    协调高端、预算、年轻和成熟客户的不同销售方法。
    """
    
    def __init__(self, tenant_id: str):
        # MAS架构：使用质量优化策略进行战略分析
        super().__init__(
            agent_id=f"market_strategy_{tenant_id}", 
            tenant_id=tenant_id,
            routing_strategy=RoutingStrategy.PERFORMANCE_FIRST  # 战略规划需要高质量分析
        )
        
        # LLM integration for strategy refinement
        self.llm_client = get_llm_client()
        self.prompt_manager = get_prompt_manager()
        
        # Strategy definitions for different segments
        self.strategy_profiles = {
            "premium": {
                "approach": "consultative_luxury",
                "tone": "sophisticated",
                "focus": "exclusivity_and_quality",
                "key_messages": ["premium_ingredients", "luxury_experience", "exclusive_access"],
                "price_sensitivity": "low",
                "decision_factors": ["quality", "prestige", "uniqueness"]
            },
            "budget": {
                "approach": "value_focused",
                "tone": "practical",
                "focus": "cost_effectiveness",
                "key_messages": ["great_value", "multi_purpose", "essential_needs"],
                "price_sensitivity": "high",
                "decision_factors": ["price", "functionality", "necessity"]
            },
            "youth": {
                "approach": "trend_driven",
                "tone": "energetic",
                "focus": "innovation_and_trends",
                "key_messages": ["trending", "social_media_worthy", "self_expression"],
                "price_sensitivity": "medium",
                "decision_factors": ["trends", "social_proof", "experimentation"]
            },
            "mature": {
                "approach": "trust_building",
                "tone": "respectful",
                "focus": "proven_results",
                "key_messages": ["proven_effectiveness", "gentle_formulation", "age_appropriate"],
                "price_sensitivity": "medium",
                "decision_factors": ["effectiveness", "safety", "reputation"]
            }
        }
        
        self.logger.info(f"市场策略协调器初始化完成: {self.agent_id}")
    
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """
        处理策略选择消息
        
        分析客户特征并选择合适的市场策略。
        
        参数:
            message: 包含客户信息的消息
            
        返回:
            AgentMessage: 包含策略建议的响应
        """
        try:
            customer_profile = message.payload.get("customer_profile", {})
            conversation_context = message.payload.get("conversation_context", {})
            
            strategy_recommendation = await self._select_and_refine_strategy(
                customer_profile, conversation_context
            )
            
            response_payload = {
                "strategy_recommendation": strategy_recommendation,
                "processing_agent": self.agent_id,
                "strategy_timestamp": get_current_datetime().isoformat()
            }
            
            return await self.send_message(
                recipient=message.sender,
                message_type="response",
                payload=response_payload,
                context=message.context
            )
            
        except Exception as e:
            error_context = {
                "message_id": message.message_id,
                "sender": message.sender
            }
            error_info = await self.handle_error(e, error_context)
            
            fallback_strategy = {
                "segment": "premium",
                "strategy": self.strategy_profiles["premium"],
                "confidence": 0.5,
                "fallback": True
            }
            
            return await self.send_message(
                recipient=message.sender,
                message_type="response",
                payload={"error": error_info, "strategy_recommendation": fallback_strategy},
                context=message.context
            )
    
    async def process_conversation(self, state: ThreadState) -> ThreadState:
        """
        处理对话状态中的策略选择
        
        在LangGraph工作流中选择和应用市场策略。
        
        参数:
            state: 当前对话状态
            
        返回:
            ThreadState: 更新后的对话状态
        """
        start_time = get_current_datetime()
        
        try:
            customer_profile = state.customer_profile
            conversation_context = {
                "sentiment": state.sentiment_analysis.get("sentiment", "neutral") if state.sentiment_analysis else "neutral",
                "intent": state.intent_analysis.get("intent", "browsing") if state.intent_analysis else "browsing",
                "urgency": state.intent_analysis.get("urgency", "medium") if state.intent_analysis else "medium",
                "customer_input": state.customer_input
            }
            
            # 选择和优化策略
            strategy_recommendation = await self._select_and_refine_strategy(
                customer_profile, conversation_context
            )
            
            # 更新对话状态
            state.agent_responses[self.agent_id] = {
                "strategy_recommendation": strategy_recommendation,
                "selected_segment": strategy_recommendation["segment"],
                "strategy_profile": strategy_recommendation["strategy"],
                "processing_complete": True
            }
            state.active_agents.append(self.agent_id)
            
            # 为其他智能体提供策略提示
            if not hasattr(state, 'strategy_hints'):
                state.strategy_hints = {}
            state.strategy_hints.update(strategy_recommendation["strategy"])
            
            # 更新处理统计
            processing_time = get_processing_time_ms(start_time)
            self.update_stats(processing_time)
            
            return state
            
        except Exception as e:
            await self.handle_error(e, {"thread_id": state.thread_id})
            
            # 设置默认策略
            state.agent_responses[self.agent_id] = {
                "strategy_recommendation": {
                    "segment": "premium",
                    "strategy": self.strategy_profiles["premium"],
                    "confidence": 0.5,
                    "fallback": True
                },
                "error": str(e),
                "agent_id": self.agent_id
            }
            
            return state
    
    async def _select_and_refine_strategy(
        self, 
        customer_profile: Dict[str, Any], 
        conversation_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        选择并优化市场策略
        
        参数:
            customer_profile: 客户档案
            conversation_context: 对话上下文
            
        返回:
            Dict[str, Any]: 策略推荐结果
        """
        try:
            # 1. 基础客户细分
            customer_segment = analyze_customer_segment(customer_profile)
            base_strategy = get_strategy_for_segment(customer_segment)
            
            # 2. 根据对话上下文调整策略
            adapted_strategy = adapt_strategy_to_context(base_strategy, conversation_context)
            
            # 3. 应用策略配置
            strategy_profile = self.strategy_profiles.get(customer_segment.value, self.strategy_profiles["premium"])
            
            # 4. LLM增强策略优化
            enhanced_strategy = await self._enhance_strategy_with_llm(
                customer_segment.value, adapted_strategy, conversation_context
            )
            
            # 5. 合并所有策略元素
            final_strategy = {
                **strategy_profile,
                **adapted_strategy,
                **enhanced_strategy
            }
            
            return {
                "segment": customer_segment.value,
                "strategy": final_strategy,
                "confidence": self._calculate_strategy_confidence(customer_profile, conversation_context),
                "reasoning": f"Selected {customer_segment.value} strategy based on customer profile and context",
                "agent_id": self.agent_id
            }
            
        except Exception as e:
            self.logger.error(f"策略选择失败: {e}")
            return {
                "segment": "premium",
                "strategy": self.strategy_profiles["premium"],
                "confidence": 0.5,
                "error": str(e),
                "fallback": True,
                "agent_id": self.agent_id
            }
    
    async def _enhance_strategy_with_llm(
        self, 
        segment: str, 
        base_strategy: Dict[str, Any], 
        conversation_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        使用LLM增强策略
        
        参数:
            segment: 客户细分
            base_strategy: 基础策略
            conversation_context: 对话上下文
            
        返回:
            Dict[str, Any]: 增强后的策略元素
        """
        try:
            # 构建策略增强提示
            strategy_prompt = f"""
As a marketing strategy expert, enhance the {segment} market strategy for this customer interaction.

Base Strategy: {base_strategy}
Customer Context: {conversation_context}
Segment Profile: {self.strategy_profiles.get(segment, {})}

Provide 3 specific enhancements:
1. Personalized messaging approach
2. Specific tactics for this interaction
3. Key value propositions to emphasize

Keep response concise and actionable.
"""
            
            messages = [{"role": "user", "content": strategy_prompt}]
            response = await self.llm_client.chat_completion(messages, temperature=0.6)
            
            # 简化解析 - 在生产环境中会更复杂
            enhanced_elements = {
                "llm_enhancement": response,
                "enhanced_messaging": f"Enhanced {segment} approach",
                "contextual_tactics": [f"Tactic for {segment} segment"],
                "personalized_value_props": [f"Value proposition for {segment}"]
            }
            
            return enhanced_elements
            
        except Exception as e:
            self.logger.warning(f"LLM策略增强失败: {e}")
            return {
                "llm_enhancement": f"Standard {segment} approach",
                "enhancement_fallback": True
            }
    
    def _calculate_strategy_confidence(
        self, 
        customer_profile: Dict[str, Any], 
        conversation_context: Dict[str, Any]
    ) -> float:
        """
        计算策略选择置信度
        
        参数:
            customer_profile: 客户档案
            conversation_context: 对话上下文
            
        返回:
            float: 置信度分数 (0.0-1.0)
        """
        confidence = 0.6  # 基础置信度
        
        # 根据客户档案完整度调整
        if customer_profile:
            if customer_profile.get("age"):
                confidence += 0.1
            if customer_profile.get("budget_preference"):
                confidence += 0.1
            if customer_profile.get("lifestyle"):
                confidence += 0.1
            if customer_profile.get("purchase_history"):
                confidence += 0.1
        
        # 根据对话上下文调整
        if conversation_context:
            if conversation_context.get("sentiment") != "neutral":
                confidence += 0.05
            if conversation_context.get("intent") != "browsing":
                confidence += 0.05
        
        return min(1.0, confidence)
    
    def get_strategy_metrics(self) -> Dict[str, Any]:
        """
        获取策略选择性能指标
        
        返回:
            Dict[str, Any]: 性能指标信息
        """
        return {
            "total_strategy_selections": self.processing_stats["messages_processed"],
            "error_rate": self.processing_stats["errors"] / max(1, self.processing_stats["messages_processed"]) * 100,
            "average_processing_time": self.processing_stats["average_response_time"],
            "last_activity": self.processing_stats["last_activity"],
            "available_strategies": list(self.strategy_profiles.keys()),
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id
        }