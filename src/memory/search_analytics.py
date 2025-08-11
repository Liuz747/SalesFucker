"""
消息搜索和分析模块
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from elasticsearch import AsyncElasticsearch

from .models import ConversationMessage, MessageType
from src.utils import get_component_logger


class SearchAnalytics:
    """消息搜索和分析引擎"""
    
    def __init__(self, tenant_id: str, es_client: AsyncElasticsearch):
        self.tenant_id = tenant_id
        self.es_client = es_client
        self.logger = get_component_logger(__name__, tenant_id)
        
        # 统计计数器
        self._stats = {
            "search_queries": 0,
            "messages_retrieved": 0,
            "errors": 0
        }
    
    async def search_messages(
        self,
        assistant_id: str,
        device_id: str,
        customer_id: Optional[str] = None,
        query_text: Optional[str] = None,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        message_types: Optional[List[MessageType]] = None,
        limit: int = 20
    ) -> List[ConversationMessage]:
        """
        智能消息搜索
        
        支持:
        - 全文搜索
        - 客户筛选
        - 时间范围
        - 消息类型过滤
        """
        try:
            # 构建复合查询 - 强制数据隔离防止跨助理污染
            must_clauses = [
                {"term": {"tenant_id": self.tenant_id}},
                {"term": {"assistant_id": assistant_id}},
                {"term": {"device_id": device_id}}
            ]
            
            if customer_id:
                must_clauses.append({"term": {"customer_id": customer_id}})
            
            if query_text:
                must_clauses.append({
                    "multi_match": {
                        "query": query_text,
                        "fields": ["content", "metadata.summary"],
                        "type": "best_fields"
                    }
                })
            
            if date_range:
                start_date, end_date = date_range
                must_clauses.append({
                    "range": {
                        "timestamp": {
                            "gte": start_date.isoformat(),
                            "lte": end_date.isoformat()
                        }
                    }
                })
            
            if message_types:
                type_values = [mt.value for mt in message_types]
                must_clauses.append({"terms": {"message_type": type_values}})
            
            query = {"bool": {"must": must_clauses}}
            
            # 执行搜索 - 跨所有消息索引
            index_pattern = f"{self.tenant_id}_messages_*"
            response = await self.es_client.search(
                index=index_pattern,
                body={
                    "query": query,
                    "sort": [{"timestamp": {"order": "desc"}}],
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
                        self.logger.warning(f"搜索结果解析失败: {e}")
            
            self._stats["search_queries"] += 1
            self._stats["messages_retrieved"] += len(messages)
            return messages
            
        except Exception as e:
            self._stats["errors"] += 1
            self.logger.error(f"消息搜索失败: {e}")
            return []
    
    async def get_customer_message_stats(
        self,
        assistant_id: str,
        device_id: str,
        customer_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取客户消息统计
        
        提供客户行为分析数据:
        - 消息数量统计
        - 类型分布
        - 活跃时间分析
        - 情感趋势
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            query = {
                "bool": {
                    "must": [
                        {"term": {"tenant_id": self.tenant_id}},
                        {"term": {"assistant_id": assistant_id}},
                        {"term": {"device_id": device_id}},
                        {"term": {"customer_id": customer_id}},
                        {"range": {"timestamp": {"gte": start_date.isoformat()}}}
                    ]
                }
            }
            
            # 构建聚合查询
            aggs = {
                "message_types": {
                    "terms": {"field": "message_type"}
                },
                "daily_activity": {
                    "date_histogram": {
                        "field": "timestamp",
                        "calendar_interval": "day"
                    }
                },
                "avg_sentiment": {
                    "avg": {"field": "sentiment_score"}
                },
                "total_tokens": {
                    "sum": {"field": "tokens_used"}
                }
            }
            
            index_pattern = f"{self.tenant_id}_messages_*"
            response = await self.es_client.search(
                index=index_pattern,
                body={
                    "query": query,
                    "aggs": aggs,
                    "size": 0
                },
                ignore=[404]
            )
            
            stats = {
                "customer_id": customer_id,
                "period_days": days,
                "total_messages": response["hits"]["total"]["value"],
                "message_type_distribution": {},
                "daily_activity": [],
                "average_sentiment": None,
                "total_tokens_used": 0
            }
            
            # 处理聚合结果
            if "aggregations" in response:
                aggs_data = response["aggregations"]
                
                # 消息类型分布
                for bucket in aggs_data.get("message_types", {}).get("buckets", []):
                    stats["message_type_distribution"][bucket["key"]] = bucket["doc_count"]
                
                # 每日活动
                for bucket in aggs_data.get("daily_activity", {}).get("buckets", []):
                    stats["daily_activity"].append({
                        "date": bucket["key_as_string"],
                        "message_count": bucket["doc_count"]
                    })
                
                # 平均情感分数
                if "avg_sentiment" in aggs_data and aggs_data["avg_sentiment"]["value"]:
                    stats["average_sentiment"] = aggs_data["avg_sentiment"]["value"]
                
                # 总token使用量
                if "total_tokens" in aggs_data and aggs_data["total_tokens"]["value"]:
                    stats["total_tokens_used"] = int(aggs_data["total_tokens"]["value"])
            
            return stats
            
        except Exception as e:
            self._stats["errors"] += 1
            self.logger.error(f"客户统计查询失败 {customer_id}: {e}")
            return {}
    
    async def delete_old_messages(self, days_to_keep: int = 365) -> int:
        """
        清理旧消息数据
        
        根据数据保留策略删除过期消息
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            query = {
                "bool": {
                    "must": [
                        {"term": {"tenant_id": self.tenant_id}},
                        {"range": {"timestamp": {"lt": cutoff_date.isoformat()}}}
                    ]
                }
            }
            
            index_pattern = f"{self.tenant_id}_messages_*"
            response = await self.es_client.delete_by_query(
                index=index_pattern,
                body={"query": query},
                wait_for_completion=True
            )
            
            deleted_count = response.get("deleted", 0)
            self.logger.info(f"清理旧消息完成: {deleted_count}条")
            return deleted_count
            
        except Exception as e:
            self._stats["errors"] += 1
            self.logger.error(f"消息清理失败: {e}")
            return 0
    
    def get_stats(self) -> dict:
        """获取搜索统计"""
        return self._stats.copy()