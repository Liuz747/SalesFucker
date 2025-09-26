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
from typing import Optional

from .message import AgentMessage
from ...app.entities import WorkflowExecutionModel
from utils import get_component_logger
from infra.runtimes import LLMClient, LLMRequest

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

        # 默认即为活跃状态；无需显式激活流程即可直接使用
        self.is_active = True

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
    
    async def invoke_llm(
        self,
        messages: list,
        model: str = "gpt-4o-mini",
        provider: str = "openai",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        简单的LLM调用方法
        
        参数:
            messages: 消息列表，格式 [{"role": "user", "content": "text"}]
            model: 模型名称
            provider: 供应商名称
            temperature: 温度参数
            max_tokens: 最大令牌数
            
        返回:
            str: LLM响应内容
        """
        request = LLMRequest(
            id=None,
            messages=messages,
            model=model,
            provider=provider,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        response = await self.llm_client.completions(request)
        return response.content