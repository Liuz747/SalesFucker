"""
Product Expert Agent

AI-powered product recommendation engine for beauty consultations.
Provides expert product knowledge and personalized recommendations.
"""

import asyncio
from typing import Dict, Any

from utils import get_current_datetime
from ..base import BaseAgent


class ProductExpertAgent(BaseAgent):
    """
    产品专家智能体
    
    提供专业的美妆产品推荐和咨询服务。
    使用模块化架构，结合RAG和降级系统提供个性化的产品建议。
    """
    
    def __init__(self):
        # MAS架构：所有智能体都具备LLM能力，自动使用产品推荐优化配置
        super().__init__()
        
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
    
    
    async def process_conversation(self, state: dict) -> dict:
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
            
            customer_input = state.get("customer_input", "")
            customer_profile = state.get("customer_profile", {})
            customer_history = state.get('customer_history', [])
            
            # 基于情感与意图综合分析结果生成需求画像
            # 注意：intent_analysis 现在由 SentimentAnalysisAgent 统一提供
            intent_analysis = state.get("intent_analysis", {}) or {}
            needs_analysis = await self.needs_analyzer.analyze_customer_needs(
                customer_input, customer_profile, intent_analysis
            )
            
            # 生成产品推荐
            product_recommendations = await self._generate_product_recommendations(
                customer_input, customer_profile, customer_history, needs_analysis
            )
            
            # 更新对话状态
            state.setdefault("agent_responses", {})[self.agent_id] = {
                "product_recommendations": product_recommendations,
                "needs_analysis": needs_analysis,
                "processing_complete": True
            }
            state.setdefault("active_agents", []).append(self.agent_id)

            return state
            
        except Exception as e:
            self.logger.error(f"Agent processing failed: {e}", exc_info=True)
            
            # 使用协调器设置降级推荐
            fallback_response = self.recommendation_coordinator.formatter.create_fallback_response(str(e))
            state.setdefault("agent_responses", {})[self.agent_id] = {
                "product_recommendations": fallback_response,
                "error": str(e),
                "agent_id": self.agent_id
            }
            
            return state
    
    async def _generate_product_recommendations(
        self, 
        customer_input: str, 
        customer_profile: dict,
        customer_history: list[dict] = None,
        needs_analysis: dict = None
    ) -> dict:
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
                "agent_id": self.agent_id
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
                "error": str(e)
            }