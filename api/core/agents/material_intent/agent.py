"""
Material Intent Analysis Agent - 素材发送意向分析智能体

专注于分析客户的素材发送意向，基于历史对话内容判断用户是否需要产品图片、价格信息、技术参数等素材。

核心职责:
- 基于近3轮对话分析素材需求意向
- 多类型素材需求识别（图片、价格、技术参数等）
- 紧急程度和优先级判断
- 为sales agent提供对应素材提示词，以衔接回复
"""

from langfuse import observe

from core.entities import WorkflowExecutionModel
from core.memory import StorageManager
from utils import get_current_datetime
from ..base import BaseAgent
from .intent_analyzer import MaterialIntentAnalyzer


class MaterialIntentAgent(BaseAgent):
    """
    素材发送意向分析智能体

    基于用户近3轮对话内容，智能分析用户是否需要各种类型的素材。
    支持产品图片、价格信息、技术参数等多种素材类型的识别。

    设计特点：
    - 多类型素材识别：全面覆盖各种素材需求
    - 优先级评估：判断素材需求的紧急程度
    - 精准匹配：识别具体的素材类型要求
    - 记忆集成：利用系统记忆进行上下文分析
    """

    def __init__(self):
        super().__init__()

        self.memory_manager = StorageManager()

        # 初始化意向分析器
        self.intent_analyzer = MaterialIntentAnalyzer(
            llm_provider="openrouter",
            llm_model="openai/gpt-4o-mini",
            invoke_llm_fn=self.invoke_llm
        )

    @observe(name="material-intent-analysis", as_type="generation")
    async def process_conversation(self, state: WorkflowExecutionModel) -> dict:
        """
        处理对话状态中的素材发送意向分析

        工作流程：
        1. 检索记忆上下文（近3轮对话）
        2. 分析各种类型的素材需求意向
        3. 判断紧急程度和优先级
        4. 生成素材需求报告
        5. 更新状态传递给sales agent

        参数:
            state: 当前对话状态，包含 customer_input, tenant_id, thread_id

        返回:
            dict: 更新后的对话状态，包含 material_intent 信息
        """
        start_time = get_current_datetime()

        try:
            self.logger.info("=== Material Intent Agent ===")

            self.logger.debug(f"分析素材意向 - 输入: {str(state.input)[:100]}...")

            # 步骤1: 检索记忆上下文（近3轮对话）
            user_text = self._input_to_text(state.input)
            short_term_messages, _ = await self.memory_manager.retrieve_context(
                tenant_id=state.tenant_id,
                thread_id=state.thread_id,
                query_text=user_text,
            )

            # 提取近3轮用户消息用于分析
            recent_user_messages = self._extract_recent_user_messages(
                short_term_messages, max_rounds=3
            )

            self.logger.info(f"记忆检索完成 - 分析轮次: {len(recent_user_messages)}")

            # 步骤2: 执行素材意向分析
            intent_result = await self._analyze_material_intent(
                current_input=user_text,
                recent_messages=recent_user_messages,
                tenant_id=state.tenant_id,
                thread_id=str(state.thread_id)
            )

            self.logger.info(f"素材意向分析结果 - 紧急程度: {intent_result.get('urgency_level', 'low')}, "
                           f"素材类型数: {len(intent_result.get('material_types', []))}, "
                           f"tokens_used: {intent_result.get('total_tokens', 0)}")

            # 步骤3: 更新对话状态
            updated_state = self._update_state_with_intent(
                state, intent_result, recent_user_messages
            )

            processing_time = (get_current_datetime() - start_time).total_seconds()
            self.logger.info(f"素材意向分析完成: 耗时{processing_time:.2f}s, "
                           f"紧急程度={intent_result.get('urgency_level', 'low')}")
            self.logger.info("=== Material Intent Agent 处理完成 ===")

            return updated_state

        except Exception as e:
            self.logger.error(f"素材意向分析失败: {e}", exc_info=True)
            self.logger.error(f"失败时的输入: {state.input}")
            # 降级处理：返回无需求状态
            # return self._create_fallback_state(state)

    def _extract_recent_user_messages(self, messages: list, max_rounds: int = 3) -> list[str]:
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

    async def _analyze_material_intent(self, current_input: str, recent_messages: list[str], tenant_id: str, thread_id: str) -> dict:
        """
        分析素材发送意向

        Args:
            current_input: 当前用户输入
            recent_messages: 最近用户消息列表
            tenant_id: 租户ID
            thread_id: 线程ID

        Returns:
            dict: 意向分析结果
        """
        try:
            # 构建分析上下文
            analysis_context = {
                "current_input": current_input,
                "recent_messages": recent_messages,
                "message_count": len(recent_messages),
                "analysis_type": "material_intent",
                "conversation_stage": "multi_round_analysis"
            }

            # 调用意向分析器 - 传递必需的参数
            result = await self.intent_analyzer.analyze_intent(analysis_context, tenant_id, thread_id)

            # 添加分析元数据
            result["analysis_metadata"] = {
                "analyzed_messages": len(recent_messages),
                "analysis_timestamp": get_current_datetime().isoformat(),
                "input_length": len(current_input),
                "analysis_type": "material_intent"
            }

            return result

        except Exception as e:
            self.logger.error(f"素材意向分析失败: {e}")
            # 返回默认的无需求结果
            return {
                "urgency_level": "bad",
                "material_types": [],
                "priority_score": 0.0,
                "confidence": 0.0,
                "specific_requests": [],
                "recommendation": "no_material",
                "tokens_used": 0,
                "analysis_metadata": {
                    "error": str(e),
                    "fallback": True
                }
            }

    def _update_state_with_intent(self, state: dict, intent_result: dict, recent_messages: list[str]) -> dict:
        """
        更新状态，添加素材意向信息

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

        # 核心传递字段：material_intent
        material_intent = {
            "urgency_level": intent_result.get("urgency_level", "low"),      # "high", "medium", "low"
            "material_types": intent_result.get("material_types", []),       # 素材类型列表
            "priority_score": intent_result.get("priority_score", 0.0),      # 0.0-1.0 优先级评分
            "confidence": intent_result.get("confidence", 0.0),              # 0.0-1.0 置信度
            "specific_requests": intent_result.get("specific_requests", []), # 具体素材需求
            "recommendation": intent_result.get("recommendation", "no_material"),  # "send_immediately", "send_soon", "no_material"
            "analyzed_message_count": len(recent_messages),
            "analysis_timestamp": current_time.isoformat()
        }

        # 构建 agent_data
        agent_data = {
            "agent_type": "material_intent",
            "material_intent": material_intent,
            "intent_result": intent_result,
            "analyzed_messages": recent_messages,
            "timestamp": current_time,
            "token_usage": token_info,
            "tokens_used": token_info["total_tokens"],
            "response_length": len(str(intent_result))
        }

        self.logger.info(f"material intent 字段已添加: urgency={material_intent['urgency_level']}, "
                        f"types={len(material_intent['material_types'])}")

        # 返回增量更新字典，让 LangGraph 的 Reducer 正确合并状态
        # 这样 input_tokens 和 output_tokens 才能正确累加（使用 operator.add）
        return {
            "material_intent": material_intent,
            "input_tokens": token_info["input_tokens"],
            "output_tokens": token_info["output_tokens"],
            "values": {"agent_responses": {self.agent_id: agent_data}},
            "active_agents": [self.agent_id]
        }
