"""
批量操作管理模块

提供高性能的批量读写操作，包括批量写入缓冲区管理。
优化大规模数据操作的性能和吞吐量。

核心功能:
- 批量Elasticsearch操作
- 写入缓冲区管理
- 异步批量写入任务
- 错误处理和重试机制
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from elasticsearch import AsyncElasticsearch
from utils import get_component_logger


class BatchOperationManager:
    """
    批量操作管理器
    
    负责管理所有批量数据库操作，包括读取和写入。
    实现写入缓冲区和定时刷新机制，优化性能。
    """
    
    def __init__(self, tenant_id: str, config):
        self.tenant_id = tenant_id
        self.config = config
        self.logger = get_component_logger(__name__, tenant_id)
        
        # Elasticsearch客户端
        self._es_client: Optional[AsyncElasticsearch] = None
        
        # 写入缓冲区
        self._write_buffer: List[Dict[str, Any]] = []
        
        # 批量写入任务
        self._batch_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # 统计信息
        self._batch_writes = 0
        self._elasticsearch_queries = 0
    
    async def initialize(self, es_client: AsyncElasticsearch):
        """初始化批量操作管理器"""
        self._es_client = es_client
        
        # 启动批量写入任务
        self._batch_task = asyncio.create_task(self._batch_write_worker())
        
        self.logger.info(f"批量操作管理器初始化完成: {self.tenant_id}")
    
    async def batch_get_from_elasticsearch(self, customer_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        从Elasticsearch批量获取客户档案
        
        Args:
            customer_ids: 客户ID列表
            
        Returns:
            客户档案字典 {customer_id: profile_data}
        """
        results = {}
        
        try:
            # 构建批量查询
            es_queries = []
            for customer_id in customer_ids:
                es_queries.append({
                    "_index": f"{self.tenant_id}_profiles",
                    "_id": customer_id
                })
            
            # 执行批量查询
            es_response = await self._es_client.mget(body={"docs": es_queries})
            
            # 处理结果
            for doc in es_response["docs"]:
                if doc.get("found"):
                    customer_id = doc["_id"]
                    profile = doc["_source"]
                    results[customer_id] = profile
            
            self._elasticsearch_queries += 1
            
        except Exception as e:
            self.logger.error(f"批量Elasticsearch查询失败: {e}")
        
        return results
    
    async def add_to_write_buffer(self, operation_type: str, customer_id: str, data: Dict[str, Any]):
        """
        添加操作到写入缓冲区
        
        Args:
            operation_type: 操作类型 (如 'update_profile')
            customer_id: 客户ID
            data: 要写入的数据
        """
        write_operation = {
            "operation": operation_type,
            "customer_id": customer_id,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self._write_buffer.append(write_operation)
        
        # 如果缓冲区满了，立即触发批量写入
        if len(self._write_buffer) >= self.config.batch_size:
            await self._flush_write_buffer()
    
    async def _batch_write_worker(self):
        """批量写入工作线程"""
        while not self._shutdown_event.is_set():
            try:
                # 等待写入间隔或关闭信号
                await asyncio.wait_for(
                    self._shutdown_event.wait(), 
                    timeout=self.config.flush_interval
                )
            except asyncio.TimeoutError:
                # 超时 - 执行批量写入
                if self._write_buffer:
                    await self._flush_write_buffer()
    
    async def _flush_write_buffer(self):
        """刷新写入缓冲区到Elasticsearch"""
        if not self._write_buffer:
            return
        
        operations = self._write_buffer.copy()
        self._write_buffer.clear()
        
        try:
            # 构建批量操作
            bulk_operations = []
            for op in operations:
                if op["operation"] == "update_profile":
                    bulk_operations.extend([
                        {
                            "update": {
                                "_index": f"{self.tenant_id}_profiles",
                                "_id": op["customer_id"]
                            }
                        },
                        {
                            "doc": op["data"],
                            "doc_as_upsert": True
                        }
                    ])
            
            if bulk_operations:
                response = await self._es_client.bulk(body=bulk_operations)
                
                if response.get("errors"):
                    error_count = len([item for item in response['items'] if 'error' in item])
                    self.logger.warning(f"批量写入部分失败: {error_count}条记录")
                
                self._batch_writes += 1
                self.logger.debug(f"批量写入完成: {len(operations)}条记录")
        
        except Exception as e:
            self.logger.error(f"批量写入失败: {e}")
            # 重新添加到缓冲区重试(只重试前10条)
            self._write_buffer.extend(operations[:10])
    
    async def force_flush(self):
        """强制刷新所有待写入数据"""
        await self._flush_write_buffer()
    
    def get_buffer_status(self) -> Dict[str, Any]:
        """获取缓冲区状态"""
        return {
            "pending_writes": len(self._write_buffer),
            "batch_size": self.config.batch_size,
            "flush_interval": self.config.flush_interval
        }
    
    def get_operation_stats(self) -> Dict[str, Any]:
        """获取操作统计信息"""
        return {
            "batch_writes": self._batch_writes,
            "elasticsearch_queries": self._elasticsearch_queries
        }
    
    async def shutdown(self):
        """关闭批量操作管理器"""
        # 停止批量写入任务
        self._shutdown_event.set()
        if self._batch_task:
            await self._batch_task
        
        # 刷新剩余的写入操作
        await self._flush_write_buffer()
        
        self.logger.info(f"批量操作管理器已关闭: {self.tenant_id}")
