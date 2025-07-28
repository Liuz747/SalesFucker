"""
销售智能体 - 轻量级核心模块

该模块作为销售智能体的核心，遵循模块化设计原则。
专注于智能体核心逻辑，将模板、策略等功能分离到专门模块。

核心功能:
- 智能体核心逻辑（< 150行）
- 对话协调和状态管理
- 模块间集成和错误处理
- LangGraph工作流节点处理
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .core import BaseAgent, AgentMessage, ConversationState
from .sales.conversation_templates import get_conversation_templates, get_conversation_responses, get_tone_variations
from .sales.sales_strategies import get_sales_strategies, analyze_customer_segment, get_strategy_for_segment, adapt_strategy_to_context
from .sales.need_assessment import analyze_customer_needs, determine_conversation_stage, ConversationStage

logger = logging.getLogger(__name__)


class SalesAgent(BaseAgent):
    """
    销售智能体 - 核心控制器
    
    负责协调各个销售模块，保持轻量级核心设计。
    按照行业标准保持在150行以内，专注于核心逻辑。
    
    职责:
    - 智能体生命周期管理
    - 模块间协调和集成
    - 对话状态管理
    - 错误处理和降级
    """
    
    def __init__(self, tenant_id: str):
        super().__init__(f"sales_agent_{tenant_id}", tenant_id)
        # 使用专门模块加载配置
        self.conversation_templates = get_conversation_templates()
        self.sales_strategies = get_sales_strategies()
        
        self.logger.info(f"销售智能体初始化完成: {self.agent_id}")
    
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """
        处理销售消息
        
        对单个消息执行销售对话处理，返回个性化销售响应。
        
        参数:
            message: 包含客户输入的智能体消息
            
        返回:
            AgentMessage: 包含销售响应的消息
        """
        try:
            customer_input = message.payload.get("text", "")
            
            # 生成销售响应
            sales_response = await self._generate_sales_response(customer_input, message.context)
            
            # 构建响应载荷
            response_payload = {
                "sales_response": sales_response,
                "agent_type": "sales",
                "processing_agent": self.agent_id,
                "response_timestamp": datetime.utcnow().isoformat()
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
                "sender": message.sender,
                "processing_agent": self.agent_id
            }
            error_info = await self.handle_error(e, error_context)
            
            return await self.send_message(
                recipient=message.sender,
                message_type="response",
                payload={"error": error_info, "sales_response": "I apologize, but I'm having trouble processing your request right now."},
                context=message.context
            )
    
    async def process_conversation(self, state: ConversationState) -> ConversationState:
        """
        处理对话状态（LangGraph工作流节点）
        
        在LangGraph工作流中执行销售对话处理，生成个性化销售响应。
        
        参数:
            state: 当前对话状态
            
        返回:
            ConversationState: 更新后的对话状态
        """
        try:
            customer_input = state.customer_input
            
            # 使用专门模块分析客户需求和对话阶段
            needs = analyze_customer_needs(customer_input)
            stage = determine_conversation_stage(customer_input, state.conversation_history)
            
            # 客户细分和策略选择
            customer_segment = analyze_customer_segment(state.customer_profile)
            strategy = get_strategy_for_segment(customer_segment)
            
            # 根据上下文调整策略
            context = {
                "sentiment": getattr(state, "sentiment", "neutral"),
                "urgency": needs.get("urgency", "normal"),
                "purchase_intent": getattr(state, "purchase_intent", "browsing")
            }
            adapted_strategy = adapt_strategy_to_context(strategy, context)
            
            # 生成个性化响应
            response = self._generate_conversation_response(
                customer_input, needs, stage.value, adapted_strategy, state
            )
            
            # 更新对话状态
            state.sales_response = response
            state.active_agents.append(self.agent_id)
            state.conversation_history.extend([
                f"Customer: {customer_input}",
                f"Sales: {response}"
            ])
            
            # 更新处理统计
            self.update_stats(time_taken=50)
            
            return state
            
        except Exception as e:
            await self.handle_error(e, {"conversation_id": state.conversation_id})
            state.error_state = "sales_processing_error"
            return state
    
    def _generate_conversation_response(self, customer_input: str, needs: Dict[str, Any],
                                      stage: str, strategy: Dict[str, Any], 
                                      state: ConversationState) -> str:
        """
        生成对话响应（轻量级方法）
        
        参数:
            customer_input: 客户输入
            needs: 客户需求分析
            stage: 对话阶段
            strategy: 销售策略
            state: 对话状态
            
        返回:
            str: 个性化销售响应
        """
        templates = self.conversation_templates.get(stage, {})
        tone_variations = get_tone_variations()
        
        # 选择基础响应模板
        if stage == "greeting":
            template_key = "new_customer" if not state.customer_profile else "returning_customer"
            base_response = templates.get(template_key, "Hello! How can I help you today?")
        elif stage == "consultation":
            base_response = templates.get("skin_analysis", "Let me help you find the perfect products.")
        else:
            base_response = templates.get("confident_close", "How can I help you today?")
        
        # 应用语调调整
        tone = strategy.get("tone", "friendly")
        if tone in tone_variations:
            tone_template = tone_variations[tone].get("recommendation", base_response)
            base_response = tone_template.format(product="our recommended products")
        
        return base_response
    
    async def _generate_sales_response(self, customer_input: str, context: Dict[str, Any]) -> str:
        """生成销售响应（简化版本）"""
        return ("Thank you for your message! I'm here to help you find the perfect beauty products. "
                "Could you tell me a bit more about what you're looking for today?")
    
    def get_conversation_metrics(self) -> Dict[str, Any]:
        """获取销售对话性能指标"""
        return {
            "total_conversations": self.processing_stats["messages_processed"],
            "error_rate": self.processing_stats["errors"] / max(1, self.processing_stats["messages_processed"]) * 100,
            "last_activity": self.processing_stats["last_activity"],
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id
        } 