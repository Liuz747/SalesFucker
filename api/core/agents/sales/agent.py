from uuid import UUID

from core.agents import BaseAgent
from core.entities import WorkflowExecutionModel
from core.prompts.template_loader import get_prompt_template
from core.tools import get_tools_schema, long_term_memory_tool, store_episodic_memory_tool
from infra.runtimes import CompletionsRequest
from libs.types import AccountStatus, Message, MessageParams
from libs.exceptions import AssistantInactiveException
from services import AssistantService, ThreadService
from utils import (
    get_chinese_time,
    get_component_logger,
    get_current_datetime,
    get_processing_time
)

logger = get_component_logger(__name__, "Sales Agent")


class SalesAgent(BaseAgent):
    """
    Sales Agent

    负责生成最终的销售话术回复。

    核心职责:
    - 接收 SentimentAgent 提供的策略提示词
    - 检索并整合记忆上下文
    - 获取并整合助理人设信息
    - 生成符合人设和策略的个性化回复
    - 自动管理助手回复的存储。
    """

    def __init__(self):
        super().__init__()
        self.agent_name = "sales_agent"

    async def process_conversation(self, state: WorkflowExecutionModel) -> dict:
        """
        处理对话状态，生成销售回复

        工作流程：
        1. 获取 SentimentAgent 确定的策略提示词
        2. 检索记忆上下文（长期+短期）
        3. 构建包含上下文的 LLM 提示词
        4. 生成回复
        5. 存储回复并更新状态

        Args:
            state: 当前工作流执行状态

        Returns:
            dict: 状态更新增量
        """
        start_time = get_current_datetime()

        try:
            logger.info("=== Sales Agent 开始处理 ===")

            await self.memory_manager.store_messages(
                state.tenant_id,
                state.thread_id,
                messages=state.input,
            )

            messages = await self.build_system_prompt(state)

            # 生成个性化回复（基于匹配的提示词 + 人设 + 记忆 + 时间 + 意向）
            sales_response, token_info = await self._generate_final_response(
                state.tenant_id,
                state.thread_id,
                state.workflow_id,
                messages,
                state.matched_prompt,
            )

            # 存储助手回复到记忆
            try:
                await self.memory_manager.save_assistant_message(
                    tenant_id=state.tenant_id,
                    thread_id=state.thread_id,
                    message=sales_response,
                )
                logger.debug("助手回复已保存到记忆")
            except Exception as e:
                logger.error(f"保存助手回复失败: {e}")

            # 更新状态 - 返回增量字典
            
            token_usage = {
                "input_tokens": token_info.get("input_tokens", 0),
                "output_tokens": token_info.get("output_tokens", 0),
                "total_tokens": token_info.get("total_tokens", 0)
            }

            agent_data = {
                "agent_id": self.agent_name,
                "agent_type": "chat",
                "sales_response": sales_response,
                "response": sales_response,
                "token_usage": token_usage,
                "timestamp": get_current_datetime(),
                "response_length": len(sales_response)
            }

            processing_time = get_processing_time(start_time)
            logger.info(f"最终回复生成完成: 耗时{processing_time:.2f}s, 长度={len(sales_response)}, tokens={token_info.get('total_tokens', 0)}")
            logger.info("=== Sales Agent 处理完成 ===")

            return {
                "output": sales_response,
                "input_tokens": token_usage["input_tokens"],
                "output_tokens": token_usage["output_tokens"],
                "total_tokens": state.total_tokens + token_usage["total_tokens"],
                "values": {"agent_responses": {self.agent_name: agent_data}}
            }

        except Exception as e:
            logger.error(f"Sales Agent处理失败: {e}", exc_info=True)
            raise e

    async def _generate_final_response(
        self,
        tenant_id: str,
        thread_id: UUID,
        run_id: UUID,
        messages: MessageParams,
        matched_prompt: dict
    ) -> tuple[str, dict]:
        """
        基于匹配提示词、人设信息、意向分析、记忆和时间生成回复（支持工具调用）

        Args:
            tenant_id: 租户ID
            thread_id: 线程ID
            run_id: 工作流执行ID
            messages: 消息列表
            matched_prompt: SentimentAgent 匹配的提示词

        Returns:
            tuple: (回复内容, token信息)
        """
        try:
            # 4. 创建 LLM 请求
            request = CompletionsRequest(
                id=run_id,
                provider="openrouter",
                model="anthropic/claude-haiku-4.5",
                temperature=0.6,
                messages=messages,
                tools=get_tools_schema([long_term_memory_tool, store_episodic_memory_tool]),
                tool_choice="auto"
            )

            # 5. 【关键】使用 invoke_llm 支持工具调用
            llm_response = await self.invoke_llm(
                request=request,
                tenant_id=tenant_id,
                thread_id=thread_id
            )

            # 6. 提取 token 信息
            token_info = self._extract_token_info(llm_response)

            # 7. 返回响应
            if llm_response.content:
                response_content = str(llm_response.content).strip()
                logger.debug(f"LLM 回复预览: {response_content[:100]}...")
                return response_content, token_info
            else:
                return self._get_fallback_response(matched_prompt), {}

        except Exception as e:
            logger.error(f"回复生成失败: {e}")
            return self._get_fallback_response(matched_prompt), {"tokens_used": 0, "error": str(e)}

    async def build_system_prompt(self, state: WorkflowExecutionModel) -> MessageParams:
        """
        构建系统提示词

        Args:
            state: 当前工作流执行状态

        Returns:
            MessageParams: 消息列表
        """
        base_system_prompt = state.matched_prompt.get("system_prompt", "你是一个人。")
        tone = state.matched_prompt.get("tone", "专业、友好")
        strategy = state.matched_prompt.get("strategy", "标准服务")
        appointment_intent = state.intent_analysis.get("appointment_intent")
        audio_output_intent = state.intent_analysis.get("audio_output_intent")
        role_prompt_content = None
        thread_context_content = None

        try:
            # 获取助理信息
            assistant = await AssistantService.get_assistant_by_id(state.assistant_id, use_cache=True)
            if assistant.status != AccountStatus.ACTIVE:
                raise AssistantInactiveException(state.assistant_id, assistant.status)

            name_display = assistant.nickname or assistant.assistant_name
            profile_lines = None

            if assistant.profile:
                profile_lines = [
                    f"- {key.replace('_', ' ').title()}: {value}"
                    for key, value in assistant.profile.items()
                    if value is not None and value != ""
                ]

            # 使用模板加载器生成角色提示词
            role_prompt_content = get_prompt_template(
                template_name="role_prompt",
                name_display=name_display,
                occupation=assistant.occupation,
                personality=assistant.personality,
                industry=assistant.industry,
                sex=assistant.sex,
                address=assistant.address,
                profile_lines=profile_lines,
                custom_instructions=None
            )
            logger.info(f"已获取助理人设信息: {role_prompt_content[:100] if role_prompt_content else 'None'}...")

            # 获取客户线程信息
            thread = await ThreadService.get_thread(state.thread_id)
            if thread:
                thread_context_content = get_prompt_template(
                    template_name="thread_context_prompt",
                    name=thread.name,
                    nickname=thread.nickname,
                    real_name=thread.real_name,
                    sex=thread.sex.value if thread.sex else None,
                    age=thread.age,
                    occupation=thread.occupation,
                    phone=thread.phone,
                    services=thread.services,
                    is_converted=thread.is_converted,
                    custom_context=None
                )
                logger.info(f"已获取客户线程信息")
        except Exception as e:
            logger.warning(f"获取助理或客户信息失败: {e}")

        user_text = self._input_to_text(state.input)
        short_term_messages, long_term_memories = await self.memory_manager.retrieve_context(
            tenant_id=state.tenant_id,
            thread_id=state.thread_id,
            query_text=user_text,
        )

        system_prompt = get_prompt_template(
            template_name="sales",
            template_file="agent_prompt.yaml",
            base_prompt=base_system_prompt,
            tone=tone,
            strategy=strategy,
            role_prompt=role_prompt_content,
            thread_context=thread_context_content,
            appointment_intent=appointment_intent,
            audio_output_intent=audio_output_intent,
            summaries=long_term_memories,
            current_time=get_chinese_time()
        )

        return [
            Message(role="system", content=system_prompt),
            *short_term_messages
        ]

    @staticmethod
    def _extract_token_info(llm_response) -> dict:
        """提取 token 使用信息"""
        try:
            input_tokens = llm_response.usage.input_tokens
            output_tokens = llm_response.usage.output_tokens
            total_tokens = input_tokens + output_tokens
            
            return {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens
            }
        except Exception as e:
            logger.warning(f"Token 信息提取失败: {e}")

        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    @staticmethod
    def _get_fallback_response(matched_prompt: dict) -> str:
        """获取兜底回复"""
        tone = matched_prompt.get("tone", "专业、友好")

        if "温和" in tone or "关怀" in tone:
            return "我理解您的感受"
        elif "积极" in tone or "热情" in tone:
            return "太好了！"
        else:
            return "感谢您的咨询。"
