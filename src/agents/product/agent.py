"""
Product Expert Agent

AI-powered product recommendation engine for beauty consultations.
Provides expert product knowledge and personalized recommendations.
"""

from typing import Dict, Any, List
import asyncio
from ..base import BaseAgent, AgentMessage, ThreadState
from src.utils import get_current_datetime, get_processing_time_ms
from src.llm.intelligent_router import RoutingStrategy

# 导入模块化组件
from .recommendation_coordinator import RecommendationCoordinator
from .needs_analyzer import CustomerNeedsAnalyzer
from .product_knowledge import ProductKnowledgeManager


class ProductExpertAgent(BaseAgent):
    """
    产品专家智能体
    
    提供专业的美妆产品推荐和咨询服务。
    使用模块化架构，结合RAG和降级系统提供个性化的产品建议。
    
    架构组件:
    - RecommendationCoordinator: 推荐策略协调器
    - CustomerNeedsAnalyzer: 客户需求分析器  
    - ProductKnowledgeManager: 产品知识管理器
    - RAGRecommendationEngine: RAG增强推荐引擎
    - FallbackRecommendationSystem: 降级推荐系统
    - RecommendationFormatter: 推荐结果格式化器
    """
    
    def __init__(self, tenant_id: str):
        # MAS架构：所有智能体都具备LLM能力，自动使用产品推荐优化配置
        super().__init__(
            agent_id=f"product_expert_{tenant_id}",
            tenant_id=tenant_id,
            routing_strategy=RoutingStrategy.PERFORMANCE_FIRST  # 产品推荐需要高质量响应
        )
        
        # 初始化模块化组件
        self.recommendation_coordinator = RecommendationCoordinator(tenant_id, self.agent_id)
        self.needs_analyzer = CustomerNeedsAnalyzer(tenant_id)
        self.knowledge_manager = ProductKnowledgeManager(tenant_id)
        
        # 系统初始化状态
        self._initialized = False
        
        self.logger.info(f"产品专家智能体初始化完成: {self.agent_id}，模块化架构，MAS自动LLM优化")
    
    async def _ensure_initialized(self) -> None:
        """确保所有组件已初始化"""
        if not self._initialized:
            try:
                await asyncio.gather(
                    self.recommendation_coordinator.initialize(),
                    self.needs_analyzer.initialize(),
                    return_exceptions=True
                )
                self._initialized = True
                self.logger.info("所有组件初始化完成")
            except Exception as e:
                self.logger.warning(f"组件初始化部分失败: {e}")
                self._initialized = True  # 继续使用降级功能
    
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """
        处理产品咨询消息
        
        分析客户需求并提供产品推荐。
        
        参数:
            message: 包含产品咨询的消息
            
        返回:
            AgentMessage: 包含产品推荐的响应
        """
        try:
            await self._ensure_initialized()
            
            customer_input = message.payload.get("text", "")
            customer_profile = message.context.get("customer_profile", {})
            customer_history = message.context.get("customer_history", [])
            
            # 分析客户需求
            needs_analysis = await self.needs_analyzer.analyze_customer_needs(
                customer_input, customer_profile
            )
            
            # 生成推荐
            product_recommendations = await self._generate_product_recommendations(
                customer_input, customer_profile, customer_history, needs_analysis
            )
            
            response_payload = {
                "product_recommendations": product_recommendations,
                "needs_analysis": needs_analysis,
                "processing_agent": self.agent_id,
                "recommendation_timestamp": get_current_datetime().isoformat()
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
            
            # 使用协调器创建降级响应
            fallback_recommendations = self.recommendation_coordinator.formatter.create_fallback_response(str(e))
            
            return await self.send_message(
                recipient=message.sender,
                message_type="response",
                payload={"error": error_info, "product_recommendations": fallback_recommendations},
                context=message.context
            )
    
    async def process_conversation(self, state: ThreadState) -> ThreadState:
        """
        处理对话状态中的产品推荐
        
        在LangGraph工作流中生成产品推荐，更新对话状态。
        
        参数:
            state: 当前对话状态
            
        返回:
            ThreadState: 更新后的对话状态
        """
        start_time = get_current_datetime()
        
        try:
            await self._ensure_initialized()
            
            customer_input = state.customer_input
            customer_profile = state.customer_profile
            customer_history = getattr(state, 'customer_history', [])
            
            # 分析客户需求和偏好
            needs_analysis = await self.needs_analyzer.analyze_customer_needs(
                customer_input, customer_profile, state.intent_analysis
            )
            
            # 生成产品推荐
            product_recommendations = await self._generate_product_recommendations(
                customer_input, customer_profile, customer_history, needs_analysis
            )
            
            # 更新对话状态
            state.agent_responses[self.agent_id] = {
                "product_recommendations": product_recommendations,
                "needs_analysis": needs_analysis,
                "processing_complete": True
            }
            state.active_agents.append(self.agent_id)
            
            # 更新处理统计
            processing_time = get_processing_time_ms(start_time)
            self.update_stats(processing_time)
            
            return state
            
        except Exception as e:
            await self.handle_error(e, {"thread_id": state.thread_id})
            
            # 使用协调器设置降级推荐
            fallback_response = self.recommendation_coordinator.formatter.create_fallback_response(str(e))
            state.agent_responses[self.agent_id] = {
                "product_recommendations": fallback_response,
                "error": str(e),
                "agent_id": self.agent_id
            }
            
            return state
    
    async def _generate_product_recommendations(
        self, 
        customer_input: str, 
        customer_profile: Dict[str, Any],
        customer_history: List[Dict[str, Any]] = None,
        needs_analysis: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        生成产品推荐
        
        使用模块化协调器智能选择最佳推荐策略
        
        参数:
            customer_input: 客户输入
            customer_profile: 客户档案
            customer_history: 客户历史
            needs_analysis: 需求分析结果
            
        返回:
            Dict[str, Any]: 产品推荐结果
        """
        try:
            # 判断是否为简单查询，使用快速推荐
            if self.knowledge_manager.is_simple_query(customer_input, needs_analysis):
                self.logger.debug("使用快速推荐路径")
                return await self.recommendation_coordinator.get_fast_recommendations(
                    customer_input, customer_profile, needs_analysis
                )
            
            # 使用完整推荐流程
            self.logger.debug("使用完整推荐路径")
            return await self.recommendation_coordinator.generate_recommendations(
                customer_input, customer_profile, needs_analysis, customer_history
            )
            
        except Exception as e:
            self.logger.error(f"产品推荐生成失败: {e}")
            return self.recommendation_coordinator.formatter.create_fallback_response(str(e))
    
    async def search_products(self, query: str, top_k: int = 10) -> Dict[str, Any]:
        """
        产品搜索
        
        参数:
            query: 搜索查询
            top_k: 返回结果数量
            
        返回:
            Dict[str, Any]: 搜索结果
        """
        await self._ensure_initialized()
        return await self.recommendation_coordinator.search_products(query, top_k)
    
    async def get_product_metrics(self) -> Dict[str, Any]:
        """
        获取产品推荐性能指标
        
        返回:
            Dict[str, Any]: 性能指标信息
        """
        try:
            await self._ensure_initialized()
            
            # 获取基础统计
            base_stats = {
                "total_recommendations": self.processing_stats["messages_processed"],
                "error_rate": self.processing_stats["errors"] / max(1, self.processing_stats["messages_processed"]) * 100,
                "average_processing_time": self.processing_stats["average_response_time"],
                "last_activity": self.processing_stats["last_activity"],
                "agent_id": self.agent_id,
                "tenant_id": self.tenant_id
            }
            
            # 获取综合统计
            comprehensive_stats = await self.recommendation_coordinator.get_comprehensive_stats()
            
            return {
                **base_stats,
                "system_details": comprehensive_stats
            }
            
        except Exception as e:
            self.logger.error(f"获取产品指标失败: {e}")
            return {
                "total_recommendations": self.processing_stats.get("messages_processed", 0),
                "error_rate": 0,
                "average_processing_time": 0,
                "last_activity": None,
                "agent_id": self.agent_id,
                "tenant_id": self.tenant_id,
                "error": str(e)
            }