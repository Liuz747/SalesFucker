"""
Appointment Intent Analysis Agent - 邀约到店意向分析智能体

专注于分析客户的邀约到店意向，基于历史对话内容判断用户是否有线下到店的需求和倾向。

核心职责:
- 基于近5轮对话分析邀约意向
- 意向强度和时间窗口判断
- 为sales agent提供邀约洞察
- 智能记忆管理和检索
"""

from typing import Dict, Any, List
from langfuse import observe

from ..base import BaseAgent
from .intent_analyzer import AppointmentIntentAnalyzer
from utils import get_current_datetime
from utils.token_manager import TokenManager
from config import mas_config
from core.memory import StorageManager
from libs.types import Message


class AppointmentIntentAgent(BaseAgent):
    """
    邀约到店意向分析智能体

    基于用户近5轮对话内容，智能分析用户是否有线下到店的意向。
    为销售团队提供精准的邀约时机判断。

    设计特点：
    - 深度语义理解：使用LLM分析对话中的邀约信号
    - 时间窗口预测：判断最佳的邀约时间范围
    - 意向强度量化：提供明确的意向评分
    - 记忆集成：利用系统记忆进行上下文分析
    """

    def __init__(self):
        super().__init__()
        self.llm_provider = mas_config.DEFAULT_LLM_PROVIDER
        # 仿照sales agent，使用相同的OpenRouter模型
        self.llm_model = "openai/gpt-4o-mini"

        self.memory_manager = StorageManager()

        # 初始化意向分析器
        self.intent_analyzer = AppointmentIntentAnalyzer(
            llm_provider=self.llm_provider,
            llm_model=self.llm_model,
            invoke_llm_fn=self.invoke_llm
        )

    @observe(name="appointment-intent-analysis", as_type="generation")
    async def process_conversation(self, state: dict) -> dict:
        """
        处理对话状态中的邀约到店意向分析

        工作流程：
        1. 检索记忆上下文（近5轮对话）
        2. 分析邀约意向信号
        3. 判断意向强度和时间窗口
        4. 生成分析报告
        5. 更新状态传递给sales agent

        参数:
            state: 当前对话状态，包含 customer_input, tenant_id, thread_id

        返回:
            dict: 更新后的对话状态，包含 appointment_intent 信息
        """
        start_time = get_current_datetime()

        try:
            self.logger.info("=== Appointment Intent Agent ===")

            customer_input = state.get("customer_input", "")
            tenant_id = state.get("tenant_id")
            thread_id = state.get("thread_id")

            self.logger.debug(f"分析邀约意向 - 输入: {str(customer_input)[:100]}...")

            # 步骤1: 检索记忆上下文（近5轮对话）
            user_text = self._input_to_text(customer_input)
            short_term_messages, long_term_memories = await self.memory_manager.retrieve_context(
                tenant_id=tenant_id,
                thread_id=thread_id,
                query_text=user_text,
            )

            # 提取近5轮用户消息用于分析
            recent_user_messages = self._extract_recent_user_messages(
                short_term_messages, max_rounds=5
            )

            self.logger.info(f"记忆检索完成 - 分析轮次: {len(recent_user_messages)}")

            # 步骤2: 执行邀约意向分析
            intent_result = await self._analyze_appointment_intent(
                current_input=user_text,
                recent_messages=recent_user_messages
            )

            self.logger.info(f"邀约意向分析结果 - 意向强度: {intent_result.get('intent_strength', 0)}, "
                           f"时间窗口: {intent_result.get('time_window', 'unknown')}, "
                           f"tokens_used: {intent_result.get('total_tokens', 0)}")

            # 步骤3: 更新对话状态
            updated_state = self._update_state_with_intent(
                state, intent_result, recent_user_messages
            )

            processing_time = (get_current_datetime() - start_time).total_seconds()
            self.logger.info(f"邀约意向分析完成: 耗时{processing_time:.2f}s, "
                           f"意向={intent_result.get('intent_strength', 0)}")
            self.logger.info("=== Appointment Intent Agent 处理完成 ===")

            return updated_state

        except Exception as e:
            self.logger.error(f"邀约意向分析失败: {e}", exc_info=True)
            self.logger.error(f"失败时的输入: {state.get('customer_input', 'None')}")
            # 降级处理：返回无意向状态
            return self._create_fallback_state(state)

    def _input_to_text(self, content) -> str:
        """将输入转换为文本"""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for node in content:
                value = getattr(node, "content", None)
                parts.append(value if isinstance(value, str) else str(node))
            return "\n".join(parts)
        return str(content)

    def _extract_recent_user_messages(self, messages: List, max_rounds: int = 5) -> List[str]:
        """
        从记忆中提取最近N轮用户消息

        Args:
            messages: 短期记忆消息列表
            max_rounds: 最大提取轮数

        Returns:
            List[str]: 用户消息内容列表
        """
        try:
            recent_messages = []
            user_message_count = 0

            # 从最新消息开始倒序提取
            for msg in reversed(messages):
                if user_message_count >= max_rounds:
                    break

                # 处理不同格式的消息对象
                if isinstance(msg, dict):
                    role = msg.get("role")
                    content = msg.get("content")
                elif hasattr(msg, 'role'):
                    role = msg.role
                    content = getattr(msg, 'content', None)
                else:
                    continue

                if role == "user" and content and str(content).strip():
                    recent_messages.insert(0, str(content))
                    user_message_count += 1

            self.logger.debug(f"提取用户消息: {len(recent_messages)}轮")
            return recent_messages

        except Exception as e:
            self.logger.error(f"提取用户消息失败: {e}")
            return []

    async def _analyze_appointment_intent(self, current_input: str, recent_messages: List[str]) -> dict:
        """
        分析邀约到店意向

        Args:
            current_input: 当前用户输入
            recent_messages: 最近用户消息列表

        Returns:
            dict: 意向分析结果
        """
        try:
            # 构建分析上下文
            analysis_context = {
                "current_input": current_input,
                "recent_messages": recent_messages,
                "message_count": len(recent_messages),
                "analysis_type": "appointment_intent",
                "conversation_stage": "multi_round_analysis"
            }

            # 调用意向分析器
            result = await self.intent_analyzer.analyze_intent(analysis_context)

            # 添加分析元数据
            result["analysis_metadata"] = {
                "analyzed_messages": len(recent_messages),
                "analysis_timestamp": get_current_datetime().isoformat(),
                "input_length": len(current_input),
                "analysis_type": "appointment_intent"
            }

            return result

        except Exception as e:
            self.logger.error(f"邀约意向分析失败: {e}")
            # 返回默认的无意向结果
            return {
                "intent_strength": 0.0,
                "time_window": "unknown",
                "confidence": 0.0,
                "signals": [],
                "recommendation": "no_appointment",
                "tokens_used": 0,
                "analysis_metadata": {
                    "error": str(e),
                    "fallback": True
                }
            }

    def _update_state_with_intent(self, state: dict, intent_result: dict, recent_messages: List[str]) -> dict:
        """
        更新状态，添加邀约意向信息

        Args:
            state: 原始状态
            intent_result: 意向分析结果
            recent_messages: 分析用的消息列表

        Returns:
            dict: 更新后的状态
        """
        current_time = get_current_datetime()

        # 创建标准化的Agent响应数据
        agent_response_data = TokenManager.extract_agent_token_info(
            agent_id=self.agent_id,
            agent_type="appointment_intent",
            llm_response=None,
            response_content=str(intent_result),
            timestamp=current_time
        )

        # 更新token信息
        token_info = {
            "input_tokens": intent_result.get("input_tokens", 0),
            "output_tokens": intent_result.get("output_tokens", 0),
            "total_tokens": intent_result.get("total_tokens", intent_result.get("tokens_used", 0))
        }
        agent_response_data["token_usage"] = token_info
        agent_response_data["tokens_used"] = token_info["total_tokens"]

        # 核心传递字段：appointment_intent
        appointment_intent = {
            "intent_strength": intent_result.get("intent_strength", 0.0),  # 0.0-1.0
            "time_window": intent_result.get("time_window", "unknown"),     # "immediate", "this_week", "this_month", "unknown"
            "confidence": intent_result.get("confidence", 0.0),              # 0.0-1.0
            "signals": intent_result.get("signals", []),                    # 检测到的意向信号列表
            "recommendation": intent_result.get("recommendation", "no_appointment"),  # "suggest_appointment", "wait_signal", "no_appointment"
            "analyzed_message_count": len(recent_messages),
            "analysis_timestamp": current_time.isoformat()
        }

        # 状态更新 - 直接设置到model字段避免并发冲突
        state["appointment_intent"] = appointment_intent
        state["values"] = state.get("values", {})

        # 备份存储在 values 结构中
        if state.get("values") is None:
            state["values"] = {}
        if state["values"].get("agent_responses") is None:
            state["values"]["agent_responses"] = {}

        agent_data = {
            "agent_type": "appointment_intent",
            "appointment_intent": appointment_intent,
            "intent_result": intent_result,
            "analyzed_messages": recent_messages,
            "timestamp": current_time,
            "token_usage": token_info,
            "tokens_used": token_info["total_tokens"],
            "response_length": len(str(intent_result))
        }

        state["values"]["agent_responses"][self.agent_id] = agent_data

        # 更新活跃智能体列表
        active_agents = state.get("active_agents")
        if active_agents is None:
            active_agents = []
        active_agents.append(self.agent_id)
        state["active_agents"] = active_agents

        self.logger.info(f"appointment intent 字段已添加: strength={appointment_intent['intent_strength']}, "
                        f"window={appointment_intent['time_window']}")

        return state

    def _create_fallback_state(self, state: dict) -> dict:
        """
        创建降级处理状态

        Args:
            state: 原始状态

        Returns:
            dict: 包含默认意向信息的状态
        """
        current_time = get_current_datetime()

        # 默认无意向状态
        appointment_intent = {
            "intent_strength": 0.0,
            "time_window": "unknown",
            "confidence": 0.0,
            "signals": [],
            "recommendation": "no_appointment",
            "analyzed_message_count": 0,
            "analysis_timestamp": current_time.isoformat(),
            "fallback": True
        }

        state["appointment_intent"] = appointment_intent

        # 简化的values存储
        if state.get("values") is None:
            state["values"] = {}
        if state["values"].get("agent_responses") is None:
            state["values"]["agent_responses"] = {}

        state["values"]["agent_responses"][self.agent_id] = {
            "agent_type": "appointment_intent",
            "appointment_intent": appointment_intent,
            "timestamp": current_time,
            "fallback": True,
            "error": "processing_failed"
        }

        return state