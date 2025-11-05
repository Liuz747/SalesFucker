"""
Sentiment & Intent Analysis Agent

LLM-powered comprehensive analysis for customer interactions in beauty consultations.
Combines sentiment analysis with intent recognition for unified customer understanding.
Provides emotional context, purchase intent, and customer needs assessment.
"""

from typing import Dict, Any
from uuid import uuid4

from langfuse import observe

from ..base import BaseAgent, parse_json_response
from core.prompts.templates import get_default_prompt, AgentType, PromptType
from utils import get_current_datetime, get_processing_time_ms
from config import mas_config
from infra.runtimes import CompletionsRequest
from libs.types import Message


class SentimentAnalysisAgent(BaseAgent):
    """
    情感与意图分析智能体

    使用LLM综合分析客户情感状态和购买意图。
    专注于美妆咨询场景的情感识别、意图判断和客户需求评估。

    整合功能：
    - 情感分析：情绪状态、满意度、紧迫性
    - 意图识别：购买意图、对话阶段、产品兴趣
    - 策略提示：基于分析结果提供销售策略建议
    """
    
    def __init__(self):
        super().__init__()

        # 使用系统配置的默认provider和模型
        self.llm_provider = mas_config.DEFAULT_LLM_PROVIDER
        self.llm_model = "openai/gpt-5-chat"  # 默认模型，LLMClient会根据provider自动选择合适模型

        self.logger.info(f"情感与意图分析智能体初始化完成: {self.agent_id}")

    @observe(name="sentiment-intent-analysis", as_type="generation")
    async def process_conversation(self, state: dict) -> dict:
        """
        处理对话状态中的情感与意图综合分析

        在LangGraph工作流中执行综合分析，更新对话状态。

        参数:
            state: 当前对话状态

        返回:
            ThreadState: 更新后的对话状态
        """
        start_time = get_current_datetime()

        try:
            customer_input = state.get("customer_input", "")
            conversation_history = state.get("conversation_history", [])
            conversation_context = self._build_conversation_context(state)

            # 执行综合分析（情感 + 意图）
            analysis_result = await self._analyze_sentiment_and_intent(
                customer_input, conversation_history, conversation_context
            )

            # 更新对话状态 - 保持向后兼容
            state["sentiment_analysis"] = analysis_result.get("sentiment", {})
            state["intent_analysis"] = analysis_result.get("intent", {})
            state.setdefault("active_agents", []).append(self.agent_id)


            return state

        except Exception as e:
            self.logger.error(f"Agent processing failed: {e}", exc_info=True)

            # 设置降级分析结果
            state["sentiment_analysis"] = {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.5,
                "emotions": [],
                "fallback": True,
                "agent_id": self.agent_id
            }
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

    async def _analyze_sentiment_and_intent(
        self,
        customer_input: str,
        conversation_history: list = None,
        conversation_context: str = ""
    ) -> Dict[str, Any]:
        """
        使用LLM综合分析客户情感和意图

        将情感分析和意图识别合并为一次LLM调用，提高效率。

        参数:
            customer_input: 客户输入文本
            conversation_history: 对话历史
            conversation_context: 对话上下文

        返回:
            Dict[str, Any]: 包含情感和意图的综合分析结果
        """
        try:
            # 构建对话历史文本
            history_text = ""
            if conversation_history:
                recent_history = conversation_history[-5:]  # 最近5轮对话
                history_text = f"\n对话历史：\n{self._format_history(recent_history)}\n"

            # 渲染情感分析提示词模板
            prompt = render_agent_prompt(
                "sentiment",
                "sentiment_analysis",
                history_text=history_text,
                customer_input=customer_input,
            )

            # 调用LLM分析
            messages = [
                Message(role="user", content=prompt)
            ]
            request = CompletionsRequest(
                id=uuid4(),
                provider=self.llm_provider,
                model=self.llm_model,
                temperature=0.3,
                messages=messages
            )
            print(f"[DEBUG] 情感分析 - 发送请求: Provider={self.llm_provider}, Model={self.llm_model}")
            llm_response = await self.invoke_llm(request)
            print(f"[DEBUG] 情感分析 - 收到响应: {type(llm_response)}, Content length: {len(str(llm_response.content)) if llm_response and llm_response.content else 0}")
            raw_response = (
                llm_response.content
                if isinstance(llm_response.content, str)
                else str(llm_response.content)
            )

            # 解析结构化响应
            default_result = {
                "sentiment": {
                    "sentiment": "neutral",
                    "score": 0.0,
                    "confidence": 0.5,
                    "emotions": [],
                    "satisfaction": "unknown",
                    "urgency": "medium"
                },
                "intent": {
                    "intent": "browsing",
                    "category": "general",
                    "confidence": 0.5,
                    "urgency": "medium",
                    "decision_stage": "awareness",
                    "needs": [],
                    "customer_profile": {}
                }
            }
            analysis_result = parse_json_response(raw_response, default_result=default_result)

            # 添加元数据
            analysis_result["sentiment"]["agent_id"] = self.agent_id
            analysis_result["sentiment"]["analysis_method"] = "llm_powered"
            analysis_result["intent"]["agent_id"] = self.agent_id
            analysis_result["intent"]["analysis_method"] = "llm_powered"
            analysis_result["intent"]["conversation_length"] = len(conversation_history or [])

            return analysis_result

        except Exception as e:
            self.logger.error(f"综合分析失败: {e}")
            return {
                "sentiment": {
                    "sentiment": "neutral",
                    "score": 0.0,
                    "confidence": 0.5,
                    "emotions": [],
                    "fallback": True,
                    "error": str(e),
                    "agent_id": self.agent_id
                },
                "intent": {
                    "intent": "browsing",
                    "category": "general",
                    "confidence": 0.5,
                    "urgency": "medium",
                    "decision_stage": "awareness",
                    "fallback": True,
                    "error": str(e),
                    "agent_id": self.agent_id
                }
            }

    def _format_history(self, history: list) -> str:
        """
        格式化对话历史

        参数:
            history: 对话历史列表

        返回:
            str: 格式化的对话历史文本
        """
        if not history:
            return ""

        formatted = []
        for i, msg in enumerate(history):
            if isinstance(msg, dict):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                formatted.append(f"{role}: {content}")
            else:
                formatted.append(str(msg))

        return "\n".join(formatted)


    def _build_conversation_context(self, state: dict) -> str:
        """
        构建对话上下文信息
        
        参数:
            state: 对话状态
            
        返回:
            str: 格式化的对话上下文
        """
        context_parts = []
        
        # 客户档案信息
        if state.get("customer_profile"):
            profile_info = []
            customer_profile = state.get("customer_profile", {})
            if customer_profile.get("skin_type"):
                profile_info.append(f"Skin type: {customer_profile['skin_type']}")
            if customer_profile.get("previous_purchases"):
                profile_info.append(f"Previous purchases: {len(customer_profile['previous_purchases'])} items")
            
            if profile_info:
                context_parts.append("Customer profile: " + ", ".join(profile_info))
        
        # 对话历史
        if state.get("conversation_history"):
            recent_history = state["conversation_history"][-3:]
            context_parts.append("Recent conversation: " + " | ".join(recent_history))
        
        # 合规和意图信息
        compliance_result = state.get("compliance_result")
        if compliance_result:
            context_parts.append(f"Compliance status: {compliance_result.get('status', 'unknown')}")

        return " | ".join(context_parts) if context_parts else "Initial interaction"
