from langfuse import observe

from ..base import BaseAgent
from ...app.entities import WorkflowExecutionModel
from utils import get_current_datetime, get_processing_time_ms

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

                            用户输入: {user_input}

                            请提供合适的回复：
                            """

        self.logger.info(f"ChatAgent初始化完成: {self.agent_id}")

    @observe(name="chat-agent-conversation", as_type="span")
    async def process_conversation(self, state: WorkflowExecutionModel) -> dict:
        """
        处理对话状态 - LangGraph工作流节点

        遵循LangGraph最佳实践:
        - 接收Pydantic模型作为输入状态
        - 返回字典形式的状态更新
        - LangGraph自动处理状态合并

        参数:
            state: 当前工作流执行状态 (Pydantic模型)

        返回:
            dict: 包含需要更新的状态字段
        """
        start_time = get_current_datetime()

        try:
            self.logger.info(f"ChatAgent开始处理对话 - 租户: {state.tenant_id}")

            # 获取用户输入
            user_input = state.input

            # 准备聊天提示词
            formatted_prompt = self.chat_prompt.format(user_input=user_input)

            messages = [{
                "role": "user",
                "content": formatted_prompt
            }]

            # 调用LLM生成回复
            chat_response = await self.llm_call(
                messages=messages,
                model="gpt-4o-mini",
                provider="openai",
                temperature=0.7,
                max_tokens=500
            )

            # 计算处理时间
            processing_time = get_processing_time_ms(start_time)

            updated_value = {
                "agent_id": self.agent_id,
                "chat_response": chat_response,
                "processing_time_ms": processing_time,
                "timestamp": get_current_datetime().isoformat(),
                "status": "completed"
            }

            self.logger.info(f"ChatAgent处理完成，耗时: {processing_time:.2f}ms")
            self.logger.info(f"ChatAgent处理完成，返回值: {updated_value}")
            
            # 返回状态更新字典
            return {
                "output": chat_response,
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