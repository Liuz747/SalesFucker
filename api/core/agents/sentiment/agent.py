"""
Sentiment Analysis Agent - 简化协调版

专注于协调各个专业组件，提供清晰的情感分析服务。
Agent 本身只负责流程控制和状态管理，具体业务逻辑委托给专门组件。

核心职责:
- 组件协调和流程控制
- 状态管理和错误处理
- 组件生命周期管理
- 对外接口统一
"""

from typing import Dict, Any, Sequence
from langfuse import observe

from ..base import BaseAgent
from .multimodal_input_processor import MultimodalInputProcessor
from .sentiment_analyzer import SentimentAnalyzer
from .sales_prompt_generator import SalesPromptGenerator
from .prompt_matcher import PromptMatcher
from utils import get_current_datetime
from config import mas_config
from core.memory import StorageManager
from libs.types import Message


class SentimentAnalysisAgent(BaseAgent):
    """
    情感分析智能体 - 简化协调版

    作为多模态情感分析的主入口，协调：
    - 多模态输入处理
    - 情感分析
    - 销售提示词生成

    设计原则：
    - 单一职责：只负责协调，不处理具体业务逻辑
    - 依赖注入：组件可替换，便于测试
    - 错误隔离：组件失败不影响整体流程
    - 状态清晰：明确的状态管理和更新
    - 记忆服务：智能体内部自主管理
    """

    def __init__(self):
        super().__init__()
        self.llm_provider = mas_config.DEFAULT_LLM_PROVIDER

        # 使用OpenRouter中可用的模型
        self.llm_model = "openai/gpt-5-chat"

        # 记忆管理
        self.memory_manager = StorageManager()
        self.prompt_matcher = PromptMatcher()

        # 初始化核心组件
        self.input_processor = MultimodalInputProcessor(
            tenant_id=getattr(self, 'tenant_id', None),
            config={
                "openai_api_key": getattr(self, '_get_openai_api_key', lambda: None)()
            }
        )

        self.sentiment_analyzer = SentimentAnalyzer(
            llm_provider=self.llm_provider,
            llm_model=self.llm_model,
            invoke_llm_fn=self.invoke_llm
        )

        self.prompt_generator = SalesPromptGenerator()

    @observe(name="sentiment-analysis", as_type="generation")
    async def process_conversation(self, state: dict) -> dict:
        """
        处理对话状态中的情感分析（增强版：集成记忆和智能提示词匹配）

        工作流程：
        1. 存储用户输入到记忆
        2. 检索记忆上下文
        3. 多模态输入处理
        4. 情感分析
        5. 旅程阶段判断（写死规则）
        6. 提示词智能匹配
        7. 状态更新

        参数:
            state: 当前对话状态，包含 customer_input, tenant_id, thread_id

        返回:
            dict: 更新后的对话状态，包含 matched_prompt 和 memory_context
        """
        start_time = get_current_datetime()

        try:
            self.logger.info("=== Sentiment Agent ===")

            customer_input = state.get("customer_input", "")
            tenant_id = state.get("tenant_id")
            thread_id = state.get("thread_id")

            self.logger.debug(f"customer_input内容: {str(customer_input)[:100]}...")

            # 步骤1: 存储用户输入到记忆
            await self.memory_manager.store_messages(
                tenant_id=tenant_id,
                thread_id=thread_id,
                messages=[Message(role="user", content=customer_input)],
            )
            
            # 步骤2: 检索记忆上下文
            user_text = self._input_to_text(customer_input)
            short_term_messages, long_term_memories = await self.memory_manager.retrieve_context(
                tenant_id=tenant_id,
                thread_id=thread_id,
                query_text=user_text,
            )
            
            memory_context = {
                "short_term": short_term_messages,
                "long_term": long_term_memories
            }
            
            self.logger.info(f"记忆检索完成 - 短期消息数: {len(memory_context['short_term'])}, 长期摘要数: {len(memory_context['long_term'])}")

            # 步骤3: 处理多模态输入
            processed_text, multimodal_context = await self._process_input(customer_input)
            self.logger.info(f"多模态输入处理完成 - processed_text长度: {len(processed_text)}, context类型: {multimodal_context.get('type')}")

            # 步骤4: 执行情感分析（使用短期消息历史+当前输入）
            sentiment_result = await self._analyze_sentiment_with_history(processed_text, multimodal_context, memory_context['short_term'])
            self.logger.info(f"情感分析结果 - sentiment: {sentiment_result.get('sentiment')}, score: {sentiment_result.get('score')}, urgency: {sentiment_result.get('urgency')}")
            self.logger.info(f"情感分析token统计 - tokens_used: {sentiment_result.get('tokens_used', 0)}")
            self.logger.info(f"情感分析上下文 - 使用历史消息数: {len(memory_context['short_term'])}")

            # 步骤5: 判断客户旅程阶段 按轮次的规则-待修改
            journey_stage = self._determine_journey_stage(memory_context['short_term'])
            self.logger.info(f"旅程阶段判断: {journey_stage} (基于对话轮次: {len(memory_context['short_term'])})")

            # 步骤6: 智能匹配提示词
            matched_prompt = self._match_prompt(sentiment_result.get('score', 0.5), journey_stage)
            self.logger.info(f"提示词匹配完成 - matched_key: {matched_prompt['matched_key']}, tone: {matched_prompt['tone']}")
            self.logger.debug(f"matched_prompt内容: {matched_prompt['system_prompt'][:150]}..." if len(matched_prompt['system_prompt']) > 150 else f"matched_prompt内容: {matched_prompt['system_prompt']}")

            # 步骤7: 更新对话状态
            updated_state = self._update_state_enhanced(
                state, processed_text, sentiment_result, matched_prompt,
                multimodal_context, memory_context, journey_stage
            )

            processing_time = (get_current_datetime() - start_time).total_seconds()
            self.logger.info(f"情感分析完成（增强版）: 耗时{processing_time:.2f}s, 情感={sentiment_result.get('sentiment')}, 旅程={journey_stage}")
            self.logger.info("=== Sentiment Agent 处理完成（增强版） ===")

            return updated_state

        except Exception as e:
            self.logger.error(f"情感分析处理失败: {e}", exc_info=True)
            self.logger.error(f"失败时的输入: {state.get('customer_input', 'None')}")
            raise e

    def _input_to_text(self, content) -> str:
        """将输入转换为文本（参考ChatAgent）"""
        if isinstance(content, str):
            return content
        if isinstance(content, Sequence):
            parts: list[str] = []
            for node in content:
                value = getattr(node, "content", None)
                parts.append(value if isinstance(value, str) else str(node))
            return "\n".join(parts)
        return str(content)

    def _determine_journey_stage(self, short_term_messages: list) -> str:
        """
        新增：判断客户旅程阶段（写死规则，简单可靠）

        Args:
            short_term_messages: 短期记忆消息列表

        Returns:
            str: "awareness" | "consideration" | "decision"
        """
        try:
            # 计算对话轮次（只算用户消息）
            user_message_count = sum(
                1 for msg in short_term_messages
                if isinstance(msg, dict) and msg.get("role") == "user"
            )
            # 兼容Message对象
            if user_message_count == 0:
                 user_message_count = sum(
                    1 for msg in short_term_messages
                    if hasattr(msg, "role") and msg.role == "user"
                )

            # 写死的简单规则
            if user_message_count <= 2:
                return "awareness"      # 前1-2轮：认知阶段
            elif user_message_count <= 5:
                return "consideration"  # 第3-5轮：考虑阶段
            else:
                return "decision"       # 第6轮+：决策阶段

        except Exception as e:
            self.logger.error(f"旅程阶段判断失败: {e}")
            return "awareness"  # 默认返回认知阶段

    def _match_prompt(self, sentiment_score: float, journey_stage: str) -> dict:
        """
        新增：智能匹配提示词

        Args:
            sentiment_score: 情感分数 0.0-1.0
            journey_stage: 旅程阶段

        Returns:
            dict: 匹配的提示词配置
        """
        try:
            # 调用 PromptMatcher 查表
            matched_prompt = self.prompt_matcher.get_prompt(
                sentiment_score=sentiment_score,
                journey_stage=journey_stage
            )

            self.logger.debug(f"提示词匹配成功 - key: {matched_prompt.get('matched_key')}")
            return matched_prompt

        except Exception as e:
            self.logger.error(f"提示词匹配失败: {e}")

    def _update_state_enhanced(
        self, state: dict, processed_text: str, sentiment_result: dict,
        matched_prompt: dict, multimodal_context: dict, memory_context: dict,
        journey_stage: str
    ) -> dict:
        """
        🔥 新增：增强版状态更新（添加 matched_prompt 和 memory_context）

        Args:
            state: 原始状态
            processed_text: 处理后的文本
            sentiment_result: 情感分析结果
            matched_prompt: 匹配的提示词
            multimodal_context: 多模态上下文
            memory_context: 记忆上下文
            journey_stage: 旅程阶段

        Returns:
            dict: 更新后的状态
        """
        # 提取token信息
        sentiment_tokens = {
            "tokens_used": sentiment_result.get("tokens_used", 0),
            "total_tokens": sentiment_result.get("total_tokens", 0)
        }

        # 🔥 增强版：根级别状态（LangGraph节点间传递）
        state["processed_text"] = processed_text
        state["matched_prompt"] = matched_prompt  # 🆕 SalesAgent 将使用这个
        state["memory_context"] = memory_context  # 🆕 记忆上下文
        state["journey_stage"] = journey_stage    # 🆕 旅程阶段

        # 保留原有的 sentiment_analysis
        state["sentiment_analysis"] = {
            **sentiment_result,
            "journey_stage": journey_stage,        # 🆕 添加旅程信息
            "processed_input": processed_text,
            "multimodal_context": multimodal_context,
            "agent_id": self.agent_id,
            **sentiment_tokens
        }

        # 备份存储在 values 结构中（用于统计和调试）
        if state.get("values") is None:
            state["values"] = {}
        if state["values"].get("agent_responses") is None:
            state["values"]["agent_responses"] = {}

        agent_data = {
            "sentiment_analysis": sentiment_result,
            "matched_prompt": matched_prompt,      # 🆕
            "memory_context": memory_context,      # 🆕
            "journey_stage": journey_stage,        # 🆕
            "processed_input": processed_text,
            "timestamp": get_current_datetime(),
            **sentiment_tokens
        }

        state["values"]["agent_responses"][self.agent_id] = agent_data

        # 更新活跃智能体列表
        state.setdefault("active_agents", []).append(self.agent_id)

        self.logger.info(f"增强版状态管理完成 - 新增字段: matched_prompt, memory_context, journey_stage")
        self.logger.info(f"状态传递完成 -> SalesAgent 可访问: state['matched_prompt'], state['memory_context']")

        return state

    async def _process_input(self, customer_input) -> tuple[str, dict]:
        """处理多模态输入"""
        try:
            return await self.input_processor.process_input(customer_input)
        except Exception as e:
            self.logger.error(f"输入处理失败: {e}")
            # 降级处理：将输入转为字符串
            return str(customer_input) if customer_input else "", {"type": "fallback", "error": str(e)}

    async def _analyze_sentiment(self, text: str, context: dict) -> dict:
        """分析情感"""
        result = await self.sentiment_analyzer.analyze_sentiment(text, context)
        self.logger.info(f"情感分析器返回结果 - sentiment: {result.get('sentiment')}, 情感分析消耗tokens: {result.get('total_tokens', 0)}")
        return result

    async def _analyze_sentiment_with_history(self, current_text: str, context: dict, short_term_msgs: list) -> dict:
        """
        使用历史消息+当前输入进行情感分析

        Args:
            current_text: 当前处理的文本
            context: 多模态上下文
            short_term_msgs: 短期历史消息列表

        Returns:
            dict: 情感分析结果
        """
        try:
            # 获取最近5条用户消息（如果有的话）
            # 注意：short_term_msgs 可能包含 dict 或 Message 对象
            recent_user_messages = []
            for msg in reversed(short_term_msgs):
                if len(recent_user_messages) >= 5:
                    break
                
                role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", None)
                content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
                
                if role == "user" and content and str(content).strip():
                    recent_user_messages.insert(0, str(content))

            # 构建合并的文本用于分析
            if recent_user_messages:
                # 创建历史对话上下文
                history_context = "\n".join([f"用户消息{i+1}: {msg}" for i, msg in enumerate(recent_user_messages)])
                combined_text = f"""最近对话历史：
{history_context}

当前用户输入：
{current_text}"""

                self.logger.info(f"使用历史消息进行情感分析 - 历史消息数: {len(recent_user_messages)}, 合并后文本长度: {len(combined_text)}")

                # 增强上下文信息，标明这是历史上下文分析
                enhanced_context = {
                    **context,
                    "analysis_type": "with_history",
                    "history_message_count": len(recent_user_messages),
                    "conversation_flow": "sequential"
                }

                # 调用原有的情感分析方法
                result = await self.sentiment_analyzer.analyze_sentiment(combined_text, enhanced_context)

                # 添加上下文信息到结果中
                result["analysis_context"] = {
                    "used_history": True,
                    "history_message_count": len(recent_user_messages),
                    "combined_text_length": len(combined_text),
                    "current_text_length": len(current_text)
                }

                self.logger.info(f"基于历史的情感分析完成 - sentiment: {result.get('sentiment')}, 使用历史消息: {len(recent_user_messages)}条")
                return result
            else:
                # 没有历史消息，使用当前文本分析
                self.logger.info("未找到历史用户消息，使用当前文本进行情感分析")
                result = await self.sentiment_analyzer.analyze_sentiment(current_text, context)

                result["analysis_context"] = {
                    "used_history": False,
                    "history_message_count": 0,
                    "combined_text_length": len(current_text),
                    "current_text_length": len(current_text)
                }

                return result

        except Exception as e:
            self.logger.error(f"基于历史的情感分析失败: {e}")
            # 降级处理：只分析当前文本
            return await self.sentiment_analyzer.analyze_sentiment(current_text, context)

    async def _generate_prompt(self, sentiment_result: dict, context: dict) -> str:
        """生成销售提示词"""
        try:
            # 使用prompt_generator生成个性化提示词
            sales_prompt = self.prompt_generator.generate_prompt(sentiment_result, context)

            self.logger.info(f"成功生成sales_prompt，长度: {len(sales_prompt)}")
            return sales_prompt

        except Exception as e:
            self.logger.error(f"提示词生成失败: {e}")
