from langfuse import observe

from core.agents import BaseAgent
from infra.runtimes import CompletionsRequest
from libs.types import (
    InputContent,
    InputType,
    Message,
    MessageParams,
    OutputType
)
from models import WorkflowExecutionModel
from utils import get_current_datetime, get_processing_time_ms


class TestChatAgent(BaseAgent):
    """
    聊天机器人智能体

    提供基础的对话功能，处理用户输入并生成友好的回复。
    专为快速响应和良好用户体验设计。
    """

    def __init__(self):
        super().__init__()

        self.agent_name = "test_chat_agent"

        # 简单聊天提示词模板
        self.chat_prompt =  """
                            你是一个友好、专业的AI助手。请根据用户的输入提供有帮助的回复。

                            特点：
                            - 保持友好和专业的语调
                            - 提供准确、有用的信息
                            - 如果不确定，诚实地说明
                            - 回复要简洁明了
                            """
        self.logger.info("ChatAgent初始化完成")

    @observe(name="chat-agent-conversation", as_type="span")
    async def process_conversation(self, state: WorkflowExecutionModel) -> dict:
        """
        处理对话状态 - LangGraph工作流节点

        参数:
            state: 当前工作流执行状态 (Pydantic模型)

        返回:
            dict: 包含需要更新的状态字段
        """
        start_time = get_current_datetime()

        try:
            self.logger.info(f"ChatAgent开始处理对话 - 线程: {state.thread_id}")

            # 将当前用户输入写入短期记忆
            await self.memory_manager.store_messages(
                tenant_id=state.tenant_id,
                thread_id=state.thread_id,
                messages=state.input,
            )

            # 解析输入：提取文本和检测类型
            user_text, input_types = self._parse_input(state.input)
            has_audio_input = InputType.AUDIO in input_types

            short_term_messages, long_term_memories = await self.memory_manager.retrieve_context(
                tenant_id=state.tenant_id,
                thread_id=state.thread_id,
                query_text=user_text,
            )

            # 构建系统提示词（包含多模态信息）
            system_prompt = self._build_system_prompt(
                self.chat_prompt,
                long_term_memories,
                input_types
            )
            llm_messages = [Message(role="system", content=system_prompt)]
            llm_messages.extend(short_term_messages)

            request = CompletionsRequest(
                id=state.workflow_id,
                provider="openrouter",
                model="google/gemini-3-flash-preview",
                messages=llm_messages,
                thread_id=state.thread_id,
                temperature=1,
                max_tokens=1000
            )

            # 调用LLM生成回复
            chat_response = await self.invoke_llm(request)

            await self.memory_manager.save_assistant_message(
                tenant_id=state.tenant_id,
                thread_id=state.thread_id,
                message=chat_response.content,
            )

            # 提取 token 信息
            input_tokens = chat_response.usage.input_tokens
            output_tokens = chat_response.usage.output_tokens

            # 计算处理时间
            processing_time = get_processing_time_ms(start_time)

            updated_value = {
                "agent_name": self.agent_name,
                "chat_response": chat_response.content,
                "processing_time_ms": processing_time,
                "timestamp": get_current_datetime().isoformat(),
                "token_usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens
                },
                "status": "completed"
            }

            self.logger.info(f"ChatAgent处理完成，耗时: {processing_time:.2f}ms")
            self.logger.info(f"ChatAgent处理完成，返回值: {updated_value}")

            # 构建返回状态
            result = {
                "output": chat_response.content,
                "input_tokens": input_tokens + state.input_tokens,
                "output_tokens": output_tokens + state.output_tokens,
                "finished_at": get_current_datetime(),
                "values": updated_value
            }

            # 如果用户输入包含音频，自动请求TTS输出
            if has_audio_input:
                result["actions"] = [OutputType.AUDIO]
                self.logger.info("检测到音频输入，已请求TTS输出")

            return result

        except Exception as e:
            self.logger.error(f"ChatAgent处理失败: {e}", exc_info=True)

            # 创建错误状态的values字典 (替换现有values)
            error_values = {
                "agent_name": self.agent_name,
                "error": str(e),
                "timestamp": get_current_datetime().isoformat(),
                "status": "failed"
            }

            # 返回错误状态更新字典
            return {
                "error_message": "聊天服务处理失败，请稍后重试",
                "exception_count": state.exception_count + 1,
                "finished_at": get_current_datetime(),
                "values": error_values
            }

    def _parse_input(self, messages: MessageParams) -> tuple[str, set[InputType]]:
        """
        解析输入消息列表，提取文本内容和检测内容类型

        Args:
            messages: 消息列表 (MessageParams)

        Returns:
            tuple[str, set[InputType]]: (合并后的文本内容, 检测到的输入类型集合)
        """
        parts: list[str] = []
        types: set[InputType] = set()

        for message in messages:
            content = message.content
            if isinstance(content, str):
                parts.append(f"{message.role}: {content}")
                types.add(InputType.TEXT)
            else:
                for item in content:
                    if isinstance(item, InputContent):
                        parts.append(f"{message.role}: {item.content}")
                        types.add(item.type)

        return "\n".join(parts), types

    def _build_system_prompt(
        self,
        base_prompt: str,
        summaries: list[dict],
        input_types: set[InputType] | None = None
    ) -> str:
        """
        构建系统提示词

        Args:
            base_prompt: 基础提示词
            summaries: 长期记忆摘要列表
            input_types: 输入类型集合（用于多模态提示）

        Returns:
            str: 完整的系统提示词
        """
        prompt_parts = [base_prompt]

        # 添加多模态输入信息
        if input_types and len(input_types) > 1:
            type_names = {
                InputType.AUDIO: "音频",
                InputType.IMAGE: "图像",
                InputType.VIDEO: "视频",
                InputType.FILES: "文件"
            }
            detected = [type_names[t] for t in input_types if t in type_names]
            if detected:
                prompt_parts.append(f"\n注意：用户输入包含多模态内容：{', '.join(detected)}。")

        # 添加长期记忆
        if summaries:
            lines: list[str] = []
            for idx, summary in enumerate(summaries, 1):
                content = summary.get("content") or ""
                tags = summary.get("tags") or []
                tag_display = (
                    f" (标签: {', '.join(str(tag) for tag in tags)})"
                    if tags
                    else ""
                )
                lines.append(f"{idx}. {content}{tag_display}")

            prompt_parts.append("\n以下长期记忆可帮助回答用户问题：\n" + "\n".join(lines))

        return "".join(prompt_parts)
