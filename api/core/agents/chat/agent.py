from typing import Sequence

from langfuse import observe

from core.entities import WorkflowExecutionModel
from core.memory import StorageManager
from infra.runtimes import CompletionsRequest
from libs.types import Message
from utils import get_current_datetime, get_processing_time_ms
from ..base import BaseAgent

class ChatAgent(BaseAgent):
    """
    聊天机器人智能体

    提供基础的对话功能，处理用户输入并生成友好的回复。
    专为快速响应和良好用户体验设计。
    """

    def __init__(self):
        super().__init__()

        self.agent_id = "chat_agent"

        # 简单聊天提示词模板
        self.chat_prompt =  """
                            你是一个友好、专业的AI助手。请根据用户的输入提供有帮助的回复。

                            特点：
                            - 保持友好和专业的语调
                            - 提供准确、有用的信息
                            - 如果不确定，诚实地说明
                            - 回复要简洁明了
                            """
        self.memory_manager = StorageManager()
        self.logger.info(f"ChatAgent初始化完成: {self.agent_id}")

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
                messages=[Message(role="user", content=state.input)],
            )

            # 准备聊天提示词
            user_text = self._input_to_text(state.input)

            short_term_messages, long_term_memories = await self.memory_manager.retrieve_context(
                tenant_id=state.tenant_id,
                thread_id=state.thread_id,
                query_text=user_text,
            )

            system_prompt = self._build_system_prompt(self.chat_prompt, long_term_memories)
            llm_messages = [Message(role="system", content=system_prompt)]
            llm_messages.extend(short_term_messages)

            request = CompletionsRequest(
                id=state.workflow_id,
                provider="openrouter",
                model="openai/gpt-5-mini",
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

            # 计算处理时间
            processing_time = get_processing_time_ms(start_time)

            updated_value = {
                "agent_id": self.agent_id,
                "chat_response": chat_response.content,
                "processing_time_ms": processing_time,
                "timestamp": get_current_datetime().isoformat(),
                "status": "completed"
            }

            self.logger.info(f"ChatAgent处理完成，耗时: {processing_time:.2f}ms")
            self.logger.info(f"ChatAgent处理完成，返回值: {updated_value}")
            
            # 返回状态更新字典
            return {
                "output": chat_response.content,
                "finished_at": get_current_datetime(),
                "values": updated_value
            }

        except Exception as e:
            self.logger.error(f"ChatAgent处理失败: {e}", exc_info=True)

            # 创建错误状态的values字典 (替换现有values)
            error_values = {
                "agent_id": self.agent_id,
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

    def _input_to_text(self, content) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, Sequence):
            parts: list[str] = []
            for node in content:
                value = getattr(node, "content", None)
                parts.append(value if isinstance(value, str) else str(node))
            return "\n".join(parts)
        return str(content)

    def _build_system_prompt(self, base_prompt: str, summaries: list[dict]) -> str:
        if not summaries:
            return base_prompt

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

        return f"{base_prompt}\n\n以下长期记忆可帮助回答用户问题：\n" + "\n".join(lines)
