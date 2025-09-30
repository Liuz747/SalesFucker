"""
Intent Analysis Agent

LLM-powered intent classification for customer interactions in beauty consultations.
Identifies purchase intent, conversation stage, and specific customer needs.
"""

from typing import Dict, Any

from ..base import BaseAgent, parse_json_response

from utils import get_current_datetime, get_processing_time_ms

class IntentAnalysisAgent(BaseAgent):
    """
    意图分析智能体
    
    使用LLM分析客户购买意图和对话需求。
    专注于美妆咨询场景的意图识别和对话阶段判断。
    """
    
    def __init__(self):
        # MAS架构：使用成本优化策略进行快速意图分析
        super().__init__()
        
        # LLM integration

        self.logger.info(f"意图分析智能体初始化完成: {self.agent_id}")
    
    async def process_conversation(self, state: dict) -> dict:
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
            customer_input = state.get("customer_input", "")
            conversation_history = state.get("conversation_history", [])
            
            # 执行意图分析
            intent_result = await self._analyze_intent(customer_input, conversation_history)
            
            # 更新对话状态
            state["intent_analysis"] = intent_result
            state.setdefault("active_agents", []).append(self.agent_id)
            
            # 根据意图分析结果设置市场策略提示
            self._set_strategy_hints(state, intent_result)

            return state
            
        except Exception as e:
            self.logger.error(f"Agent processing failed: {e}", exc_info=True)
            
            # 设置降级意图分析
            state["intent_analysis"] = {
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
            # 简化的意图分析提示词
            history_text = ""
            if conversation_history:
                history_text = f"对话历史：{str(conversation_history)}\n\n"
            
            prompt = f"""分析以下客户的购买意图：

{history_text}客户输入：{customer_input}

请返回JSON格式：
{{
    "intent": "interested",
    "category": "skincare",
    "confidence": 0.8,
    "urgency": "medium"
}}"""
            
            # 调用LLM分析
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm_call(messages, temperature=0.3)

            # 解析结构化响应
            default_result = {
                "intent": "browsing",
                "confidence": 0.5,
                "needs": [],
                "priority": "medium",
                "next_action": "continue"
            }
            intent_result = parse_json_response(response, default_result=default_result)

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
    
    def _set_strategy_hints(self, state: dict, intent_result: dict):
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
        state.setdefault("strategy_hints", {}).update(strategy_hints)

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