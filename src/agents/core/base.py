"""
智能体基础类模块

该模块定义了所有智能体的抽象基类，提供智能体的基础功能和接口规范。
所有具体的智能体实现都应该继承此基类。

核心功能:
- 智能体生命周期管理
- 消息处理抽象接口
- 错误处理和降级机制
- 性能统计和监控
- 智能体状态管理
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

from .message import AgentMessage, ConversationState
from src.utils import (
    get_component_logger, 
    get_current_datetime,
    StatusMixin,
    with_error_handling,
    ErrorHandler,
    ProcessingConstants
)


class BaseAgent(ABC, StatusMixin):
    """
    多智能体系统的抽象基类
    
    定义所有智能体必须实现的基础接口和通用功能。
    使用混入类提供标准化的状态管理功能。
    
    属性:
        agent_id: 智能体唯一标识符
        tenant_id: 租户标识符，用于多租户隔离
        logger: 日志记录器
        is_active: 智能体活跃状态
        message_queue: 消息队列
        processing_stats: 处理统计信息
        error_handler: 错误处理器
    
    子类必须实现:
        process_message: 处理单个消息的具体实现
        process_conversation: 处理对话状态的具体实现
    """
    
    def __init__(self, agent_id: str, tenant_id: Optional[str] = None):
        """
        初始化智能体基础属性
        
        参数:
            agent_id: 智能体唯一标识符，格式为 "类型_租户ID"
            tenant_id: 租户标识符，用于多租户数据隔离
        """
        super().__init__()
        
        self.agent_id = agent_id
        self.tenant_id = tenant_id
        self.logger = get_component_logger(__name__, agent_id)
        
        # 智能体状态管理
        self.is_active = False
        self.message_queue: List[AgentMessage] = []
        
        # 性能统计信息
        self.processing_stats = {
            "messages_processed": 0,
            "errors": 0,
            "last_activity": None,
            "average_response_time": 0.0,
            "total_processing_time": 0.0
        }
        
        # 错误处理器
        self.error_handler = ErrorHandler(agent_id)
        
        self.logger.info(f"智能体初始化完成: {agent_id}, 租户: {tenant_id}")
    
    @abstractmethod
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """
        处理单个智能体消息的具体实现 (抽象方法)
        
        每个具体的智能体子类必须实现此方法来定义具体的消息处理逻辑。
        此方法专注于业务逻辑，性能统计由基类自动处理。
        
        参数:
            message: 待处理的智能体消息
            
        返回:
            AgentMessage: 处理结果消息
            
        异常:
            NotImplementedError: 子类未实现此方法
        """
        pass
    
    @abstractmethod
    async def process_conversation(self, state: ConversationState) -> ConversationState:
        """
        处理对话状态的具体实现 (抽象方法)
        
        在LangGraph工作流中处理对话状态，更新相关信息并返回修改后的状态。
        子类必须实现此方法来定义具体的对话处理逻辑。
        此方法专注于业务逻辑，性能统计由基类自动处理。
        
        参数:
            state: 当前对话状态对象
            
        返回:
            ConversationState: 更新后的对话状态
            
        异常:
            NotImplementedError: 子类未实现此方法
        """
        pass
    
    async def send_message(
            self,
            recipient: str,
            message_type: str,
            payload: Dict[str, Any], 
            context: Optional[Dict[str, Any]] = None
    ) -> AgentMessage:
        """
        发送消息给其他智能体
        
        创建标准格式的智能体消息并发送给指定接收方。
        自动填充发送方信息和租户上下文。
        
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
            context=context or {},
            tenant_id=self.tenant_id
        )
        
        self.logger.info(f"发送{message_type}消息给 {recipient}")
        return message
    
    async def handle_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理智能体运行时错误
        
        使用标准化错误处理器，提供统一的错误处理机制。
        
        参数:
            error: 发生的异常对象
            context: 错误发生时的上下文信息
            
        返回:
            Dict[str, Any]: 标准化的错误信息
        """
        self.processing_stats["errors"] += 1
        return self.error_handler.handle_error(error, context)
    
    def update_stats(self, processing_time: float = 0.0):
        """
        更新智能体处理统计信息
        
        记录消息处理次数、处理时间等性能指标，用于监控和优化。
        
        参数:
            processing_time: 处理耗时(毫秒)，默认为0
        """
        self.processing_stats["messages_processed"] += 1
        self.processing_stats["last_activity"] = get_current_datetime()
        
        # 更新处理时间统计
        if processing_time > 0:
            total_time = self.processing_stats["total_processing_time"] + processing_time
            self.processing_stats["total_processing_time"] = total_time
            
            # 计算平均响应时间
            self.processing_stats["average_response_time"] = (
                total_time / self.processing_stats["messages_processed"]
            )
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取智能体当前状态信息
        
        使用StatusMixin提供的标准化状态响应格式。
        
        返回:
            Dict[str, Any]: 包含状态信息的字典
        """
        status_data = {
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id,
            "is_active": self.is_active,
            "queue_size": len(self.message_queue),
            "processing_stats": self.processing_stats.copy()
        }
        
        return self.create_status_response(status_data, "BaseAgent")
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        获取智能体健康状态
        
        根据错误率和处理性能判断健康状态。
        
        返回:
            Dict[str, Any]: 健康状态信息
        """
        total_processed = self.processing_stats["messages_processed"]
        error_rate = 0.0
        
        if total_processed > 0:
            error_rate = (self.processing_stats["errors"] / total_processed) * 100
        
        # 确定健康状态
        health_status = self.determine_health_status(
            error_rate,
            ProcessingConstants.WARNING_ERROR_RATE,
            ProcessingConstants.CRITICAL_ERROR_RATE
        )
        
        metrics = {
            "error_rate": error_rate,
            "messages_processed": total_processed,
            "average_response_time": self.processing_stats["average_response_time"],
            "queue_size": len(self.message_queue)
        }
        
        details = {
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id,
            "is_active": self.is_active
        }
        
        return self.create_health_response(health_status, metrics, details)
    
    def activate(self):
        """激活智能体，使其开始处理消息"""
        self.is_active = True
        self.logger.info(f"智能体 {self.agent_id} 已激活")
    
    def deactivate(self):
        """停用智能体，停止处理新消息"""
        self.is_active = False
        self.logger.info(f"智能体 {self.agent_id} 已停用")
    
    def clear_queue(self):
        """清空消息队列"""
        queue_size = len(self.message_queue)
        self.message_queue.clear()
        self.logger.info(f"已清空 {self.agent_id} 的消息队列 ({queue_size} 条消息)")
    
    def add_to_queue(self, message: AgentMessage):
        """
        将消息添加到处理队列
        
        检查队列大小限制，防止内存溢出。
        
        参数:
            message: 要添加的消息
        """
        if len(self.message_queue) >= ProcessingConstants.MAX_QUEUE_SIZE:
            self.logger.warning(f"队列已满，丢弃最早的消息: {self.agent_id}")
            self.message_queue.pop(0)
        
        self.message_queue.append(message)
        self.logger.debug(f"消息已添加到 {self.agent_id} 队列，当前队列长度: {len(self.message_queue)}")
    
    def __str__(self) -> str:
        """返回智能体的字符串表示"""
        return f"BaseAgent(id={self.agent_id}, tenant={self.tenant_id}, active={self.is_active})"
    
    def __repr__(self) -> str:
        """返回智能体的详细字符串表示"""
        return (f"BaseAgent(agent_id='{self.agent_id}', tenant_id='{self.tenant_id}', "
                f"is_active={self.is_active}, messages_processed={self.processing_stats['messages_processed']})") 