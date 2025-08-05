"""
智能体注册管理模块

该模块提供智能体的注册、发现、路由和生命周期管理功能。

核心功能:
- 智能体注册和注销
- 消息路由和转发
- 智能体发现和查询
- 健康状态监控
- 多租户隔离管理
"""

from typing import Dict, Any, Optional, List
from .agent import BaseAgent
from .message import AgentMessage
from src.utils import (
    get_component_logger,
    StatusMixin,
    ProcessingConstants,
    StatusConstants,
    with_error_handling
)


class AgentRegistry(StatusMixin):
    """
    智能体注册中心
    
    管理系统中所有智能体的注册、发现和路由。
    使用StatusMixin提供标准化的状态管理功能。
    
    属性:
        agents: 已注册智能体字典 {agent_id: BaseAgent}
        routing_table: 消息路由表 {sender_id: [recipient_ids]}
        tenant_agents: 按租户分组的智能体 {tenant_id: [agent_ids]}
        logger: 日志记录器
    """
    
    def __init__(self):
        """初始化智能体注册中心"""
        super().__init__()
        
        self.agents: Dict[str, BaseAgent] = {}
        self.routing_table: Dict[str, List[str]] = {}
        self.tenant_agents: Dict[str, List[str]] = {}
        self.logger = get_component_logger(__name__)
        
        self.logger.info("智能体注册中心初始化完成")
    
    @with_error_handling(fallback_response=False)
    def register_agent(self, agent: BaseAgent) -> bool:
        """
        注册智能体到系统中
        
        将智能体加入注册表，建立租户关联，激活智能体服务。
        使用错误处理装饰器自动处理异常。
        
        参数:
            agent: 要注册的智能体实例
            
        返回:
            bool: 注册是否成功
        """
        if agent.agent_id in self.agents:
            self.logger.warning(f"智能体 {agent.agent_id} 已存在，跳过注册")
            return False
        
        # 注册智能体
        self.agents[agent.agent_id] = agent
        
        # 建立租户关联
        if agent.tenant_id:
            if agent.tenant_id not in self.tenant_agents:
                self.tenant_agents[agent.tenant_id] = []
            self.tenant_agents[agent.tenant_id].append(agent.agent_id)
        
        # 激活智能体
        agent.activate()
        
        self.logger.info(
            f"智能体注册成功: {agent.agent_id}, 租户: {agent.tenant_id}"
        )
        return True
    
    @with_error_handling(fallback_response=False)
    def unregister_agent(self, agent_id: str) -> bool:
        """
        从系统中注销智能体
        
        移除智能体注册信息，清理路由表和租户关联。
        
        参数:
            agent_id: 要注销的智能体ID
            
        返回:
            bool: 注销是否成功
        """
        if agent_id not in self.agents:
            self.logger.warning(f"智能体 {agent_id} 不存在，无法注销")
            return False
        
        agent = self.agents[agent_id]
        
        # 停用智能体
        agent.deactivate()
        
        # 从注册表移除
        del self.agents[agent_id]
        
        # 清理路由表
        if agent_id in self.routing_table:
            del self.routing_table[agent_id]
        
        # 清理租户关联
        if agent.tenant_id and agent.tenant_id in self.tenant_agents:
            self.tenant_agents[agent.tenant_id].remove(agent_id)
            if not self.tenant_agents[agent.tenant_id]:
                del self.tenant_agents[agent.tenant_id]
        
        self.logger.info(f"智能体注销成功: {agent_id}")
        return True
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """
        根据ID获取智能体实例
        
        参数:
            agent_id: 智能体唯一标识符
            
        返回:
            Optional[BaseAgent]: 智能体实例，不存在时返回None
        """
        return self.agents.get(agent_id)
    
    def get_tenant_agents(self, tenant_id: str) -> List[BaseAgent]:
        """
        获取指定租户的所有智能体
        
        参数:
            tenant_id: 租户标识符
            
        返回:
            List[BaseAgent]: 租户智能体列表
        """
        if tenant_id not in self.tenant_agents:
            return []
        
        return [
            self.agents[agent_id] 
            for agent_id in self.tenant_agents[tenant_id]
            if agent_id in self.agents
        ]
    
    @with_error_handling(fallback_response=None)
    def route_message(self, message: AgentMessage) -> Optional[BaseAgent]:
        """
        路由消息到目标智能体
        
        根据消息中的接收方ID查找并返回目标智能体。
        验证租户隔离和智能体可用性。
        
        参数:
            message: 要路由的消息
            
        返回:
            Optional[BaseAgent]: 目标智能体，不存在或不可用时返回None
        """
        target_agent = self.get_agent(message.recipient)
        
        if not target_agent:
            self.logger.warning(f"目标智能体不存在: {message.recipient}")
            return None
        
        # 验证租户隔离
        if message.tenant_id and target_agent.tenant_id != message.tenant_id:
            self.logger.error(
                f"租户隔离违规: 消息租户 {message.tenant_id} "
                f"尝试访问智能体租户 {target_agent.tenant_id}"
            )
            return None
        
        if not target_agent.is_active:
            self.logger.warning(f"目标智能体未激活: {message.recipient}")
            return None
        
        return target_agent
    
    async def broadcast_message(
            self,
            sender_id: str, 
            message_type: str, 
            payload: Dict[str, Any], 
            recipients: List[str]
        ) -> List[AgentMessage]:
        """
        广播消息给多个智能体
        
        向指定的智能体列表发送相同的消息。
        自动处理发送失败的情况。
        
        参数:
            sender_id: 发送方智能体ID
            message_type: 消息类型
            payload: 消息载荷
            recipients: 接收方智能体ID列表
            
        返回:
            List[AgentMessage]: 成功发送的消息列表
        """
        sender = self.get_agent(sender_id)
        if not sender:
            self.logger.error(f"发送方智能体不存在: {sender_id}")
            return []
        
        messages = []
        for recipient_id in recipients:
            if recipient_id in self.agents:
                try:
                    message = await sender.send_message(recipient_id, message_type, payload)
                    messages.append(message)
                except Exception as e:
                    self.logger.error(f"发送消息失败 {sender_id} -> {recipient_id}: {e}")
            else:
                self.logger.warning(f"接收方智能体不存在: {recipient_id}")
        
        self.logger.info(f"广播消息完成: {sender_id} -> {len(messages)}/{len(recipients)} 成功")
        return messages
    
    def get_registry_status(self) -> Dict[str, Any]:
        """
        获取注册中心状态信息
        
        使用StatusMixin提供标准化状态响应。
        
        返回:
            Dict[str, Any]: 注册中心状态信息
        """
        active_agents = sum(1 for agent in self.agents.values() if agent.is_active)
        
        tenant_stats = {}
        for tenant_id, agent_ids in self.tenant_agents.items():
            tenant_stats[tenant_id] = {
                "total_agents": len(agent_ids),
                "active_agents": sum(
                    1 for agent_id in agent_ids 
                    if agent_id in self.agents and self.agents[agent_id].is_active
                )
            }
        
        status_data = {
            "total_registered_agents": len(self.agents),
            "active_agents": active_agents,
            "inactive_agents": len(self.agents) - active_agents,
            "tenant_count": len(self.tenant_agents),
            "tenant_stats": tenant_stats,
            "registered_agent_ids": list(self.agents.keys())
        }
        
        return self.create_status_response(status_data, "AgentRegistry")
    
    def get_agent_details(self) -> List[Dict[str, Any]]:
        """
        获取所有智能体的详细信息
        
        返回:
            List[Dict[str, Any]]: 智能体详细信息列表
        """
        return [
            {
                "agent_id": agent_id,
                "tenant_id": agent.tenant_id,
                "is_active": agent.is_active,
                "agent_type": type(agent).__name__,
                "queue_size": len(agent.message_queue),
                "messages_processed": agent.processing_stats["messages_processed"],
                "errors": agent.processing_stats["errors"],
                "last_activity": (
                    agent.processing_stats["last_activity"].isoformat() 
                    if agent.processing_stats["last_activity"] else None
                )
            }
            for agent_id, agent in self.agents.items()
        ]
    
    def cleanup_tenant(self, tenant_id: str) -> int:
        """
        清理指定租户的所有智能体
        
        用于租户数据清理或测试环境重置。
        
        参数:
            tenant_id: 要清理的租户ID
            
        返回:
            int: 清理的智能体数量
        """
        if tenant_id not in self.tenant_agents:
            return 0
        
        agent_ids = self.tenant_agents[tenant_id].copy()
        cleaned_count = 0
        
        for agent_id in agent_ids:
            if self.unregister_agent(agent_id):
                cleaned_count += 1
        
        self.logger.info(f"租户 {tenant_id} 清理完成，移除 {cleaned_count} 个智能体")
        return cleaned_count
    
    def health_check(self) -> Dict[str, Any]:
        """
        执行健康检查
        
        检查所有注册智能体的健康状态，使用标准化健康响应。
        
        返回:
            Dict[str, Any]: 健康检查结果
        """
        healthy_agents = []
        unhealthy_agents = []
        
        for agent_id, agent in self.agents.items():
            try:
                status = agent.get_status()
                if agent.is_active and status:
                    healthy_agents.append(agent_id)
                else:
                    unhealthy_agents.append(agent_id)
            except Exception as e:
                unhealthy_agents.append(agent_id)
                self.logger.error(f"智能体 {agent_id} 健康检查失败: {e}")
        
        health_score = len(healthy_agents) / len(self.agents) if self.agents else 1.0
        
        # 确定整体健康状态
        if health_score < 0.7:
            health_status = StatusConstants.CRITICAL
        elif health_score < 0.9:
            health_status = StatusConstants.WARNING
        else:
            health_status = StatusConstants.HEALTHY
        
        metrics = {
            "health_score": health_score,
            "healthy_count": len(healthy_agents),
            "unhealthy_count": len(unhealthy_agents),
            "total_agents": len(self.agents)
        }
        
        details = {
            "healthy_agents": healthy_agents,
            "unhealthy_agents": unhealthy_agents
        }
        
        return self.create_metrics_response(metrics, details)
    
    def __len__(self) -> int:
        """返回注册智能体数量"""
        return len(self.agents)
    
    def __contains__(self, agent_id: str) -> bool:
        """检查智能体是否已注册"""
        return agent_id in self.agents


# 全局智能体注册中心实例
agent_registry = AgentRegistry() 