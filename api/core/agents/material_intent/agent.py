"""
Material Intent Analysis Agent - 素材发送意向分析智能体

专注于分析客户的素材发送意向，基于历史对话内容判断用户是否需要产品图片、价格信息、技术参数等素材。

核心职责:
- 基于近3轮对话分析素材需求意向
- 多类型素材需求识别（图片、价格、技术参数等）
- 紧急程度和优先级判断
- 为sales agent提供素材发送洞察
- 智能记忆管理和检索
"""

from typing import Dict, Any, List
from langfuse import observe

from ..base import BaseAgent
from .intent_analyzer import MaterialIntentAnalyzer
from utils import get_current_datetime
from utils.token_manager import TokenManager
from config import mas_config
from core.memory import StorageManager
from libs.types import Message


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
        self.llm_provider = mas_config.DEFAULT_LLM_PROVIDER
        self.llm_model = "openai/gpt-4o-mini"  # 使用高效的模型进行意图分析

        self.memory_manager = StorageManager()

        # 初始化意向分析器
        self.intent_analyzer = MaterialIntentAnalyzer(
            llm_provider=self.llm_provider,
            llm_model=self.llm_model,
            invoke_llm_fn=self.invoke_llm
        )

    @observe(name="material-intent-analysis", as_type="generation")
    async def process_conversation(self, state: dict) -> dict:
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

            customer_input = state.get("customer_input", "")
            tenant_id = state.get("tenant_id")
            thread_id = state.get("thread_id")

            self.logger.debug(f"分析素材意向 - 输入: {str(customer_input)[:100]}...")

            # 步骤1: 检索记忆上下文（近3轮对话）
            user_text = self._input_to_text(customer_input)
            short_term_messages, long_term_memories = await self.memory_manager.retrieve_context(
                tenant_id=tenant_id,
                thread_id=thread_id,
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
                recent_messages=recent_user_messages
            )

            self.logger.info(f"素材意向分析结果 - 紧急程度: {intent_result.get('urgency_level', 'low')}, "
                           f"素材类型数: {len(intent_result.get('material_types', []))}, "
                           f"tokens_used: {intent_result.get('tokens_used', 0)}")

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
            self.logger.error(f"失败时的输入: {state.get('customer_input', 'None')}")
            # 降级处理：返回无需求状态
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

    def _extract_recent_user_messages(self, messages: List, max_rounds: int = 3) -> List[str]:
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

    async def _analyze_material_intent(self, current_input: str, recent_messages: List[str]) -> dict:
        """
        分析素材发送意向

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
                "analysis_type": "material_intent",
                "conversation_stage": "multi_round_analysis"
            }

            # 调用意向分析器
            result = await self.intent_analyzer.analyze_intent(analysis_context)

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
                "urgency_level": "low",
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

    def _update_state_with_intent(self, state: dict, intent_result: dict, recent_messages: List[str]) -> dict:
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

        # 创建标准化的Agent响应数据
        agent_response_data = TokenManager.extract_agent_token_info(
            agent_id=self.agent_id,
            agent_type="material_intent",
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

        # 状态更新 - 直接设置到model字段避免并发冲突
        state["material_intent"] = material_intent
        state["values"] = state.get("values", {})

        # 备份存储在 values 结构中
        if state.get("values") is None:
            state["values"] = {}
        if state["values"].get("agent_responses") is None:
            state["values"]["agent_responses"] = {}

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

        state["values"]["agent_responses"][self.agent_id] = agent_data

        # 更新活跃智能体列表
        state.setdefault("active_agents", []).append(self.agent_id)

        self.logger.info(f"material intent 字段已添加: urgency={material_intent['urgency_level']}, "
                        f"types={len(material_intent['material_types'])}")

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

        # 默认无需求状态
        material_intent = {
            "urgency_level": "low",
            "material_types": [],
            "priority_score": 0.0,
            "confidence": 0.0,
            "specific_requests": [],
            "recommendation": "no_material",
            "analyzed_message_count": 0,
            "analysis_timestamp": current_time.isoformat(),
            "fallback": True
        }

        state["material_intent"] = material_intent

        # 简化的values存储
        if state.get("values") is None:
            state["values"] = {}
        if state["values"].get("agent_responses") is None:
            state["values"]["agent_responses"] = {}

        state["values"]["agent_responses"][self.agent_id] = {
            "agent_type": "material_intent",
            "material_intent": material_intent,
            "timestamp": current_time,
            "fallback": True,
            "error": "processing_failed"
        }

        return state