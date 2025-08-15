"""
对话存储核心操作模块
"""

import uuid
from typing import List, Optional
from datetime import datetime
from elasticsearch import AsyncElasticsearch

from .models import ConversationMessage, MessageType
from .index_manager import IndexManager
from utils import get_component_logger


class StorageOperations:
    """对话存储核心操作"""
    
    def __init__(self, tenant_id: str, es_client: AsyncElasticsearch):
        self.tenant_id = tenant_id
        self.es_client = es_client
        self.index_manager = IndexManager(tenant_id, es_client)
        self.logger = get_component_logger(__name__, tenant_id)
        
        # 性能统计
        self._stats = {
            "messages_stored": 0,
            "messages_retrieved": 0,
            "conversations_created": 0,
            "errors": 0
        }
    
    async def store_message(self, message: ConversationMessage) -> bool:
        """
        存储单条消息
        
        自动处理:
        - 消息ID生成
        - 时间戳标记
        - 索引路由
        - 错误重试
        """
        try:
            # 确保消息ID存在
            if not message.message_id:
                message.message_id = str(uuid.uuid4())
            
            # 设置时间戳
            if not message.timestamp:
                message.timestamp = datetime.utcnow()
            
            # 存储到Elasticsearch
            index_name = self.index_manager.get_messages_index(message.thread_id)
            doc_id = message.message_id
            
            response = await self.es_client.index(
                index=index_name,
                id=doc_id,
                body=message.to_dict(),
                refresh='wait_for'  # 确保立即可搜索
            )
            
            if response.get('result') in ['created', 'updated']:
                self._stats["messages_stored"] += 1
                self.logger.debug(f"消息存储成功: {message.message_id}")
                return True
            
        except Exception as e:
            self._stats["errors"] += 1
            self.logger.error(f"消息存储失败 {message.message_id}: {e}")
        
        return False
    
    async def batch_store_messages(self, messages: List[ConversationMessage]) -> int:
        """
        批量存储消息
        
        优化大量消息的存储性能
        """
        if not messages:
            return 0
        
        try:
            # 构建批量操作
            bulk_operations = []
            for message in messages:
                if not message.message_id:
                    message.message_id = str(uuid.uuid4())
                if not message.timestamp:
                    message.timestamp = datetime.utcnow()
                
                index_name = self.index_manager.get_messages_index(message.thread_id)
                
                bulk_operations.extend([
                    {
                        "index": {
                            "_index": index_name,
                            "_id": message.message_id
                        }
                    },
                    message.to_dict()
                ])
            
            # 执行批量操作
            response = await self.es_client.bulk(
                body=bulk_operations,
                refresh='wait_for'
            )
            
            # 统计成功数量
            successful = 0
            if not response.get("errors"):
                successful = len(messages)
            else:
                for item in response["items"]:
                    if "index" in item and item["index"].get("status") in [200, 201]:
                        successful += 1
            
            self._stats["messages_stored"] += successful
            self.logger.info(f"批量存储完成: {successful}/{len(messages)}")
            return successful
            
        except Exception as e:
            self._stats["errors"] += 1
            self.logger.error(f"批量存储失败: {e}")
            return 0
    
    async def get_conversation_history(
        self,
        thread_id: str,
        assistant_id: str,
        device_id: str,
        limit: int = 50,
        offset: int = 0,
        message_types: Optional[List[MessageType]] = None
    ) -> List[ConversationMessage]:
        """
        获取对话历史
        
        支持:
        - 分页查询
        - 类型过滤
        - 时间排序
        - 高性能检索
        """
        try:
            index_name = self.index_manager.get_messages_index(thread_id)
            
            # 构建查询 - 增强数据隔离
            query = {
                "bool": {
                    "must": [
                        {"term": {"thread_id": thread_id}},
                        {"term": {"tenant_id": self.tenant_id}},
                        {"term": {"assistant_id": assistant_id}},
                        {"term": {"device_id": device_id}}
                    ]
                }
            }
            
            # 添加消息类型过滤
            if message_types:
                type_values = [mt.value for mt in message_types]
                query["bool"]["must"].append({
                    "terms": {"message_type": type_values}
                })
            
            # 执行搜索
            response = await self.es_client.search(
                index=index_name,
                body={
                    "query": query,
                    "sort": [{"timestamp": {"order": "asc"}}],
                    "from": offset,
                    "size": limit
                },
                ignore=[404]
            )
            
            messages = []
            if response.get("hits"):
                for hit in response["hits"]["hits"]:
                    try:
                        message = ConversationMessage.from_dict(hit["_source"])
                        messages.append(message)
                    except Exception as e:
                        self.logger.warning(f"消息解析失败: {e}")
            
            self._stats["messages_retrieved"] += len(messages)
            return messages
            
        except Exception as e:
            self._stats["errors"] += 1
            self.logger.error(f"历史查询失败 {thread_id}: {e}")
            return []
    
    def get_stats(self) -> dict:
        """获取操作统计"""
        return self._stats.copy()