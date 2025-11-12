"""
RAG推荐引擎核心逻辑
RAG Recommendation Engine Core Logic

处理RAG增强的产品推荐生成
"""

import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime

# from core.rag import (
#     ProductRecommender,
#     RecommendationType, 
#     RecommendationRequest,
#     ProductSearch,
#     SearchQuery
# )

logger = logging.getLogger(__name__)

class RAGRecommendationEngine:
    """RAG推荐引擎"""
    
    def __init__(self):
        self.recommender = ProductRecommender()
        self.search = ProductSearch()
        
        # 配置参数
        self.max_recommendations = 5
        self.similarity_threshold = 0.7
        self.response_timeout = 30
        
        # 默认推荐策略
        self.default_recommendation_types = [
            RecommendationType.PERSONALIZED,
            RecommendationType.QUERY_BASED,
            RecommendationType.TRENDING
        ]
        
        self.logger = logging.getLogger(f"{__name__}")
        self.initialized = False
    
    async def initialize(self) -> None:
        """初始化RAG推荐引擎"""
        try:
            await self.recommender.initialize()
            await self.search.initialize()
            self.initialized = True
            self.logger.info(f"RAG推荐引擎初始化完成")
        except Exception as e:
            self.logger.error(f"RAG推荐引擎初始化失败: {e}")
            raise
    
    async def generate_recommendations(
        self,
        customer_input: str,
        customer_profile: Dict[str, Any],
        customer_history: List[Dict[str, Any]] = None,
        needs_analysis: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        生成RAG增强的产品推荐
        
        Args:
            customer_input: 客户输入
            customer_profile: 客户档案
            customer_history: 客户历史记录
            needs_analysis: 需求分析结果
            
        Returns:
            Dict[str, Any]: 推荐结果
        """
        if not self.initialized:
            raise RuntimeError("推荐引擎未初始化")
        
        try:
            # 确定推荐策略
            recommendation_type = self._determine_recommendation_strategy(
                customer_input, customer_profile, needs_analysis
            )
            
            # 构建推荐请求
            request = RecommendationRequest(
                customer_id=customer_profile.get("customer_id", "anonymous"),
                tenant_id="default",
                rec_type=recommendation_type,
                context={
                    "query": customer_input,
                    "needs_analysis": needs_analysis or {},
                    "conversation_context": True
                },
                max_results=self.max_recommendations
            )
            
            # 获取推荐结果
            recommendations = await asyncio.wait_for(
                self.recommender.recommend(request),
                timeout=self.response_timeout
            )
            
            return {
                "success": True,
                "recommendations": recommendations,
                "strategy": recommendation_type.value,
                "total_candidates": len(recommendations),
                "processing_time": 0,
                "cache_hit": False,
                "metadata": {}
            }
            
        except asyncio.TimeoutError:
            self.logger.warning("RAG推荐超时")
            return {
                "success": False,
                "error": "recommendation_timeout",
                "message": "推荐生成超时"
            }
        except Exception as e:
            self.logger.error(f"RAG推荐生成失败: {e}")
            return {
                "success": False,
                "error": "recommendation_failed",
                "message": str(e)
            }
    
    def _determine_recommendation_strategy(
        self,
        customer_input: str,
        customer_profile: Dict[str, Any],
        needs_analysis: Dict[str, Any] = None
    ) -> RecommendationType:
        """
        根据上下文确定推荐策略
        
        Args:
            customer_input: 客户输入
            customer_profile: 客户档案
            needs_analysis: 需求分析结果
            
        Returns:
            RecommendationType: 推荐策略类型
        """
        input_lower = customer_input.lower()
        
        # 基于查询的推荐
        if any(keyword in input_lower for keyword in [
            "find", "looking for", "need", "want", "recommend", "suggest"
        ]):
            return RecommendationType.QUERY_BASED

        # 相似产品推荐
        if any(keyword in input_lower for keyword in [
            "similar", "like this", "alternatives", "compare"
        ]):
            return RecommendationType.SIMILAR

        # 热门推荐
        if any(keyword in input_lower for keyword in [
            "popular", "trending", "best seller", "top rated"
        ]):
            return RecommendationType.TRENDING

        # 交叉销售推荐
        if customer_profile.get("purchase_history") and any(keyword in input_lower for keyword in [
            "reorder", "buy again", "same as before", "usual"
        ]):
            return RecommendationType.CROSS_SELL
        
        # 默认使用个性化推荐
        return RecommendationType.PERSONALIZED
    
    async def search_products(self, query: str, top_k: int = 10) -> Dict[str, Any]:
        """
        产品语义搜索
        
        Args:
            query: 搜索查询
            top_k: 返回结果数量
            
        Returns:
            Dict[str, Any]: 搜索结果
        """
        if not self.initialized:
            raise RuntimeError("搜索引擎未初始化")
        
        try:
            search_query = SearchQuery(
                text=query,
                top_k=top_k
            )
            
            search_result = await self.search.search(search_query)
            
            return {
                "success": True,
                "results": search_result.results,
                "total_results": len(search_result.results),
                "processing_time": search_result.processing_time
            }
            
        except Exception as e:
            self.logger.error(f"产品搜索失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取推荐引擎统计信息"""
        try:
            if not self.initialized:
                return {
                    "initialized": False,
                    "error": "推荐引擎未初始化"
                }
            
            recommendation_stats = await self.recommender.get_recommendation_stats()
            
            return {
                "initialized": True,
                "configuration": {
                    "max_recommendations": self.max_recommendations,
                    "similarity_threshold": self.similarity_threshold,
                    "response_timeout": self.response_timeout
                },
                "recommendation_stats": recommendation_stats,
                "supported_types": [t.value for t in self.default_recommendation_types],
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"获取推荐引擎统计失败: {e}")
            return {
                "initialized": self.initialized,
                "error": str(e)
            }