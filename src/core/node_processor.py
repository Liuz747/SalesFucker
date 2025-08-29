"""
节点处理器模块

该模块负责各个智能体节点的处理逻辑和错误降级策略。
使用通用工具消除重复代码，提高可维护性。

核心功能:
- 通用智能体节点处理
- 标准化错误处理和降级策略
- 节点状态管理
- 智能体协调调用
"""

import asyncio
from typing import Dict, Any, Callable, Optional

from src.agents.base import ThreadState, agent_registry
from utils import get_component_logger
from libs.constants import StatusConstants, WorkflowConstants


class NodeProcessor:
    """
    节点处理器
    
    属性:
        tenant_id: 租户标识符
        node_mapping: 节点名称到智能体ID的映射
        logger: 日志记录器
        fallback_handlers: 降级处理器映射
    """
    
    def __init__(self, tenant_id: str, node_mapping: Dict[str, str]):
        """
        初始化节点处理器
        
        参数:
            tenant_id: 租户标识符
            node_mapping: 节点到智能体的映射关系
        """
        self.tenant_id = tenant_id
        self.node_mapping = node_mapping
        self.logger = get_component_logger(__name__, tenant_id)
        
        # 定义各节点的降级处理器
        self.fallback_handlers = self._init_fallback_handlers()
    
    def _init_fallback_handlers(self) -> Dict[str, Callable]:
        """
        初始化降级处理器映射
        
        为每个节点类型定义特定的降级处理逻辑。
        
        返回:
            Dict[str, Callable]: 节点名称到降级处理器的映射
        """
        return {
            WorkflowConstants.COMPLIANCE_NODE: self._compliance_fallback,
            WorkflowConstants.SENTIMENT_NODE: self._sentiment_fallback,
            WorkflowConstants.INTENT_NODE: self._intent_fallback,
            WorkflowConstants.STRATEGY_NODE: self._strategy_fallback,
            WorkflowConstants.SALES_NODE: self._sales_fallback,
            WorkflowConstants.PRODUCT_NODE: self._product_fallback,
            WorkflowConstants.MEMORY_NODE: self._memory_fallback,
        }
    
    async def _process_agent_node(self, state: dict, node_name: str) -> dict:
        """
        通用智能体节点处理方法
        
        统一处理智能体调用、错误处理和降级策略。
        
        参数:
            state: 当前对话状态字典
            node_name: 节点名称
            
        返回:
            dict: 更新后的状态字典
        """
        agent_id = self.node_mapping.get(node_name)
        if not agent_id:
            self.logger.error(f"节点映射不存在: {node_name}")
            return self._apply_fallback(state, node_name, None)
        
        agent = agent_registry.get_agent(agent_id)
        if not agent:
            self.logger.warning(f"智能体未找到: {agent_id}")
            return self._apply_fallback(state, node_name, None)
        
        try:
            conversation_state = ThreadState(**state)
            result_state = await agent.process_conversation(conversation_state)
            
            self.logger.debug(f"节点处理完成: {node_name} ({agent_id})")
            return result_state.model_dump()
            
        except Exception as e:
            self.logger.error(f"节点 {node_name} 处理错误: {e}", exc_info=True)
            return self._apply_fallback(state, node_name, e)
    
    def _apply_fallback(self, state: dict, node_name: str, error: Optional[Exception]) -> dict:
        """
        应用降级处理策略
        
        参数:
            state: 当前状态
            node_name: 节点名称
            error: 可选的错误信息
            
        返回:
            dict: 应用降级后的状态
        """
        fallback_handler = self.fallback_handlers.get(node_name)
        if fallback_handler:
            return fallback_handler(state, error)
        else:
            # 默认降级处理
            state["error_state"] = f"{node_name}_unavailable"
            return state
    
    # ============ 具体节点处理方法 ============
    
    async def compliance_node(self, state: dict) -> dict:
        """合规审查节点"""
        return await self._process_agent_node(state, WorkflowConstants.COMPLIANCE_NODE)
    
    async def sentiment_node(self, state: dict) -> dict:
        """情感分析节点"""
        return await self._process_agent_node(state, WorkflowConstants.SENTIMENT_NODE)
    
    async def intent_node(self, state: dict) -> dict:
        """意图分析节点"""
        return await self._process_agent_node(state, WorkflowConstants.INTENT_NODE)
    
    async def strategy_node(self, state: dict) -> dict:
        """市场策略节点"""
        return await self._process_agent_node(state, WorkflowConstants.STRATEGY_NODE)
    
    async def sales_node(self, state: dict) -> dict:
        """销售智能体节点"""
        return await self._process_agent_node(state, WorkflowConstants.SALES_NODE)
    
    async def product_node(self, state: dict) -> dict:
        """产品专家节点"""
        return await self._process_agent_node(state, WorkflowConstants.PRODUCT_NODE)
    
    async def memory_node(self, state: dict) -> dict:
        """记忆管理节点"""
        return await self._process_agent_node(state, WorkflowConstants.MEMORY_NODE)
    
    
    # ============ 降级处理器 ============
    # 每个降级处理器专注于特定节点的降级逻辑
    
    def _compliance_fallback(self, state: dict, error: Optional[Exception]) -> dict:
        """合规审查降级处理"""
        state["compliance_result"] = {
            "status": StatusConstants.APPROVED,
            "fallback": True,
            "message": "合规检查系统暂时不可用，默认通过"
        }
        return state
    
    def _sentiment_fallback(self, state: dict, error: Optional[Exception]) -> dict:
        """情感分析降级处理"""
        state["sentiment_analysis"] = {
            "sentiment": "neutral",
            "score": 0.0,
            "confidence": 0.5,
            "fallback": True
        }
        return state
    
    def _intent_fallback(self, state: dict, error: Optional[Exception]) -> dict:
        """意图分析降级处理"""
        state["intent_analysis"] = {
            "intent": "general_inquiry",
            "confidence": 0.5,
            "category": "unknown",
            "fallback": True
        }
        return state
    
    def _strategy_fallback(self, state: dict, error: Optional[Exception]) -> dict:
        """市场策略降级处理"""
        # 根据客户输入尝试简单的策略判断
        customer_input = state.get("customer_input", "").lower()
        
        if any(word in customer_input for word in ["luxury", "premium", "expensive"]):
            strategy = WorkflowConstants.PREMIUM_STRATEGY
        elif any(word in customer_input for word in ["budget", "cheap", "affordable"]):
            strategy = WorkflowConstants.BUDGET_STRATEGY
        elif any(word in customer_input for word in ["young", "trendy", "cool"]):
            strategy = WorkflowConstants.YOUTH_STRATEGY
        else:
            strategy = WorkflowConstants.PREMIUM_STRATEGY  # 默认策略
        
        state["market_strategy"] = {
            "strategy": strategy,
            "confidence": 0.6,
            "fallback": True
        }
        return state
    
    def _sales_fallback(self, state: dict, error: Optional[Exception]) -> dict:
        """销售智能体降级处理"""
        agent_id = self.node_mapping.get(WorkflowConstants.SALES_NODE, "sales_agent")
        
        state["agent_responses"] = state.get("agent_responses", {})
        state["agent_responses"][agent_id] = {
            "response": "感谢您的咨询！我很乐意为您推荐合适的美容产品。请告诉我您具体的需求？",
            "fallback": True,
            "timestamp": state.get("timestamp")
        }
        return state
    
    def _product_fallback(self, state: dict, error: Optional[Exception]) -> dict:
        """产品专家降级处理"""
        state["product_recommendations"] = {
            "status": "unavailable",
            "message": "产品推荐系统暂时不可用",
            "fallback": True
        }
        return state
    
    def _memory_fallback(self, state: dict, error: Optional[Exception]) -> dict:
        """记忆管理降级处理"""
        state["memory_update"] = {
            "status": StatusConstants.FAILED,
            "message": "记忆系统暂时不可用",
            "fallback": True
        }
        return state
    
    
    # ============ 特殊处理节点 ============
    
    async def blocked_completion_node(self, state: dict) -> dict:
        """
        合规阻止完成节点 - 处理被合规系统阻止的内容
        """
        compliance_result = state.get("compliance_result", {})
        state["final_response"] = compliance_result.get(
            "user_message", 
            "很抱歉，您的请求涉及到敏感内容，无法继续处理。"
        )
        state["processing_complete"] = True
        state["blocked_by_compliance"] = True
        return state
    
    # ============ 并行处理节点 ============
    
    async def parallel_analysis_node(self, state: dict) -> dict:
        """
        并行分析节点 - 同时处理情感和意图分析
        
        性能优化：将原本串行的情感分析和意图分析改为并行处理
        预期延迟减少：40-50%
        """
        try:
            # 并行执行情感分析和意图分析
            sentiment_task = self.sentiment_node(state.copy())
            intent_task = self.intent_node(state.copy())
            
            # 等待两个任务完成
            sentiment_result, intent_result = await asyncio.gather(
                sentiment_task,
                intent_task,
                return_exceptions=True
            )
            
            # 合并结果
            if isinstance(sentiment_result, Exception):
                self.logger.error(f"情感分析并行处理失败: {sentiment_result}")
                state = self._sentiment_fallback(state, sentiment_result)
            else:
                state.update({
                    "sentiment_analysis": sentiment_result.get("sentiment_analysis"),
                    "agent_responses": {
                        **state.get("agent_responses", {}),
                        **sentiment_result.get("agent_responses", {})
                    }
                })
            
            if isinstance(intent_result, Exception):
                self.logger.error(f"意图分析并行处理失败: {intent_result}")
                state = self._intent_fallback(state, intent_result)
            else:
                state.update({
                    "intent_analysis": intent_result.get("intent_analysis"),
                    "agent_responses": {
                        **state.get("agent_responses", {}),
                        **intent_result.get("agent_responses", {})
                    }
                })
            
            self.logger.debug("并行分析节点处理完成")
            return state
            
        except Exception as e:
            self.logger.error(f"并行分析节点处理失败: {e}")
            # 降级到串行处理
            state = await self.sentiment_node(state)
            state = await self.intent_node(state)
            return state
    
    async def parallel_completion_node(self, state: dict) -> dict:
        """
        并行完成节点 - 同时处理产品推荐和记忆更新
        
        性能优化：产品推荐和记忆更新可以并行执行
        预期延迟减少：30-40%
        """
        try:
            # 并行执行产品推荐和记忆更新
            product_task = self.product_node(state.copy())
            memory_task = self.memory_node(state.copy())
            
            # 等待两个任务完成
            product_result, memory_result = await asyncio.gather(
                product_task,
                memory_task,
                return_exceptions=True
            )
            
            # 合并产品推荐结果
            if isinstance(product_result, Exception):
                self.logger.error(f"产品推荐并行处理失败: {product_result}")
                state = self._product_fallback(state, product_result)
            else:
                state.update({
                    "product_recommendations": product_result.get("product_recommendations"),
                    "agent_responses": {
                        **state.get("agent_responses", {}),
                        **product_result.get("agent_responses", {})
                    }
                })
            
            # 合并记忆更新结果
            if isinstance(memory_result, Exception):
                self.logger.error(f"记忆更新并行处理失败: {memory_result}")
                state = self._memory_fallback(state, memory_result)
            else:
                state.update({
                    "memory_update": memory_result.get("memory_update"),
                    "customer_profile": memory_result.get("customer_profile", state.get("customer_profile", {})),
                    "agent_responses": {
                        **state.get("agent_responses", {}),
                        **memory_result.get("agent_responses", {})
                    }
                })
            
            # 标记处理完成，因为这现在是最终节点
            state["processing_complete"] = True
            self.logger.debug("并行完成节点处理完成")
            return state
            
        except Exception as e:
            self.logger.error(f"并行完成节点处理失败: {e}")
            # 降级到串行处理
            state = await self.product_node(state)
            state = await self.memory_node(state)
            state["processing_complete"] = True
            return state
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        获取节点处理器性能指标
        
        返回:
            Dict[str, Any]: 性能统计信息
        """
        return {
            "tenant_id": self.tenant_id,
            "node_count": len(self.node_mapping),
            "fallback_handlers": len(self.fallback_handlers),
            "parallel_processing": {
                "enabled": True,
                "parallel_analysis": ["sentiment", "intent"],
                "parallel_completion": ["product", "memory"]
            },
            "performance_optimizations": [
                "async_parallel_processing",
                "graceful_fallback_strategies",
                "exception_handling_isolation",
                "result_merging_optimization"
            ]
        } 