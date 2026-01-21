"""
智能体基础类模块

该模块定义了所有智能体的抽象基类，提供智能体的基础功能和接口规范。
所有具体的智能体实现都应该继承此基类。

核心功能:
- 智能体生命周期管理
- 消息处理抽象接口
- 错误处理和降级机制
- 智能体状态管理
- 工具调用支持
"""

from abc import ABC, abstractmethod
import json
from uuid import UUID

from core.memory import StorageManager
from core.tools import get_handler
from infra.runtimes import LLMClient, CompletionsRequest, LLMResponse, TokenUsage
from libs.types import MessageParams, InputContent, AssistantMessage, ToolMessage
from models import WorkflowExecutionModel
from utils import get_component_logger


class BaseAgent(ABC):
    """
    多智能体系统(MAS)的抽象基类
    
    专为营销行业多智能体系统设计，提供核心智能体功能。
    通过组合模式集成LLM能力和监控功能。

    子类必须实现:
        process_conversation: 处理对话状态的具体实现
    """
    
    def __init__(self):
        # 初始化组件
        self.llm_client = LLMClient()
        self.memory_manager = StorageManager()
        self.logger = get_component_logger(__name__)
    
    @abstractmethod
    async def process_conversation(self, state: WorkflowExecutionModel) -> dict:
        """
        处理对话状态的具体实现 (抽象方法)

        在LangGraph工作流中处理对话状态，更新相关信息并返回修改后的状态。
        子类必须实现此方法来定义具体的对话处理逻辑。

        参数:
            state: 当前工作流执行状态模型

        返回:
            dict: 更新后的对话状态
        """
        pass

    async def invoke_llm(
        self,
        request: CompletionsRequest,
        tenant_id: str,
        thread_id: UUID,
        max_iterations: int = 3
    ) -> LLMResponse:
        """
        调用 LLM 并支持工具调用

        该方法实现完整的工具调用循环：
        1. 调用 LLM，传入可用工具定义
        2. 如果 LLM 请求工具调用，执行工具
        3. 将工具结果返回给 LLM
        4. LLM 生成最终回复

        Args:
            request: LLM 请求
            tenant_id
            thread_id
            max_iterations: 最大工具调用迭代次数（防止无限循环）

        Returns:
            LLMResponse: 最终的 LLM 响应
        """
        if not request.tools:
            # 没有工具，直接调用 LLM
            return await self.llm_client.completions(request)


        # 迭代调用：LLM → 工具执行 → LLM → ...
        iteration = 0
        accumulated_tokens = TokenUsage(input_tokens=0, output_tokens=0)
        first_content = None

        while iteration < max_iterations:
            iteration += 1
            self.logger.info(f"工具调用迭代 {iteration}/{max_iterations}")

            # 调用 LLM
            response = await self.llm_client.completions(request)

            # 检查是否有工具调用
            if not response.tool_calls or response.finish_reason == "stop":
                self.logger.info("LLM 未请求工具调用，返回最终响应")

                # 如果当前响应没有content，但之前的迭代有content，则使用之前保存的content
                if not response.content and first_content:
                    self.logger.info("当前响应无内容，使用之前迭代中的content")
                    response.content = first_content

                return response

            self.logger.info(f"LLM 请求调用 {len(response.tool_calls)} 个工具")

            # 保存第一次迭代的content
            if iteration == 1 and response.content:
                tmp_content = response.content

                markers = ['\nantml:', '\nHuman:']

                positions = [pos for marker in markers if (pos := tmp_content.find(marker)) != -1]

                if positions:
                    cut_pos = min(positions)
                    tmp_content = tmp_content[:cut_pos]
                    self.logger.info("检测到回复被XML污染，已清理。")

                first_content = tmp_content.rstrip()

            accumulated_tokens.input_tokens += response.usage.input_tokens
            accumulated_tokens.output_tokens += response.usage.output_tokens
            response.usage = accumulated_tokens

            # 将 assistant 的响应添加到消息历史（包含 tool_calls）
            assistant_message = AssistantMessage(
                role="assistant",
                content=response.content,
                tool_calls=[
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    }
                    for tc in response.tool_calls
                ]
            )
            request.messages.append(assistant_message)

            # 执行所有工具调用
            for tool_call in response.tool_calls:
                handler = get_handler(tool_call.name)
                self.logger.info(f"执行工具: {tool_call.name}, 参数: {tool_call.arguments}")
                result = await handler(
                    tenant_id=tenant_id,
                    thread_id=thread_id,
                    **tool_call.arguments
                )
                result = json.dumps(result, ensure_ascii=False)

                # 将工具结果添加到消息历史
                tool_message = ToolMessage(
                    role="tool",
                    content=result,
                    tool_call_id=tool_call.id
                )
                request.messages.append(tool_message)

        self.logger.warning(f"达到最大工具调用迭代次数 {max_iterations}，返回最后响应")

        # 如果最后的响应没有content，使用第一次迭代的content
        if not response.content and first_content:
            self.logger.info("达到最大迭代次数，使用第一次迭代的content")
            response.content = first_content

        return response

    @staticmethod
    def _input_to_text(messages: MessageParams) -> str:
        """
        将输入转换为文本

        该方法处理多种输入格式，统一转换为纯文本字符串。
        仅提取用户的消息内容，用于长期记忆的检索。

        参数:
            messages: 输入内容

        返回:
            str: 转换后的文本内容
        """
        parts: list[str] = []
        for message in messages:
            # 只处理用户消息，跳过assistant消息
            if message.role != "user":
                continue

            # 处理字符串内容
            if isinstance(message.content, str):
                parts.append(message.content)
            else:
                for node in message.content:
                    if isinstance(node, InputContent):
                        parts.append(node.content)

        # 默认转为字符串
        return "\n".join(parts)