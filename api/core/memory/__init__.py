"""
记忆管理模块

该模块处理所有客户记忆和上下文管理功能：
- 短期记忆（STM）通过Redis实现
- 长期记忆（LTM）通过Elasticsearch实现
- 向量语义搜索通过Milvus实现
- 对话历史存储和管理

主要组件：
- ConversationStore: Redis短期会话存储
- ElasticsearchIndex: Elasticsearch索引管理器
- StorageManager: 混合记忆协调器
- SummarizationService: LLM摘要服务
"""

from .conversation_store import ConversationStore
from .elasticsearch_index import ElasticsearchIndex
from .preservation_heuristics import conversation_quality_evaluator
from .storage_manager import StorageManager
from .summarize import SummarizationService


__all__ = [
    'ConversationStore',
    'ElasticsearchIndex',
    'StorageManager',
    'SummarizationService',
    "conversation_quality_evaluator"
]
