"""
对话存储模块

为B2B多租户场景设计的完整对话历史存储解决方案。
存储用户输入消息和LLM响应，支持多模态内容。

核心特性:
- 结构化消息存储
- 多模态内容支持
- 租户隔离
- 实时检索和分析
- 性能优化存储
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from elasticsearch import AsyncElasticsearch

from .models import ConversationMessage, MessageType
from .storage_operations import StorageOperations
from .search_analytics import SearchAnalytics
from .index_manager import IndexManager
from src.utils import get_component_logger

# 重新导出模型，保持向后兼容
from .models import MessageType, MessageStatus, ConversationMessage
from .message_builder import MessageBuilder, create_conversation_store


class ConversationStore:
    """
    对话存储引擎
    
    专为B2B场景设计的高性能消息存储系统:
    - 支持每秒1000+消息存储
    - 毫秒级历史检索
    - 多租户数据隔离
    - 智能数据生命周期管理
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.logger = get_component_logger(__name__, tenant_id)
        self._es_client: Optional[AsyncElasticsearch] = None
        
        # 组件初始化（延迟到连接建立后）
        self._storage_ops: Optional[StorageOperations] = None
        self._search_analytics: Optional[SearchAnalytics] = None
        self._index_manager: Optional[IndexManager] = None
    
    async def initialize(self, elasticsearch_url: str):
        """初始化Elasticsearch连接和组件"""
        try:
            self._es_client = AsyncElasticsearch([elasticsearch_url])
            
            # 初始化子组件
            self._storage_ops = StorageOperations(self.tenant_id, self._es_client)
            self._search_analytics = SearchAnalytics(self.tenant_id, self._es_client)
            self._index_manager = IndexManager(self.tenant_id, self._es_client)
            
            # 确保索引存在
            await self._index_manager.ensure_indices()
            
            self.logger.info(f"对话存储引擎初始化完成: {self.tenant_id}")
        except Exception as e:
            self.logger.error(f"对话存储引擎初始化失败: {e}")
            raise
    
    # 存储操作代理方法
    async def store_message(self, message: ConversationMessage) -> bool:
        """存储单条消息"""
        return await self._storage_ops.store_message(message)
    
    async def batch_store_messages(self, messages: List[ConversationMessage]) -> int:
        """批量存储消息"""
        return await self._storage_ops.batch_store_messages(messages)
    
    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 50,
        offset: int = 0,
        message_types: Optional[List[MessageType]] = None
    ) -> List[ConversationMessage]:
        """获取对话历史"""
        return await self._storage_ops.get_conversation_history(
            conversation_id, limit, offset, message_types
        )
    
    # 搜索和分析操作代理方法
    async def search_messages(
        self,
        customer_id: Optional[str] = None,
        query_text: Optional[str] = None,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        message_types: Optional[List[MessageType]] = None,
        limit: int = 20
    ) -> List[ConversationMessage]:
        """智能消息搜索"""
        return await self._search_analytics.search_messages(
            customer_id, query_text, date_range, message_types, limit
        )
    
    async def get_customer_message_stats(
        self,
        customer_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """获取客户消息统计"""
        return await self._search_analytics.get_customer_message_stats(customer_id, days)
    
    async def delete_old_messages(self, days_to_keep: int = 365) -> int:
        """清理旧消息数据"""
        return await self._search_analytics.delete_old_messages(days_to_keep)
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        storage_stats = self._storage_ops.get_stats()
        search_stats = self._search_analytics.get_stats()
        indices_info = await self._index_manager.get_indices_info()
        
        # 合并统计信息
        combined_stats = {**storage_stats, **search_stats}
        
        return {
            "tenant_id": self.tenant_id,
            "performance_stats": combined_stats,
            "indices_info": indices_info
        }
    
    async def cleanup(self):
        """清理资源"""
        if self._es_client:
            await self._es_client.close()
        self.logger.info(f"对话存储引擎已清理: {self.tenant_id}")