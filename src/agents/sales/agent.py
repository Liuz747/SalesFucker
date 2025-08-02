"""
销售智能体 - 轻量级核心模块

该模块作为销售智能体的核心，遵循模块化设计原则。
专注于智能体核心逻辑，将模板、策略等功能分离到专门模块。

核心功能:
- 智能体核心逻辑
- 对话协调和状态管理
- 模块间集成和错误处理
- LangGraph工作流节点处理
"""

from typing import Dict, Any

from ..core import BaseAgent, AgentMessage, ConversationState
from .sales_strategies import get_sales_strategies, analyze_customer_segment, get_strategy_for_segment, adapt_strategy_to_context
from src.utils import format_timestamp
from src.llm import get_llm_client, get_prompt_manager


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
        
        # LLM integration for dynamic responses
        self.llm_client = get_llm_client()
        self.prompt_manager = get_prompt_manager()
        
        # Strategy management
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
                "response_timestamp": format_timestamp()
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
            
            # 从IntentAnalysisAgent获取增强的客户分析数据
            intent_analysis = state.intent_analysis or {}
            customer_profile_data = intent_analysis.get("customer_profile", {})
            
            # 提取客户需求信息 (来自LLM分析)
            needs = {
                "skin_concerns": customer_profile_data.get("skin_concerns", []),
                "product_interests": customer_profile_data.get("product_interests", []),
                "urgency": customer_profile_data.get("urgency", "normal"),
                "experience_level": customer_profile_data.get("experience_level", "intermediate"),
                "budget_signals": customer_profile_data.get("budget_signals", [])
            }
            
            # 获取对话阶段 (来自LLM分析)
            stage_value = intent_analysis.get("conversation_stage", "consultation")
            
            # 使用LLM提取的信息丰富客户档案
            if customer_profile_data.get("skin_type_indicators"):
                state.customer_profile["inferred_skin_type"] = customer_profile_data["skin_type_indicators"][0]
            if customer_profile_data.get("budget_signals"):
                state.customer_profile["budget_preference"] = customer_profile_data["budget_signals"][0]
            if customer_profile_data.get("experience_level"):
                state.customer_profile["experience_level"] = customer_profile_data["experience_level"]
            
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
            
            # 生成LLM驱动的个性化响应
            response = await self._generate_llm_response(
                customer_input, needs, stage_value, adapted_strategy, state
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
    
    async def _generate_llm_response(self, customer_input: str, needs: Dict[str, Any],
                                   stage: str, strategy: Dict[str, Any], 
                                   state: ConversationState) -> str:
        """
        使用LLM生成个性化销售响应
        
        参数:
            customer_input: 客户输入
            needs: 客户需求分析
            stage: 对话阶段
            strategy: 销售策略
            state: 对话状态
            
        返回:
            str: LLM生成的个性化销售响应
        """
        try:
            # 准备提示词参数
            conversation_history = self.prompt_manager.format_conversation_history(
                state.conversation_history
            )
            
            # 获取销售咨询提示词
            prompt = self.prompt_manager.get_prompt(
                "sales",
                "consultation",
                brand_name=self.tenant_id,
                customer_input=customer_input,
                conversation_history=conversation_history,
                skin_type=state.customer_profile.get("skin_type", "not specified"),
                concerns=", ".join(needs.get("concerns", ["general consultation"])),
                budget_range=state.customer_profile.get("budget_range", "medium"),
                purchase_history=", ".join(state.customer_profile.get("purchase_history", ["none"])),
                tone=strategy.get("tone", "friendly"),
                tone_description=self._get_tone_description(strategy.get("tone", "friendly")),
                strategy=strategy.get("approach", "consultative")
            )
            
            # 调用LLM生成响应
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm_client.chat_completion(messages, temperature=0.8)
            
            return response
            
        except Exception as e:
            self.logger.error(f"LLM响应生成失败: {e}")
            # 降级到简单模板响应
            return self._generate_fallback_response(stage, strategy)
    
    async def _generate_sales_response(self, customer_input: str, context: Dict[str, Any]) -> str:
        """生成销售响应（LLM驱动）"""
        try:
            prompt = self.prompt_manager.get_prompt(
                "sales",
                "consultation", 
                customer_input=customer_input,
                brand_name=self.tenant_id
            )
            
            messages = [{"role": "user", "content": prompt}]
            return await self.llm_client.chat_completion(messages, temperature=0.8)
            
        except Exception as e:
            self.logger.error(f"销售响应生成失败: {e}")
            return self._generate_fallback_response("consultation", {"tone": "friendly"})
    
    def _get_tone_description(self, tone: str) -> str:
        """获取语调描述"""
        tone_descriptions = {
            "sophisticated": "elegant and refined",
            "energetic": "enthusiastic and exciting", 
            "professional": "expert and authoritative",
            "warm": "caring and personal",
            "friendly": "approachable and helpful"
        }
        return tone_descriptions.get(tone, "professional and helpful")
    
    def _generate_fallback_response(self, stage: str, strategy: Dict[str, Any]) -> str:
        """生成降级响应"""
        tone = strategy.get("tone", "friendly")
        
        if stage == "greeting":
            return "Hello! Welcome! I'm excited to help you find the perfect beauty products today. What brings you here?"
        elif stage == "consultation":
            return "I'd love to help you find products that work perfectly for your needs. Could you tell me more about what you're looking for?"
        else:
            return "Thank you for your interest! How can I help you with your beauty needs today?"
    
    def get_conversation_metrics(self) -> Dict[str, Any]:
        """获取销售对话性能指标"""
        return {
            "total_conversations": self.processing_stats["messages_processed"],
            "error_rate": self.processing_stats["errors"] / max(1, self.processing_stats["messages_processed"]) * 100,
            "last_activity": self.processing_stats["last_activity"],
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id
        } 