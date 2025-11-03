"""
记忆管理模块

该模块处理所有客户记忆和上下文管理功能：
- 短期记忆（STM）通过Redis实现
- 长期记忆（LTM）通过Elasticsearch实现
- 向量语义搜索通过Milvus实现
- 对话历史存储和管理

主要组件：
- ConversationStore: Redis短期会话存储
- IndexManager: Elasticsearch索引管理器
- VectorStore: Milvus向量存储接口
- SearchResult: 记忆搜索结果数据类
"""

from .conversation_store import ConversationStore
from .index_manager import IndexManager
from .vector_store import VectorStore, SearchResult

__all__ = [
    'ConversationStore',
    'IndexManager',
    'VectorStore',
    'SearchResult',
]
