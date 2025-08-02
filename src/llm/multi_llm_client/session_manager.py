"""
会话管理器模块

负责管理LLM客户端的会话和上下文。
"""

import asyncio
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from src.utils import get_component_logger


class Session:
    """会话对象"""
    
    def __init__(self, session_id: str, tenant_id: str, agent_type: str):
        """
        初始化会话
        
        参数:
            session_id: 会话ID
            tenant_id: 租户ID
            agent_type: 智能体类型
        """
        self.session_id = session_id
        self.tenant_id = tenant_id
        self.agent_type = agent_type
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        self.is_active = True
        
        # 会话数据
        self.context = {}
        self.message_history = []
        self.metadata = {}
        
        # 统计信息
        self.request_count = 0
        self.total_tokens = 0
        self.total_cost = 0.0
    
    def update_access_time(self):
        """更新最后访问时间"""
        self.last_accessed = datetime.now()
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """添加消息到历史"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.message_history.append(message)
    
    def get_recent_messages(self, count: int = 10) -> List[Dict]:
        """获取最近的消息"""
        return self.message_history[-count:] if self.message_history else []
    
    def update_stats(self, tokens: int, cost: float):
        """更新统计信息"""
        self.request_count += 1
        self.total_tokens += tokens
        self.total_cost += cost


class SessionManager:
    """会话管理器"""
    
    def __init__(self, session_timeout_minutes: int = 60):
        """
        初始化会话管理器
        
        参数:
            session_timeout_minutes: 会话超时时间（分钟）
        """
        self.logger = get_component_logger(__name__, "SessionManager")
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        
        # 会话存储
        self.sessions: Dict[str, Session] = {}
        self.tenant_sessions: Dict[str, Set[str]] = {}
        
        # 清理任务
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
    
    async def start(self):
        """启动会话管理器"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())
            self.logger.info("会话管理器启动完成")
    
    async def stop(self):
        """停止会话管理器"""
        self._shutdown_event.set()
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("会话管理器已停止")
    
    def create_session(
        self, 
        session_id: str, 
        tenant_id: str, 
        agent_type: str = "default"
    ) -> Session:
        """
        创建新会话
        
        参数:
            session_id: 会话ID
            tenant_id: 租户ID
            agent_type: 智能体类型
            
        返回:
            Session: 会话对象
        """
        if session_id in self.sessions:
            self.logger.warning(f"会话已存在: {session_id}")
            return self.sessions[session_id]
        
        session = Session(session_id, tenant_id, agent_type)
        self.sessions[session_id] = session
        
        # 添加到租户会话索引
        if tenant_id not in self.tenant_sessions:
            self.tenant_sessions[tenant_id] = set()
        self.tenant_sessions[tenant_id].add(session_id)
        
        self.logger.debug(f"创建会话: {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """
        获取会话
        
        参数:
            session_id: 会话ID
            
        返回:
            Optional[Session]: 会话对象或None
        """
        session = self.sessions.get(session_id)
        if session and session.is_active:
            session.update_access_time()
            return session
        return None
    
    def get_or_create_session(
        self, 
        session_id: str, 
        tenant_id: str, 
        agent_type: str = "default"
    ) -> Session:
        """
        获取或创建会话
        
        参数:
            session_id: 会话ID
            tenant_id: 租户ID
            agent_type: 智能体类型
            
        返回:
            Session: 会话对象
        """
        session = self.get_session(session_id)
        if session is None:
            session = self.create_session(session_id, tenant_id, agent_type)
        return session
    
    def close_session(self, session_id: str):
        """
        关闭会话
        
        参数:
            session_id: 会话ID
        """
        session = self.sessions.get(session_id)
        if session:
            session.is_active = False
            
            # 从租户索引中移除
            if session.tenant_id in self.tenant_sessions:
                self.tenant_sessions[session.tenant_id].discard(session_id)
                if not self.tenant_sessions[session.tenant_id]:
                    del self.tenant_sessions[session.tenant_id]
            
            del self.sessions[session_id]
            self.logger.debug(f"关闭会话: {session_id}")
    
    def get_tenant_sessions(self, tenant_id: str) -> List[Session]:
        """
        获取租户的所有会话
        
        参数:
            tenant_id: 租户ID
            
        返回:
            List[Session]: 会话列表
        """
        session_ids = self.tenant_sessions.get(tenant_id, set())
        return [
            self.sessions[session_id] 
            for session_id in session_ids 
            if session_id in self.sessions and self.sessions[session_id].is_active
        ]
    
    async def _cleanup_expired_sessions(self):
        """清理过期会话"""
        while not self._shutdown_event.is_set():
            try:
                current_time = datetime.now()
                expired_sessions = []
                
                for session_id, session in self.sessions.items():
                    if current_time - session.last_accessed > self.session_timeout:
                        expired_sessions.append(session_id)
                
                for session_id in expired_sessions:
                    self.close_session(session_id)
                    self.logger.debug(f"清理过期会话: {session_id}")
                
                if expired_sessions:
                    self.logger.info(f"清理了 {len(expired_sessions)} 个过期会话")
                
                # 等待下次清理
                await asyncio.sleep(300)  # 每5分钟清理一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"会话清理失败: {str(e)}")
                await asyncio.sleep(60)  # 出错后等待1分钟再试
    
    @asynccontextmanager
    async def session_context(self, session_id: str, tenant_id: str, agent_type: str = "default"):
        """
        会话上下文管理器
        
        参数:
            session_id: 会话ID
            tenant_id: 租户ID
            agent_type: 智能体类型
        """
        session = self.get_or_create_session(session_id, tenant_id, agent_type)
        try:
            yield session
        finally:
            session.update_access_time()
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        获取会话统计信息
        
        返回:
            Dict[str, Any]: 统计信息
        """
        total_sessions = len(self.sessions)
        active_sessions = sum(1 for s in self.sessions.values() if s.is_active)
        
        # 按租户统计
        tenant_stats = {}
        for tenant_id, session_ids in self.tenant_sessions.items():
            tenant_stats[tenant_id] = len(session_ids)
        
        # 按智能体类型统计
        agent_stats = {}
        for session in self.sessions.values():
            if session.is_active:
                agent_type = session.agent_type
                agent_stats[agent_type] = agent_stats.get(agent_type, 0) + 1
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "tenant_stats": tenant_stats,
            "agent_stats": agent_stats,
            "session_timeout_minutes": self.session_timeout.total_seconds() / 60
        }