"""
Sentiment Analysis Agent

负责对话过程中的情感分析、意图识别和流程控制。

核心职责:
- 多模态输入处理与标准化
- 基于历史上下文的情感分析
- 客户旅程阶段判定
- 销售策略提示词匹配
- 状态管理与记忆更新
"""

from typing import Sequence
from langfuse import observe

from ..base import BaseAgent
from .multimodal_input_processor import MultimodalInputProcessor
from .sentiment_analyzer import SentimentAnalyzer
from .sales_prompt_generator import SalesPromptGenerator
from .prompt_matcher import PromptMatcher
from utils import get_current_datetime
from config import mas_config
from core.memory import StorageManager
from libs.types import Message, InputContentParams
from libs.types.memory import MemoryType
from core.entities import WorkflowExecutionModel

class SentimentAnalysisAgent(BaseAgent):
    """
    情感分析智能体
    
    作为对话系统的核心协调组件，负责：
    1. 处理多模态输入（文本/图片）
    2. 分析用户情感与意图
    3. 确定客户旅程阶段
    4. 匹配最佳销售策略提示词
    
    该智能体维护对话状态，并为下游的 SalesAgent 准备必要的上下文信息。
    """

    def __init__(self):
        super().__init__()
        self.llm_provider = mas_config.DEFAULT_LLM_PROVIDER

        # 使用OpenRouter中可用的模型
        self.llm_model = "openai/gpt-5-mini"

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
    async def process_conversation(self, state: WorkflowExecutionModel) -> dict:
        """
        处理对话状态中的情感分析流程
        
        工作流程：
        1. 处理多模态输入并存储到记忆
        2. 检索相关记忆上下文
        3. 执行基于历史的情感分析
        4. 判定客户旅程阶段
        5. 匹配销售策略提示词
        6. 注入外部动态信息（如朋友圈互动）
        7. 更新对话状态
        
        Args:
            state: 当前工作流执行状态
            
        Returns:
            dict: 更新后的状态增量，包含 sentiment_analysis, matched_prompt 等
        """
        start_time = get_current_datetime()

        try:
            self.logger.info("=== Sentiment Agent ===")

            customer_input = state.get("input")
            tenant_id = state.get("tenant_id")
            thread_id = str(state.get("thread_id"))

            self.logger.debug(f"input内容: {str(customer_input)[:100]}...")

            # 步骤1: 处理多模态输入 (优先处理，将图片转为文字)
            processed_text, multimodal_context = await self._process_input(customer_input)
            self.logger.info(f"多模态输入处理完成 - 输入消息条数: {len(processed_text)}, context类型: {multimodal_context.get('type')}")

            # 步骤2: 存储用户输入到记忆 (存储处理后的文字描述，确保记忆包含图片语义)
            # 注意：这里我们将处理后的 processed_text 存入记忆，而不是原始的 customer_input
            # 这样后续检索时，图片内容就是可被搜索和理解的文本形式
            await self.memory_manager.store_messages(
                tenant_id=tenant_id,
                thread_id=thread_id,
                messages=[Message(role="user", content=processed_text)],
            )
            
            # 步骤3: 检索记忆上下文 (使用处理后的文本进行检索)
            short_term_messages, long_term_memories = await self.memory_manager.retrieve_context(
                tenant_id=tenant_id,
                thread_id=thread_id,
                query_text=processed_text,
            )
            
            memory_context = {
                "short_term": short_term_messages,
                "long_term": long_term_memories
            }
            
            self.logger.info(f"记忆检索完成 - 短期消息数: {len(memory_context['short_term'])}, 长期摘要数: {len(memory_context['long_term'])}")

            # 步骤4: 执行情感分析（结合短期消息历史）
            sentiment_result = await self._analyze_sentiment_with_history(processed_text, multimodal_context, memory_context['short_term'])
            self.logger.info(f"情感分析结果 - sentiment: {sentiment_result.get('sentiment')}, score: {sentiment_result.get('score')}, urgency: {sentiment_result.get('urgency')}")
            self.logger.info(f"情感分析token统计 - tokens_used: {sentiment_result.get('tokens_used', 0)}")
            self.logger.info(f"情感分析上下文 - 使用历史消息数: {len(memory_context['short_term'])}")

            # 步骤5: 判断客户旅程阶段
            journey_stage = self._determine_journey_stage(memory_context['short_term'])
            self.logger.info(f"旅程阶段判断: {journey_stage} (基于对话轮次: {len(memory_context['short_term'])})")

            # 步骤6: 智能匹配提示词
            matched_prompt = self._match_prompt(sentiment_result.get('score', 0.5), journey_stage)
            self.logger.info(f"提示词匹配完成 - matched_key: {matched_prompt['matched_key']}, tone: {matched_prompt['tone']}")
            self.logger.debug(f"matched_prompt内容: {matched_prompt['system_prompt'][:150]}..." if len(matched_prompt['system_prompt']) > 150 else f"matched_prompt内容: {matched_prompt['system_prompt']}")

            # 步骤6.5: 注入外部活动记忆 (如朋友圈互动)
            # 仅在情感积极（> 0.5）时注入，增强互动性
            sentiment_score = sentiment_result.get('score', 0.5)
            if sentiment_score > 0.5:
                try:
                    external_memories = await self.memory_manager.get_external_context(
                        tenant_id=tenant_id,
                        thread_id=thread_id,
                        query_text=processed_text,
                        limit=3, # 最近3条
                        memory_types=[MemoryType.MOMENTS_INTERACTION] # 未来可添加 MemoryType.OFFLINE_REPORT 等
                    )
                    
                    if external_memories:
                        self.logger.info(f"发现 {len(external_memories)} 条外部活动记忆，注入上下文")
                        
                        # 格式化外部记忆
                        memory_texts = []
                        for mem in external_memories:
                             # 简单处理时间
                            created_at = mem.get('created_at', '')[:10] 
                            content = mem.get('content', '')
                            memory_texts.append(f"- [{created_at}] {content}")
                        
                        external_context_str = "\n".join(memory_texts)
                        
                        # 注入到 matched_prompt 的 system_prompt 中
                        # SalesAgent 会直接使用这个 system_prompt
                        additional_prompt = f"\n【用户近期动态（可适当寒暄提及）】\n{external_context_str}\n"
                        matched_prompt["system_prompt"] += additional_prompt
                        
                except Exception as e:
                    self.logger.warning(f"获取外部记忆失败，跳过注入: {e}")


            # 步骤7: 更新对话状态 - 使用Reducer模式返回增量更新
            
            # 使用TokenManager创建标准化的Agent响应数据
            current_time = get_current_datetime()
            
            # 更新token信息，使用sentiment_result中的实际数据
            token_info = {
                "input_tokens": sentiment_result.get("input_tokens", 0),
                "output_tokens": sentiment_result.get("output_tokens", 0),
                "total_tokens": sentiment_result.get("total_tokens", sentiment_result.get("tokens_used", 0))
            }

            agent_data = {
                "agent_type": "sentiment",
                "sentiment_analysis": sentiment_result,
                "matched_prompt": matched_prompt,
                "journey_stage": journey_stage,
                "processed_input": processed_text,
                "timestamp": current_time,
                "token_usage": token_info,             # 标准化的token信息
                "tokens_used": token_info["total_tokens"],  # 向后兼容
                "response_length": len(str(sentiment_result))
            }
            
            # 构造 sentiment_analysis 更新对象
            sentiment_analysis_update = {
                **sentiment_result,
                "journey_stage": journey_stage,        #  添加旅程信息
                "processed_input": processed_text,
                "multimodal_context": multimodal_context,
                "agent_id": self.agent_id,
                "token_usage": token_info,             # 标准化的token信息
                "tokens_used": token_info["total_tokens"]  # 向后兼容
            }
            
            # 构造返回的增量状态
            return {
                "sentiment_analysis": sentiment_analysis_update,
                "matched_prompt": matched_prompt,
                "journey_stage": journey_stage,
                "values": {"agent_responses": {self.agent_id: agent_data}},
                "active_agents": [self.agent_id]
            }

            # self.logger.info(f"情感分析完成: 耗时{processing_time:.2f}s, 情感={sentiment_result.get('sentiment')}, 旅程={journey_stage}")
            # self.logger.info("=== Sentiment Agent 处理完成 ===")

        except Exception as e:
            self.logger.error(f"情感分析处理失败: {e}", exc_info=True)
            # 失败时的输入处理可能需要调整
            input_content = state.get("input") if isinstance(state, dict) else getattr(state, "input", "unknown")
            self.logger.error(f"失败时的输入: {str(input_content)[:100]}")
            raise e

    def _input_to_text(self, content) -> str:
        """将输入转换为文本"""
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
        判断客户旅程阶段
        
        基于对话轮次进行简单规则判断。

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

            # 简单的规则判定
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
        根据情感和旅程阶段匹配提示词

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
            return {
                "system_prompt": "你是一个专业友好的美容顾问。",
                "tone": "专业、友好",
                "strategy": "标准服务",
                "matched_key": "fallback",
                "sentiment_level": "medium",
                "journey_stage": journey_stage,
                "sentiment_score": sentiment_score
            }

    def _update_state_enhanced(
        self, state: dict, processed_text: str, sentiment_result: dict,
        matched_prompt: dict, multimodal_context: dict, memory_context: dict,
        journey_stage: str
    ) -> dict:
        """
        构建更新后的状态对象

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
        # 使用TokenManager创建标准化的Agent响应数据
        current_time = get_current_datetime()
        
        # 更新token信息，使用sentiment_result中的实际数据
        token_info = {
            "input_tokens": sentiment_result.get("input_tokens", 0),
            "output_tokens": sentiment_result.get("output_tokens", 0),
            "total_tokens": sentiment_result.get("total_tokens", sentiment_result.get("tokens_used", 0))
        }
        
        # 构建标准化的Agent响应数据 (原TokenManager逻辑)
        agent_response_data = {
            "agent_id": self.agent_id,
            "agent_type": "sentiment",
            "response": str(sentiment_result),
            "token_usage": token_info,
            "tokens_used": token_info["total_tokens"],
            "response_length": len(str(sentiment_result)),
            "timestamp": current_time
        }

        # LangGraph节点间传递 - 直接设置到model字段避免并发冲突
        state["processed_text"] = processed_text
        state["matched_prompt"] = matched_prompt  # SalesAgent 将使用matched_prompt 作为优化输入
        state["journey_stage"] = journey_stage    # 旅程阶段
        state["values"] = state.get("values", {})

        # 保留原有的 sentiment_analysis，添加标准化token信息
        state["sentiment_analysis"] = {
            **sentiment_result,
            "journey_stage": journey_stage,        #  添加旅程信息
            "processed_input": processed_text,
            "multimodal_context": multimodal_context,
            "agent_id": self.agent_id,
            "token_usage": token_info,             # 标准化的token信息
            "tokens_used": token_info["total_tokens"]  # 向后兼容
        }

        # 备份存储在 values 结构中（用于统计和调试）
        if state.get("values") is None:
            state["values"] = {}
        if state["values"].get("agent_responses") is None:
            state["values"]["agent_responses"] = {}

        agent_data = {
            "agent_type": "sentiment",
            "sentiment_analysis": sentiment_result,
            "matched_prompt": matched_prompt,
            "journey_stage": journey_stage,
            "processed_input": processed_text,
            "timestamp": current_time,
            "token_usage": token_info,             # 标准化的token信息
            "tokens_used": token_info["total_tokens"],  # 向后兼容
            "response_length": len(str(sentiment_result))
        }

        state["values"]["agent_responses"][self.agent_id] = agent_data

        # 更新活跃智能体列表
        active_agents = state.get("active_agents")
        if active_agents is None:
            active_agents = []
        active_agents.append(self.agent_id)
        state["active_agents"] = active_agents

        self.logger.info(f"sentiment agent 新增字段: matched_prompt, journey_stage")

        return state

    async def _process_input(self, customer_input: InputContentParams) -> tuple[str, dict]:
        """处理多模态输入"""
        try:
            # 简单的适配逻辑
            input_data = customer_input
            return await self.input_processor.process_input(input_data)
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
