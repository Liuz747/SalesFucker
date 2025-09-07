"""
推荐协调器
Recommendation Coordinator

统一协调RAG推荐引擎和降级推荐系统
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List

from .recommendation_engine import RAGRecommendationEngine
from .fallback_system import FallbackRecommendationSystem
from .recommendation_formatter import RecommendationFormatter
from .product_knowledge import ProductKnowledgeManager

logger = logging.getLogger(__name__)

class RecommendationCoordinator:
    """推荐协调器 - 统一管理各种推荐策略"""
    
    def __init__(self, tenant_id: str, agent_id: str):
        self.tenant_id = tenant_id
        self.agent_id = agent_id
        self.logger = logging.getLogger(f"{__name__}.{tenant_id}")
        
        # 初始化各组件
        self.rag_engine = RAGRecommendationEngine(tenant_id)
        self.fallback_system = FallbackRecommendationSystem(tenant_id, agent_id)
        self.formatter = RecommendationFormatter(tenant_id, agent_id)
        self.knowledge_manager = ProductKnowledgeManager(tenant_id)
        
        # 系统状态
        self.rag_available = False
        self.initialization_attempted = False
        
        # 配置参数
        self.max_retries = 2
        self.timeout_seconds = 30
        
        self.logger.info(f"推荐协调器初始化: {agent_id}")
    
    async def initialize(self) -> None:
        """初始化推荐系统"""
        if self.initialization_attempted:
            return
        
        self.initialization_attempted = True
        
        try:
            # 尝试初始化RAG引擎
            await asyncio.wait_for(
                self.rag_engine.initialize(),
                timeout=self.timeout_seconds
            )
            self.rag_available = True
            self.logger.info("RAG推荐引擎可用")
            
        except Exception as e:
            self.logger.warning(f"RAG引擎初始化失败，将使用降级系统: {e}")
            self.rag_available = False
    
    async def generate_recommendations(
        self,
        customer_input: str,
        customer_profile: Dict[str, Any],
        needs_analysis: Dict[str, Any] = None,
        customer_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成产品推荐（自动选择最佳策略）
        
        参数:
            customer_input: 客户输入
            customer_profile: 客户档案
            needs_analysis: 需求分析结果
            customer_history: 客户历史
            
        返回:
            Dict[str, Any]: 统一格式的推荐结果
        """
        try:
            # 确保系统已初始化
            if not self.initialization_attempted:
                await self.initialize()
            
            # 优先尝试RAG推荐
            if self.rag_available:
                try:
                    rag_result = await self._get_rag_recommendations(
                        customer_input, customer_profile, customer_history, needs_analysis
                    )
                    
                    if rag_result.get("success", False):
                        # RAG推荐成功，返回已格式化的结果
                        # RAG引擎返回的数据已经是正确格式
                        recommendations = rag_result.get("recommendations", [])
                        
                        # 构建统一格式响应
                        return {
                            "products": [
                                {
                                    "id": rec.get("product_id", ""),
                                    "name": rec.get("product_data", {}).get("name", ""),
                                    "brand": rec.get("product_data", {}).get("brand", ""),
                                    "category": rec.get("product_data", {}).get("category", ""),
                                    "price": rec.get("product_data", {}).get("price", 0),
                                    "rating": rec.get("product_data", {}).get("rating", 0),
                                    "description": rec.get("product_data", {}).get("description", ""),
                                    "benefits": rec.get("product_data", {}).get("benefits", ""),
                                    "confidence_score": rec.get("confidence_score", 0),
                                    "recommendation_reason": rec.get("recommendation_reason", "")
                                } for rec in recommendations
                            ],
                            "general_advice": "基于您的需求，我为您推荐了以下产品。",
                            "recommendation_strategy": rag_result.get("strategy", "rag"),
                            "total_candidates": rag_result.get("total_candidates", 0),
                            "processing_time": rag_result.get("processing_time", 0),
                            "cache_hit": rag_result.get("cache_hit", False),
                            "confidence": self._calculate_rag_confidence(recommendations),
                            "agent_id": self.agent_id,
                            "rag_enhanced": True,
                            "metadata": rag_result.get("metadata", {})
                        }
                    else:
                        self.logger.warning("RAG推荐失败，切换到降级系统")
                        self.rag_available = False
                        
                except Exception as e:
                    self.logger.error(f"RAG推荐异常: {e}")
                    self.rag_available = False
            
            # 使用降级推荐系统
            return await self._get_fallback_recommendations(
                customer_input, customer_profile, needs_analysis
            )
            
        except Exception as e:
            self.logger.error(f"推荐生成完全失败: {e}")
            return self.formatter.create_fallback_response(str(e))
    
    async def _get_rag_recommendations(
        self,
        customer_input: str,
        customer_profile: Dict[str, Any],
        customer_history: List[Dict[str, Any]] = None,
        needs_analysis: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """获取RAG增强推荐"""
        for attempt in range(self.max_retries):
            try:
                result = await asyncio.wait_for(
                    self.rag_engine.generate_recommendations(
                        customer_input,
                        customer_profile,
                        customer_history,
                        needs_analysis
                    ),
                    timeout=self.timeout_seconds
                )
                
                if result.get("success", False):
                    return result
                else:
                    self.logger.warning(f"RAG推荐尝试 {attempt + 1} 失败: {result.get('error', 'unknown')}")
                    
            except asyncio.TimeoutError:
                self.logger.warning(f"RAG推荐超时，尝试 {attempt + 1}/{self.max_retries}")
                
            except Exception as e:
                self.logger.error(f"RAG推荐异常，尝试 {attempt + 1}/{self.max_retries}: {e}")
        
        return {"success": False, "error": "RAG推荐多次尝试失败"}
    
    async def _get_fallback_recommendations(
        self,
        customer_input: str,
        customer_profile: Dict[str, Any],
        needs_analysis: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """获取降级推荐"""
        try:
            fallback_result = await self.fallback_system.generate_fallback_recommendations(
                customer_input, customer_profile, needs_analysis
            )
            
            # 添加推荐置信度计算
            if not fallback_result.get("confidence"):
                fallback_result["confidence"] = self.knowledge_manager.calculate_recommendation_confidence(
                    customer_profile, needs_analysis, base_confidence=0.6
                )
            
            return fallback_result
            
        except Exception as e:
            self.logger.error(f"降级推荐失败: {e}")
            return self.formatter.create_fallback_response(str(e))
    
    async def get_fast_recommendations(
        self,
        customer_input: str,
        customer_profile: Dict[str, Any],
        needs_analysis: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        快速推荐（使用预计算结果，适合简单查询）
        
        参数:
            customer_input: 客户输入
            customer_profile: 客户档案
            needs_analysis: 需求分析结果
            
        返回:
            Dict[str, Any]: 快速推荐结果
        """
        try:
            # 确定产品分类
            category = "skincare"  # 默认
            if needs_analysis:
                category = needs_analysis.get("product_category", "skincare")
            else:
                category = self.knowledge_manager.identify_product_category(customer_input)
            
            # 获取热门产品
            popular_products = self.knowledge_manager.get_popular_products(category)
            
            # 构建快速推荐响应
            products = []
            for i, product in enumerate(popular_products[:3]):
                products.append({
                    "id": f"fast_{category}_{i}",
                    "name": product["name"],
                    "brand": "热门品牌",
                    "category": product["category"],
                    "price": 0,  # 快速推荐不显示价格
                    "rating": 4.5,
                    "description": f"热门{product['category']}产品",
                    "confidence_score": 0.8,
                    "recommendation_reason": "热门推荐"
                })
            
            # 生成建议
            general_advice = f"这些是我们{category}类别中最受欢迎的产品，都有很好的用户反馈。"
            
            # 计算置信度
            confidence = self.knowledge_manager.calculate_recommendation_confidence(
                customer_profile, needs_analysis, base_confidence=0.8
            )
            
            return {
                "products": products,
                "general_advice": general_advice,
                "recommendation_method": "fast_lookup",
                "agent_id": self.agent_id,
                "confidence": confidence,
                "rag_enhanced": False,
                "processing_time": "< 50ms"
            }
            
        except Exception as e:
            self.logger.error(f"快速推荐失败: {e}")
            return self.formatter.create_fallback_response(str(e))
    
    async def search_products(self, query: str, top_k: int = 10) -> Dict[str, Any]:
        """
        产品搜索
        
        参数:
            query: 搜索查询
            top_k: 返回结果数量
            
        返回:
            Dict[str, Any]: 搜索结果
        """
        if self.rag_available:
            try:
                return await self.rag_engine.search_products(query, top_k)
            except Exception as e:
                self.logger.error(f"RAG搜索失败: {e}")
        
        # 降级到基础搜索
        return {
            "success": False,
            "error": "搜索功能暂时不可用", 
            "results": []
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取推荐系统状态"""
        return {
            "coordinator_id": self.agent_id,
            "tenant_id": self.tenant_id,
            "rag_available": self.rag_available,
            "initialization_attempted": self.initialization_attempted,
            "active_strategy": "rag" if self.rag_available else "fallback",
            "components": {
                "rag_engine": "available" if self.rag_available else "unavailable",
                "fallback_system": "available",
                "formatter": "available",
                "knowledge_manager": "available"
            }
        }
    
    async def get_comprehensive_stats(self) -> Dict[str, Any]:
        """获取综合统计信息"""
        stats = {
            "system_status": self.get_system_status(),
            "knowledge_stats": self.knowledge_manager.get_knowledge_stats(),
            "fallback_stats": self.fallback_system.get_fallback_stats()
        }
        
        # 如果RAG可用，添加RAG统计
        if self.rag_available:
            try:
                rag_stats = await self.rag_engine.get_stats()
                stats["rag_stats"] = rag_stats
            except Exception as e:
                self.logger.error(f"获取RAG统计失败: {e}")
                stats["rag_stats"] = {"error": str(e)}
        
        return stats
    
    def _calculate_rag_confidence(self, recommendations: List[Dict[str, Any]]) -> float:
        """计算RAG推荐置信度"""
        if not recommendations:
            return 0.0
        
        confidence_scores = [rec.get("confidence_score", 0.5) for rec in recommendations]
        return sum(confidence_scores) / len(confidence_scores)