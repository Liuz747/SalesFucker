"""
Appointment Intent Analysis Agent - 邀约到店意向分析智能体

专注于分析客户的邀约到店意向，基于历史对话内容判断用户是否有线下到店的需求和倾向。

核心职责:
- 基于近5轮对话分析邀约意向
- 意向强度和时间窗口判断
- 为sales agent提供邀约洞察
- 智能记忆管理和检索
"""

from langfuse import observe

from typing import Optional

from core.memory import StorageManager
from utils import get_current_datetime
from ..base import BaseAgent
from .intent_analyzer import AppointmentIntentAnalyzer
from utils.appointment_time_parser import parse_appointment_time


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

        self.memory_manager = StorageManager()

        # 初始化意向分析器
        self.intent_analyzer = AppointmentIntentAnalyzer(
            llm_provider="openrouter",
            llm_model="openai/gpt-4o-mini",
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

    def _extract_recent_user_messages(self, messages: list, max_rounds: int = 5) -> list[str]:
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

    async def _analyze_appointment_intent(self, current_input: str, recent_messages: list[str]) -> dict:
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

    def _update_state_with_intent(self, state: dict, intent_result: dict, recent_messages: list[str]) -> dict:
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

        # 更新token信息
        token_info = {
            "input_tokens": intent_result.get("input_tokens", 0),
            "output_tokens": intent_result.get("output_tokens", 0),
            "total_tokens": intent_result.get("total_tokens", intent_result.get("tokens_used", 0))
        }

        # 创建标准化的Agent响应数据 (原TokenManager逻辑)
        agent_response_data = {
            "agent_id": self.agent_id,
            "agent_type": "appointment_intent",
            "response": str(intent_result),
            "token_usage": token_info,
            "tokens_used": token_info["total_tokens"],
            "response_length": len(str(intent_result)),
            "timestamp": current_time
        }

        # 核心传递字段：appointment_intent
        appointment_intent = {
            "intent_strength": intent_result.get("intent_strength", 0.0),  # 0.0-1.0
            "time_window": intent_result.get("time_window", "unknown"),     # "immediate", "this_week", "this_month", "unknown"
            "confidence": intent_result.get("confidence", 0.0),              # 0.0-1.0
            "signals": intent_result.get("signals", []),                    # 检测到的意向信号列表
            "recommendation": intent_result.get("recommendation", "no_appointment"),  # "suggest_appointment", "wait_signal", "no_appointment"
            "analyzed_message_count": len(recent_messages),
            "analysis_timestamp": current_time.isoformat(),
            # 新增：提取的实体信息
            "extracted_entities": intent_result.get("extracted_entities", {})
        }

        # 处理实体提取结果，生成 business_outputs
        business_outputs = self._generate_business_outputs(
            intent_result, appointment_intent, recent_messages
        )

        # 状态更新 - 直接设置到model字段避免并发冲突
        state["appointment_intent"] = appointment_intent
        state["business_outputs"] = business_outputs  # 新增：设置业务输出
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
        
        # 添加 token 计数到顶层状态
        state["input_tokens"] = token_info["input_tokens"]
        state["output_tokens"] = token_info["output_tokens"]

        return state

    def _generate_business_outputs(self, intent_result: dict, appointment_intent: dict, recent_messages: list[str]) -> dict:
        """
        基于意向分析结果生成业务输出

        Args:
            intent_result: LLM分析结果
            appointment_intent: 标准化的意向信息
            recent_messages: 最近的用户消息

        Returns:
            dict: 结构化的业务输出，包含邀约信息
        """
        try:
            # 优化生成逻辑：只要有有效实体信息就生成business_outputs，不仅依赖recommendation
            # 这样可以更好地处理各种意图场景，提高邀约信息提取的健壮性

            # 提取实体信息
            extracted_entities = intent_result.get("extracted_entities", {})
            entity_confidence = extracted_entities.get("entity_confidence", {})

            # 获取时间表达式
            time_expression = extracted_entities.get("time_expression")

            # 检查是否有足够的有效实体信息来生成邀约
            has_valid_entities = False
            if extracted_entities.get("name") and entity_confidence.get("name", 0) > 0.5:
                has_valid_entities = True
            if time_expression and entity_confidence.get("time_expression", 0) > 0.3:  # 降低时间置信度要求
                has_valid_entities = True
            if extracted_entities.get("phone") and entity_confidence.get("phone", 0) > 0.5:
                has_valid_entities = True

            # 如果没有任何有效实体信息，则不生成business_outputs
            if not has_valid_entities:
                self.logger.debug("未提取到有效实体信息，跳过business_outputs生成")
                return None

            # 解析时间
            parsed_time = None
            if time_expression and entity_confidence.get("time_expression", 0) > 0.5:
                timestamp_ms, parse_info = parse_appointment_time(time_expression)
                if timestamp_ms:
                    parsed_time = timestamp_ms
                    self.logger.info(f"时间解析成功: {time_expression} -> {timestamp_ms} ({parse_info.get('method', 'unknown')})")
                else:
                    self.logger.warning(f"时间解析失败: {time_expression} - {parse_info.get('error', 'unknown error')}")

            # 构建邀约信息
            invitation_data = {
                "status": 1,  # 1表示待确认的邀约
                "time": parsed_time or 0,
                "service": extracted_entities.get("service"),
                "name": extracted_entities.get("name"),
                "phone": self._parse_phone_number(extracted_entities.get("phone")) if extracted_entities.get("phone") else None,
                # 添加元数据信息
                "extraction_metadata": {
                    "intent_strength": appointment_intent.get("intent_strength", 0),
                    "confidence": appointment_intent.get("confidence", 0),
                    "entity_confidence": entity_confidence,
                    "time_expression_original": time_expression,
                    "time_parse_info": parse_info if time_expression else None,
                    "analyzed_message_count": len(recent_messages),
                    "extraction_timestamp": get_current_datetime().isoformat()
                }
            }

            self.logger.info(f"生成邀约信息: status={invitation_data['status']}, "
                           f"time={invitation_data['time']}, "
                           f"service={invitation_data['service']}, "
                           f"name={invitation_data['name']}, "
                           f"phone={invitation_data['phone']}")

            return invitation_data

        except Exception as e:
            self.logger.error(f"生成业务输出失败: {e}", exc_info=True)
            return None

    def _parse_phone_number(self, phone_str: str) -> Optional[int]:
        """
        解析电话号码为整数

        Args:
            phone_str: 电话号码字符串

        Returns:
            Optional[int]: 解析后的电话号码，失败返回None
        """
        if not phone_str:
            return None

        try:
            # 移除所有非数字字符
            clean_phone = ''.join(c for c in str(phone_str) if c.isdigit())

            # 验证手机号格式（中国手机号11位）
            if len(clean_phone) == 11 and clean_phone.startswith('1'):
                return int(clean_phone)
            else:
                self.logger.warning(f"无效的手机号格式: {phone_str} -> {clean_phone}")
                return None
        except (ValueError, TypeError) as e:
            self.logger.warning(f"电话号码解析失败: {phone_str} - {e}")
            return None

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