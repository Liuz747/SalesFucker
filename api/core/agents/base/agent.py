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
from utils import get_component_logger
from infra.monitoring import AgentMonitor
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
        process_message: 处理单个消息的具体实现
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
        self.logger = get_component_logger(__name__, self.agent_id)
        self.monitor = AgentMonitor(self.agent_id, self.agent_type)
    
    @abstractmethod
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """
        处理单个智能体消息的具体实现 (抽象方法)
        
        每个具体的智能体子类必须实现此方法来定义具体的消息处理逻辑。
        性能统计由基类自动处理。
        
        参数:
            message: 待处理的智能体消息
            
        返回:
            AgentMessage: 处理结果消息
        """
        pass
    
    @abstractmethod
    async def process_conversation(self, state: dict) -> dict:
        """
        处理对话状态的具体实现 (抽象方法)
        
        在LangGraph工作流中处理对话状态，更新相关信息并返回修改后的状态。
        子类必须实现此方法来定义具体的对话处理逻辑。
        
        参数:
            state: 当前对话状态字典
            
        返回:
            dict[str, Any]: 更新后的对话状态
        """
        pass
    
    async def send_message(
            self,
            recipient: str,
            message_type: str,
            payload: dict, 
            context: Optional[dict] = None
    ) -> AgentMessage:
        """
        发送消息给其他智能体
        
        创建标准格式的智能体消息并发送给指定接收方。
        
        参数:
            recipient: 接收方智能体ID
            message_type: 消息类型 (query/response/notification/trigger/suggestion)
            payload: 消息载荷数据
            context: 可选的上下文信息
            
        返回:
            AgentMessage: 创建的消息对象
        """
        message = AgentMessage(
            sender=self.agent_id,
            recipient=recipient,
            message_type=message_type,
            payload=payload,
            context=context or {}
        )
        
        self.logger.info(f"发送{message_type}消息给 {recipient}")
        return message
    
    async def llm_call(
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
    
    async def handle_error(self, error: Exception, context: dict = None):
        """
        处理智能体错误
        
        参数:
            error: 发生的错误
            context: 错误上下文信息
        """
        self.logger.error(f"智能体错误: {error}", exc_info=True)
        if context:
            self.logger.error(f"错误上下文: {context}")
    
    def update_stats(self, processing_time: float = None, time_taken: float = None, **kwargs):
        """
        更新处理统计信息
        
        参数:
            processing_time: 处理时间（毫秒）
            time_taken: 处理时间（向后兼容）
            **kwargs: 其他参数
        """
        # 向后兼容处理
        actual_time = processing_time or time_taken or 0
        
        # 基础统计更新，具体实现可以在子类中扩展
        self.logger.debug(f"处理完成，耗时: {actual_time:.2f}ms")
    