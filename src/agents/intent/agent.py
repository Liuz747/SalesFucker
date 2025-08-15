"""
Intent Analysis Agent

LLM-powered intent classification for customer interactions in beauty consultations.
Identifies purchase intent, conversation stage, and specific customer needs.
"""

from typing import Dict, Any
from ..base import BaseAgent, AgentMessage, ThreadState
from src.llm import get_multi_llm_client
from src.prompts import get_prompt_manager
from utils import parse_intent_response
from src.llm.intelligent_router import RoutingStrategy
from utils import get_current_datetime, get_processing_time_ms


class IntentAnalysisAgent(BaseAgent):
    """
    意图分析智能体
    
    使用LLM分析客户购买意图和对话需求。
    专注于美妆咨询场景的意图识别和对话阶段判断。
    """
    
    def __init__(self, tenant_id: str):
        # MAS架构：使用成本优化策略进行快速意图分析
        super().__init__(
            agent_id=f"intent_analysis_{tenant_id}", 
            tenant_id=tenant_id,
            routing_strategy=RoutingStrategy.COST_FIRST  # 快速意图识别，成本优化
        )
        
        # LLM integration
        self.llm_client = get_multi_llm_client()
        self.prompt_manager = get_prompt_manager()
        
        self.logger.info(f"意图分析智能体初始化完成: {self.agent_id}")
    
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """
        处理意图分析消息
        
        分析单个消息的客户意图。
        
        参数:
            message: 包含待分析文本的消息
            
        返回:
            AgentMessage: 包含意图分析结果的响应
        """
        try:
            customer_input = message.payload.get("text", "")
            conversation_history = message.context.get("conversation_history", [])
            
            intent_result = await self._analyze_intent(customer_input, conversation_history)
            
            response_payload = {
                "intent_analysis": intent_result,
                "processing_agent": self.agent_id,
                "analysis_timestamp": get_current_datetime().isoformat()
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
            
            fallback_result = {
                "intent": "browsing",
                "category": "general",
                "confidence": 0.5,
                "urgency": "medium",
                "fallback": True
            }
            
            return await self.send_message(
                recipient=message.sender,
                message_type="response", 
                payload={"error": error_info, "intent_analysis": fallback_result},
                context=message.context
            )
    
    async def process_conversation(self, state: ThreadState) -> ThreadState:
        """
        处理对话状态中的意图分析
        
        在LangGraph工作流中执行意图分析，更新对话状态。
        
        参数:
            state: 当前对话状态
            
        返回:
            ThreadState: 更新后的对话状态
        """
        start_time = get_current_datetime()
        
        try:
            customer_input = state.customer_input
            conversation_history = state.conversation_history
            
            # 执行意图分析
            intent_result = await self._analyze_intent(customer_input, conversation_history)
            
            # 更新对话状态
            state.intent_analysis = intent_result
            state.active_agents.append(self.agent_id)
            
            # 根据意图分析结果设置市场策略提示
            self._set_strategy_hints(state, intent_result)
            
            # 更新处理统计
            processing_time = get_processing_time_ms(start_time)
            self.update_stats(processing_time)
            
            return state
            
        except Exception as e:
            await self.handle_error(e, {"thread_id": state.thread_id})
            
            # 设置降级意图分析
            state.intent_analysis = {
                "intent": "browsing",
                "category": "general",
                "confidence": 0.5,
                "urgency": "medium",
                "decision_stage": "awareness",
                "fallback": True,
                "agent_id": self.agent_id
            }
            
            return state
    
    async def _analyze_intent(self, customer_input: str, conversation_history: list = None) -> Dict[str, Any]:
        """
        使用LLM分析客户意图
        
        参数:
            customer_input: 客户输入文本
            conversation_history: 对话历史
            
        返回:
            Dict[str, Any]: 意图分析结果
        """
        try:
            # 格式化对话历史
            formatted_history = self.prompt_manager.format_conversation_history(
                conversation_history or []
            )
            
            # 获取意图分析提示词
            prompt = self.prompt_manager.get_prompt(
                "intent",
                "purchase_intent",
                customer_input=customer_input,
                conversation_history=formatted_history,
                previous_intent="unknown"
            )
            
            # 调用LLM分析
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm_client.chat_completion(messages, temperature=0.3)
            
            # 解析结构化响应
            intent_result = parse_intent_response(response)
            
            # 添加额外的分析信息
            intent_result["agent_id"] = self.agent_id
            intent_result["analysis_method"] = "llm_powered"
            intent_result["conversation_length"] = len(conversation_history or [])
            
            return intent_result
            
        except Exception as e:
            self.logger.error(f"意图分析失败: {e}")
            return {
                "intent": "browsing",
                "category": "general",
                "confidence": 0.5,
                "urgency": "medium",
                "decision_stage": "awareness",
                "fallback": True,
                "error": str(e),
                "agent_id": self.agent_id
            }
    
    def _set_strategy_hints(self, state: ThreadState, intent_result: Dict[str, Any]):
        """
        根据意图分析结果设置策略提示
        
        参数:
            state: 对话状态
            intent_result: 意图分析结果
        """
        # 根据产品类别设置市场策略提示
        category = intent_result.get("category", "general")
        intent_level = intent_result.get("intent", "browsing")
        urgency = intent_result.get("urgency", "medium")
        
        strategy_hints = {}
        
        # 根据意图级别设置策略
        if intent_level == "ready_to_buy":
            strategy_hints["approach"] = "closing_focused"
            strategy_hints["priority"] = "conversion"
        elif intent_level == "comparing":
            strategy_hints["approach"] = "competitive_advantage"
            strategy_hints["priority"] = "differentiation"
        elif intent_level == "interested":
            strategy_hints["approach"] = "educational"
            strategy_hints["priority"] = "trust_building"
        else:
            strategy_hints["approach"] = "exploratory"
            strategy_hints["priority"] = "rapport_building"
        
        # 根据紧急程度调整
        if urgency == "high":
            strategy_hints["response_speed"] = "immediate"
            strategy_hints["detail_level"] = "concise"
        elif urgency == "low":
            strategy_hints["response_speed"] = "thorough"
            strategy_hints["detail_level"] = "comprehensive"
        
        # 将策略提示存储在状态中
        if not hasattr(state, 'strategy_hints'):
            state.strategy_hints = {}
        state.strategy_hints.update(strategy_hints)
    
    def get_intent_metrics(self) -> Dict[str, Any]:
        """
        获取意图分析性能指标
        
        返回:
            Dict[str, Any]: 性能指标信息
        """
        return {
            "total_analyses": self.processing_stats["messages_processed"],
            "error_rate": self.processing_stats["errors"] / max(1, self.processing_stats["messages_processed"]) * 100,
            "average_processing_time": self.processing_stats["average_response_time"],
            "last_activity": self.processing_stats["last_activity"],
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id
        }