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
from typing import Dict, Any, Optional

from .message import AgentMessage, ConversationState
from src.llm.llm_mixin import LLMMixin
from src.utils import get_component_logger, ErrorHandler, StatusMixin
from src.infra.monitoring import AgentMonitor

from src.llm.intelligent_router import RoutingStrategy
from src.llm.provider_config import GlobalProviderConfig

class BaseAgent(ABC, StatusMixin, LLMMixin):
    """
    多智能体系统(MAS)的抽象基类
    
    专为美妆行业多智能体系统设计，提供核心智能体功能。
    通过组合模式集成LLM能力和监控功能。
    
    属性:
        agent_id: 智能体唯一标识符
        tenant_id: 租户标识符，用于多租户隔离
        agent_type: 智能体类型（从agent_id提取）
        logger: 日志记录器
        is_active: 智能体活跃状态
        error_handler: 错误处理器
        monitor: 智能体监控器
    
    子类必须实现:
        process_message: 处理单个消息的具体实现
        process_conversation: 处理对话状态的具体实现
    """
    
    def __init__(
        self, 
        agent_id: str, 
        tenant_id: Optional[str] = None,
        llm_config: Optional[GlobalProviderConfig] = None,
        routing_strategy: Optional[RoutingStrategy] = None
    ):
        # 提取智能体类型并初始化LLMMixin
        agent_type = agent_id.split('_')[0] if '_' in agent_id else "unknown"
        super().__init__(agent_id, agent_type, tenant_id, llm_config, routing_strategy)
        
        self.agent_id = agent_id
        self.tenant_id = tenant_id
        self.is_active = False
        self.logger = get_component_logger(__name__, agent_id)
        self.error_handler = ErrorHandler(agent_id)
        self.monitor = AgentMonitor(agent_id, agent_type, tenant_id)
    
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
    async def process_conversation(self, state: ConversationState) -> ConversationState:
        """
        处理对话状态的具体实现 (抽象方法)
        
        在LangGraph工作流中处理对话状态，更新相关信息并返回修改后的状态。
        子类必须实现此方法来定义具体的对话处理逻辑。
        
        参数:
            state: 当前对话状态对象
            
        返回:
            ConversationState: 更新后的对话状态
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
    
    def activate(self):
        """激活智能体，使其开始处理消息"""
        self.is_active = True
        self.logger.info(f"智能体 {self.agent_id} 已激活")
    
    def deactivate(self):
        """停用智能体，停止处理新消息"""
        self.is_active = False
        self.logger.info(f"智能体 {self.agent_id} 已停用")
    
    def get_status(self) -> Dict[str, Any]:
        """获取智能体状态信息（直接使用AgentMonitor）"""
        # 直接使用AgentMonitor的全面状态数据
        status_data = self.monitor.get_comprehensive_status()
        
        # 添加BaseAgent特定信息（没有在monitor中的）
        status_data['is_active'] = self.is_active
        if self.routing_strategy:
            status_data['routing_strategy'] = self.routing_strategy.value
            
        return self.create_status_response(status_data)
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取智能体指标数据"""
        comprehensive_status = self.monitor.get_comprehensive_status()
        
        return self.create_metrics_response(
            {
                **comprehensive_status['processing_metrics'],
                **comprehensive_status['error_rates'],
                **comprehensive_status['error_counts']
            },
            {
                'agent_id': self.agent_id,
                'tenant_id': self.tenant_id,
                'agent_type': self.agent_type,
                'is_active': self.is_active
            }
        )
    
    @property
    def agent_type(self) -> str:
        """智能体类型（从agent_id提取）"""
        return self.agent_id.split('_')[0] if '_' in self.agent_id else "unknown"
    
    def __repr__(self) -> str:
        return f"BaseAgent(id={self.agent_id}, tenant={self.tenant_id}, active={self.is_active})"