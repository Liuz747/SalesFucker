"""
Memory Agent

Customer profile management and conversation context persistence.
Handles customer data storage, retrieval, and profile updates.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json

from ..core import BaseAgent, AgentMessage, ConversationState
from src.utils import get_current_datetime, get_processing_time_ms


class MemoryAgent(BaseAgent):
    """
    记忆管理智能体
    
    负责客户档案管理和对话上下文持久化。
    存储客户偏好、购买历史和对话记录。
    """
    
    def __init__(self, tenant_id: str):
        super().__init__(f"memory_agent_{tenant_id}", tenant_id)
        
        # 优化的内存存储结构
        self.customer_profiles: Dict[str, Dict[str, Any]] = {}
        self.conversation_history: Dict[str, List[Dict[str, Any]]] = {}
        
        # 性能优化组件
        self._profile_cache = {}  # LRU缓存
        self._cache_max_size = 1000
        self._executor = ThreadPoolExecutor(max_workers=4)  # 异步I/O处理
        
        # 索引结构 - 快速查询
        self._customer_index = {}  # 客户ID到最后更新时间映射
        self._profile_locks = {}  # 并发控制
        
        self.logger.info(f"记忆管理智能体初始化完成: {self.agent_id}，启用性能优化")
    
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """
        处理记忆管理消息
        
        存储或检索客户信息。
        
        参数:
            message: 包含记忆操作请求的消息
            
        返回:
            AgentMessage: 包含记忆操作结果的响应
        """
        try:
            operation = message.payload.get("operation", "retrieve")
            customer_id = message.payload.get("customer_id")
            
            if operation == "store":
                result = await self._store_customer_data(message.payload)
            elif operation == "retrieve":
                result = await self._retrieve_customer_data(customer_id)
            elif operation == "update":
                result = await self._update_customer_profile(message.payload)
            else:
                result = {"error": f"Unknown operation: {operation}"}
            
            response_payload = {
                "memory_operation_result": result,
                "processing_agent": self.agent_id,
                "operation_timestamp": get_current_datetime().isoformat()
            }
            
            return await self.send_message(
                recipient=message.sender,
                message_type="response",
                payload=response_payload,
                context=message.context
            )
            
        except Exception as e:
            error_context = {
                "message_id": message.message_id,
                "sender": message.sender
            }
            error_info = await self.handle_error(e, error_context)
            
            return await self.send_message(
                recipient=message.sender,
                message_type="response",
                payload={"error": error_info, "memory_operation_result": {"success": False}},
                context=message.context
            )
    
    async def process_conversation(self, state: ConversationState) -> ConversationState:
        """
        处理对话状态中的记忆管理
        
        更新客户档案和对话历史。
        
        参数:
            state: 当前对话状态
            
        返回:
            ConversationState: 更新后的对话状态
        """
        start_time = get_current_datetime()
        
        try:
            customer_id = state.customer_id
            
            # 检索现有客户档案
            if customer_id:
                existing_profile = await self._retrieve_customer_data(customer_id)
                if existing_profile.get("profile"):
                    state.customer_profile.update(existing_profile["profile"])
            
            # 更新客户档案信息
            profile_updates = self._extract_profile_updates(state)
            if profile_updates and customer_id:
                await self._update_customer_profile({
                    "customer_id": customer_id,
                    "updates": profile_updates
                })
                state.customer_profile.update(profile_updates)
            
            # 存储对话记录
            await self._store_conversation_record(state)
            
            # 更新对话状态
            state.agent_responses[self.agent_id] = {
                "memory_updated": True,
                "profile_updates": profile_updates,
                "processing_complete": True
            }
            state.active_agents.append(self.agent_id)
            
            # 更新处理统计
            processing_time = get_processing_time_ms(start_time)
            self.update_stats(processing_time)
            
            return state
            
        except Exception as e:
            await self.handle_error(e, {"conversation_id": state.conversation_id})
            
            # 设置错误状态但不影响对话继续
            state.agent_responses[self.agent_id] = {
                "memory_updated": False,
                "error": str(e),
                "fallback": True,
                "agent_id": self.agent_id
            }
            
            return state
    
    async def _store_customer_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        存储客户数据
        
        参数:
            payload: 包含客户数据的载荷
            
        返回:
            Dict[str, Any]: 存储操作结果
        """
        try:
            customer_id = payload.get("customer_id")
            customer_data = payload.get("customer_data", {})
            
            if not customer_id:
                return {"success": False, "error": "Customer ID required"}
            
            # 简化存储 (生产环境中使用Elasticsearch)
            self.customer_profiles[customer_id] = {
                "customer_id": customer_id,
                "profile": customer_data,
                "created_at": get_current_datetime().isoformat(),
                "updated_at": get_current_datetime().isoformat(),
                "tenant_id": self.tenant_id
            }
            
            self.logger.info(f"存储客户数据: {customer_id}")
            
            return {
                "success": True,
                "customer_id": customer_id,
                "stored_fields": list(customer_data.keys())
            }
            
        except Exception as e:
            self.logger.error(f"客户数据存储失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _retrieve_customer_data(self, customer_id: str) -> Dict[str, Any]:
        """
        优化的客户数据检索
        
        使用缓存和异步I/O提升性能
        
        参数:
            customer_id: 客户ID
            
        返回:
            Dict[str, Any]: 客户数据
        """
        try:
            if not customer_id:
                return {"success": False, "error": "Customer ID required"}
            
            # 1. 检查缓存 - O(1)性能
            if customer_id in self._profile_cache:
                cached_data = self._profile_cache[customer_id]
                self.logger.debug(f"缓存命中: {customer_id}")
                return cached_data
            
            # 2. 异步检索数据
            profile_data = await self._async_get_profile(customer_id)
            
            if profile_data:
                result = {
                    "success": True,
                    "customer_id": customer_id,
                    "profile": profile_data["profile"],
                    "last_updated": profile_data.get("updated_at"),
                    "conversation_history": self.conversation_history.get(customer_id, [])
                }
            else:
                result = {
                    "success": True,
                    "customer_id": customer_id,
                    "profile": {},
                    "conversation_history": [],
                    "new_customer": True
                }
            
            # 3. 更新缓存
            self._update_cache(customer_id, result)
            
            return result
                
        except Exception as e:
            self.logger.error(f"客户数据检索失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _async_get_profile(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """异步获取客户档案"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, 
            lambda: self.customer_profiles.get(customer_id)
        )
    
    def _update_cache(self, customer_id: str, data: Dict[str, Any]):
        """更新LRU缓存"""
        if len(self._profile_cache) >= self._cache_max_size:
            # 移除最旧的条目
            oldest_key = next(iter(self._profile_cache))
            del self._profile_cache[oldest_key]
        
        self._profile_cache[customer_id] = data
    
    async def _update_customer_profile(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新客户档案
        
        参数:
            payload: 包含更新数据的载荷
            
        返回:
            Dict[str, Any]: 更新操作结果
        """
        try:
            customer_id = payload.get("customer_id")
            updates = payload.get("updates", {})
            
            if not customer_id:
                return {"success": False, "error": "Customer ID required"}
            
            # 获取现有档案或创建新档案
            existing_profile = self.customer_profiles.get(customer_id, {
                "customer_id": customer_id,
                "profile": {},
                "created_at": get_current_datetime().isoformat(),
                "tenant_id": self.tenant_id
            })
            
            # 更新档案数据
            existing_profile["profile"].update(updates)
            existing_profile["updated_at"] = get_current_datetime().isoformat()
            
            # 存储更新后的档案
            self.customer_profiles[customer_id] = existing_profile
            
            self.logger.info(f"更新客户档案: {customer_id}, 字段: {list(updates.keys())}")
            
            return {
                "success": True,
                "customer_id": customer_id,
                "updated_fields": list(updates.keys()),
                "profile": existing_profile["profile"]
            }
            
        except Exception as e:
            self.logger.error(f"客户档案更新失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _store_conversation_record(self, state: ConversationState) -> Dict[str, Any]:
        """
        存储对话记录
        
        参数:
            state: 对话状态
            
        返回:
            Dict[str, Any]: 存储结果
        """
        try:
            customer_id = state.customer_id
            if not customer_id:
                return {"success": False, "error": "No customer ID"}
            
            # 构建对话记录
            conversation_record = {
                "conversation_id": state.conversation_id,
                "timestamp": get_current_datetime().isoformat(),
                "customer_input": state.customer_input,
                "final_response": state.final_response,
                "sentiment": state.sentiment_analysis.get("sentiment", "neutral") if state.sentiment_analysis else "neutral",
                "intent": state.intent_analysis.get("intent", "unknown") if state.intent_analysis else "unknown",
                "active_agents": state.active_agents.copy(),
                "tenant_id": self.tenant_id
            }
            
            # 存储对话记录
            if customer_id not in self.conversation_history:
                self.conversation_history[customer_id] = []
            
            self.conversation_history[customer_id].append(conversation_record)
            
            # 保持最近50条对话记录
            if len(self.conversation_history[customer_id]) > 50:
                self.conversation_history[customer_id] = self.conversation_history[customer_id][-50:]
            
            return {"success": True, "record_stored": True}
            
        except Exception as e:
            self.logger.error(f"对话记录存储失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _extract_profile_updates(self, state: ConversationState) -> Dict[str, Any]:
        """
        从对话状态中提取客户档案更新
        
        参数:
            state: 对话状态
            
        返回:
            Dict[str, Any]: 档案更新数据
        """
        updates = {}
        
        # 从意图分析中提取信息
        if state.intent_analysis:
            intent_data = state.intent_analysis
            if intent_data.get("category") and intent_data["category"] != "general":
                updates["preferred_category"] = intent_data["category"]
            
            if intent_data.get("urgency"):
                updates["last_urgency_level"] = intent_data["urgency"]
        
        # 从情感分析中提取信息
        if state.sentiment_analysis:
            sentiment_data = state.sentiment_analysis
            if sentiment_data.get("sentiment"):
                updates["last_sentiment"] = sentiment_data["sentiment"]
        
        # 从合规结果中提取偏好 (如果有特殊需求)
        if state.compliance_result:
            compliance_data = state.compliance_result
            if compliance_data.get("status") == "flagged":
                updates["requires_careful_handling"] = True
        
        # 从客户输入中推断偏好 (简化版本)
        if state.customer_input:
            input_lower = state.customer_input.lower()
            
            # 检测皮肤类型偏好
            if "oily" in input_lower or "greasy" in input_lower:
                updates["inferred_skin_type"] = "oily"
            elif "dry" in input_lower or "dehydrated" in input_lower:
                updates["inferred_skin_type"] = "dry"
            elif "sensitive" in input_lower:
                updates["inferred_skin_type"] = "sensitive"
            
            # 检测预算偏好
            if any(word in input_lower for word in ["expensive", "luxury", "premium"]):
                updates["budget_preference"] = "high"
            elif any(word in input_lower for word in ["cheap", "budget", "affordable"]):
                updates["budget_preference"] = "low"
        
        # 添加最后交互时间
        if updates:
            updates["last_interaction"] = get_current_datetime().isoformat()
        
        return updates
    
    def get_memory_metrics(self) -> Dict[str, Any]:
        """
        获取记忆管理性能指标
        
        返回:
            Dict[str, Any]: 性能指标信息
        """
        total_customers = len(self.customer_profiles)
        total_conversations = sum(len(history) for history in self.conversation_history.values())
        
        return {
            "total_operations": self.processing_stats["messages_processed"],
            "error_rate": self.processing_stats["errors"] / max(1, self.processing_stats["messages_processed"]) * 100,
            "average_processing_time": self.processing_stats["average_response_time"],
            "last_activity": self.processing_stats["last_activity"],
            "total_customers": total_customers,
            "total_conversations": total_conversations,
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id
        }