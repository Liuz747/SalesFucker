"""
Elasticsearch索引管理模块
"""

from typing import Dict, Any
from elasticsearch import AsyncElasticsearch
from utils import get_component_logger


class IndexManager:
    """Elasticsearch索引管理器"""
    
    def __init__(self, tenant_id: str, es_client: AsyncElasticsearch):
        self.tenant_id = tenant_id
        self.es_client = es_client
        self.logger = get_component_logger(__name__, tenant_id)
    
    def get_messages_index(self, conversation_id: str) -> str:
        """
        获取消息索引名称
        
        使用对话ID的哈希值进行索引分片，提高性能
        """
        # 使用conversation_id的哈希值来分片索引
        hash_suffix = abs(hash(conversation_id)) % 10
        return f"{self.tenant_id}_messages_{hash_suffix:02d}"
    
    async def ensure_indices(self):
        """确保所有必要的索引存在"""
        # 创建消息存储索引模板
        template_name = f"{self.tenant_id}_messages_template"
        template_body = {
            "index_patterns": [f"{self.tenant_id}_messages_*"],
            "template": {
                "settings": {
                    "number_of_shards": 3,
                    "number_of_replicas": 1,
                    "refresh_interval": "1s",
                    "index.max_result_window": 50000
                },
                "mappings": {
                    "properties": {
                        "message_id": {"type": "keyword"},
                        "conversation_id": {"type": "keyword"},
                        "tenant_id": {"type": "keyword"},
                        "customer_id": {"type": "keyword"},
                        "message_type": {"type": "keyword"},
                        "content": {
                            "type": "text",
                            "analyzer": "ik_max_word",
                            "search_analyzer": "ik_smart"
                        },
                        "metadata": {"type": "object", "enabled": True},
                        "timestamp": {"type": "date"},
                        "status": {"type": "keyword"},
                        "model_name": {"type": "keyword"},
                        "tokens_used": {"type": "integer"},
                        "processing_time_ms": {"type": "float"},
                        "attachments": {"type": "object", "enabled": False},
                        "sentiment_score": {"type": "float"},
                        "intent_categories": {"type": "keyword"}
                    }
                }
            }
        }
        
        try:
            await self.es_client.indices.put_template(
                name=template_name,
                body=template_body
            )
            self.logger.info(f"创建索引模板: {template_name}")
        except Exception as e:
            self.logger.error(f"创建索引模板失败: {e}")
    
    async def get_indices_info(self) -> Dict[str, Any]:
        """获取索引信息"""
        try:
            index_pattern = f"{self.tenant_id}_messages_*"
            response = await self.es_client.cat.indices(
                index=index_pattern,
                format="json",
                h="index,docs.count,store.size"
            )
            
            return {
                "total_indices": len(response),
                "indices_details": response
            }
        except Exception:
            return {}