"""
智能体基础类模块

该模块定义了所有智能体的抽象基类，提供智能体的基础功能和接口规范。
所有具体的智能体实现都应该继承此基类。

核心功能:
- 智能体生命周期管理
- 消息处理抽象接口
- 错误处理和降级机制
- 智能体状态管理
"""

from abc import ABC, abstractmethod

from core.entities import WorkflowExecutionModel
from infra.runtimes import LLMClient, CompletionsRequest, LLMResponse
from libs.types import MessageParams, InputContent
from utils import get_component_logger


class BaseAgent(ABC):
    """
    多智能体系统(MAS)的抽象基类
    
    专为美妆行业多智能体系统设计，提供核心智能体功能。
    通过组合模式集成LLM能力和监控功能。
    
    属性:
        agent_id: 智能体唯一标识符
        agent_type: 智能体类型（从agent_id提取）
        logger: 日志记录器
        is_active: 智能体活跃状态
        monitor: 智能体监控器
    
    子类必须实现:
        process_conversation: 处理对话状态的具体实现
    """
    
    def __init__(self):
        # Auto-derive agent_id from class name
        class_name = self.__class__.__name__
        if class_name.endswith('Agent'):
            self.agent_id = class_name[:-5].lower()  # ComplianceAgent -> compliance
        else:
            self.agent_id = class_name.lower()

        # 初始化LLM客户端
        self.llm_client = LLMClient()

        # 初始化其他组件
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
    
    async def invoke_llm(self, request: CompletionsRequest) -> LLMResponse:
        """
        简单的LLM调用方法

        参数:
            request: LLM请求

        返回:
            str: LLM响应内容
        """

        return await self.llm_client.completions(request)

    def _input_to_text(self, messages: MessageParams) -> str:
        """
        将输入转换为文本（仅提取用户消息）

        该方法处理多种输入格式，统一转换为纯文本字符串。
        只提取role为"user"的消息内容，过滤掉assistant消息。

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