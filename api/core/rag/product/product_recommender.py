"""
产品推荐引擎

该模块提供多策略产品推荐功能。
支持相似产品、个性化推荐、热门产品和交叉销售等策略。

核心功能:
- 策略1: 相似产品推荐（向量相似度）
- 策略2: 个性化推荐（用户历史+偏好）
- 策略3: 热门产品推荐（流行度）
- 策略4: 交叉销售推荐（经常一起购买）
- 策略加权和混合
"""

from enum import Enum
from typing import Optional

from core.rag.product.product_search import ProductResult, product_search
from utils import get_component_logger

logger = get_component_logger(__name__, "ProductRecommender")


class RecommendationStrategy(str, Enum):
    """推荐策略枚举"""
    SIMILAR = "similar"  # 相似产品
    PERSONALIZED = "personalized"  # 个性化
    TRENDING = "trending"  # 热门产品
    CROSS_SELL = "cross_sell"  # 交叉销售


class ProductRecommender:
    """
    产品推荐引擎

    提供多种推荐策略，可以单独使用或组合使用。
    """

    def __init__(self):
        """初始化ProductRecommender"""
        # 默认策略权重
        self.default_weights = {
            RecommendationStrategy.SIMILAR: 0.4,
            RecommendationStrategy.PERSONALIZED: 0.3,
            RecommendationStrategy.TRENDING: 0.2,
            RecommendationStrategy.CROSS_SELL: 0.1
        }

    async def recommend(
        self,
        tenant_id: str,
        user_context: Optional[dict] = None,
        product_context: Optional[str] = None,
        strategies: Optional[list[RecommendationStrategy]] = None,
        strategy_weights: Optional[dict[RecommendationStrategy, float]] = None,
        top_k: int = 10
    ) -> list[ProductResult]:
        """
        综合推荐产品

        参数:
            tenant_id: 租户ID
            user_context: 用户上下文（历史、偏好等）
            product_context: 产品上下文（当前浏览的产品ID）
            strategies: 使用的策略列表
            strategy_weights: 策略权重
            top_k: 返回数量

        返回:
            list[ProductResult]: 推荐产品列表
        """
        try:
            logger.info(f"开始产品推荐: tenant={tenant_id}, strategies={strategies}")

            # 使用默认策略
            if strategies is None:
                strategies = [
                    RecommendationStrategy.SIMILAR,
                    RecommendationStrategy.PERSONALIZED,
                    RecommendationStrategy.TRENDING
                ]

            # 使用默认权重
            if strategy_weights is None:
                strategy_weights = self.default_weights

            # 收集各策略的推荐结果
            all_recommendations = {}

            for strategy in strategies:
                weight = strategy_weights.get(strategy, 0.0)
                if weight <= 0:
                    continue

                # 执行策略
                results = await self._execute_strategy(
                    strategy=strategy,
                    tenant_id=tenant_id,
                    user_context=user_context,
                    product_context=product_context,
                    top_k=top_k * 2  # 获取更多结果用于混合
                )

                # 加权并合并结果
                for product in results:
                    product_id = product.product_id
                    weighted_score = product.score * weight

                    if product_id in all_recommendations:
                        # 累加分数
                        all_recommendations[product_id].score += weighted_score
                    else:
                        # 新产品
                        product.score = weighted_score
                        all_recommendations[product_id] = product

            # 按分数排序
            recommendations = sorted(
                all_recommendations.values(),
                key=lambda x: x.score,
                reverse=True
            )[:top_k]

            logger.info(f"产品推荐完成: {len(recommendations)} 个产品")
            return recommendations

        except Exception as e:
            logger.error(f"产品推荐失败: {e}")
            return []

    async def _execute_strategy(
        self,
        strategy: RecommendationStrategy,
        tenant_id: str,
        user_context: Optional[dict],
        product_context: Optional[str],
        top_k: int
    ) -> list[ProductResult]:
        """
        执行单个推荐策略

        参数:
            strategy: 推荐策略
            tenant_id: 租户ID
            user_context: 用户上下文
            product_context: 产品上下文
            top_k: 返回数量

        返回:
            list[ProductResult]: 推荐结果
        """
        match strategy:
            case RecommendationStrategy.SIMILAR:
                return await self._recommend_similar(tenant_id, product_context, top_k)

            case RecommendationStrategy.PERSONALIZED:
                return await self._recommend_personalized(tenant_id, user_context, top_k)

            case RecommendationStrategy.TRENDING:
                return await self._recommend_trending(tenant_id, top_k)

            case RecommendationStrategy.CROSS_SELL:
                return await self._recommend_cross_sell(tenant_id, product_context, top_k)

            case _:
                logger.warning(f"未知推荐策略: {strategy}")
                return []

    async def _recommend_similar(
        self,
        tenant_id: str,
        product_id: Optional[str],
        top_k: int
    ) -> list[ProductResult]:
        """
        策略1: 相似产品推荐

        参数:
            tenant_id: 租户ID
            product_id: 产品ID
            top_k: 返回数量

        返回:
            list[ProductResult]: 相似产品列表
        """
        if not product_id:
            logger.debug("无产品上下文，跳过相似产品推荐")
            return []

        logger.debug(f"执行相似产品推荐: {product_id}")
        return await product_search.search_similar_products(
            tenant_id=tenant_id,
            product_id=product_id,
            top_k=top_k
        )

    async def _recommend_personalized(
        self,
        tenant_id: str,
        user_context: Optional[dict],
        top_k: int
    ) -> list[ProductResult]:
        """
        策略2: 个性化推荐

        基于用户历史和偏好推荐产品。

        参数:
            tenant_id: 租户ID
            user_context: 用户上下文
            top_k: 返回数量

        返回:
            list[ProductResult]: 个性化推荐列表
        """
        if not user_context:
            logger.debug("无用户上下文，跳过个性化推荐")
            return []

        logger.debug("执行个性化推荐")

        # 从用户上下文提取信息
        user_preferences = user_context.get("preferences", [])
        user_history = user_context.get("history", [])
        user_age = user_context.get("age")
        user_interests = user_context.get("interests", [])

        # 构建个性化查询
        query_parts = []

        if user_preferences:
            query_parts.extend(user_preferences)

        if user_interests:
            query_parts.extend(user_interests)

        if user_age:
            query_parts.append(f"适合{user_age}岁")

        if not query_parts:
            # 如果没有足够的用户信息，使用历史记录
            if user_history:
                query_parts.append(f"类似于 {' '.join(user_history[:3])}")

        if not query_parts:
            logger.debug("用户上下文信息不足，无法生成个性化推荐")
            return []

        query = " ".join(query_parts)

        # 使用产品搜索
        return await product_search.search_by_query(
            tenant_id=tenant_id,
            query=query,
            top_k=top_k
        )

    async def _recommend_trending(
        self,
        tenant_id: str,
        top_k: int
    ) -> list[ProductResult]:
        """
        策略3: 热门产品推荐

        推荐当前流行的产品。

        参数:
            tenant_id: 租户ID
            top_k: 返回数量

        返回:
            list[ProductResult]: 热门产品列表
        """
        logger.debug("执行热门产品推荐")

        # 这里使用简化实现
        # 实际应该从产品服务获取热门产品列表
        # 或者基于销量、浏览量等指标排序

        # 使用通用查询获取热门产品
        query = "热门 推荐 畅销"

        return await product_search.search_by_query(
            tenant_id=tenant_id,
            query=query,
            top_k=top_k
        )

    async def _recommend_cross_sell(
        self,
        tenant_id: str,
        product_id: Optional[str],
        top_k: int
    ) -> list[ProductResult]:
        """
        策略4: 交叉销售推荐

        推荐经常一起购买的产品。

        参数:
            tenant_id: 租户ID
            product_id: 产品ID
            top_k: 返回数量

        返回:
            list[ProductResult]: 交叉销售产品列表
        """
        if not product_id:
            logger.debug("无产品上下文，跳过交叉销售推荐")
            return []

        logger.debug(f"执行交叉销售推荐: {product_id}")

        # 这里使用简化实现
        # 实际应该从订单数据分析经常一起购买的产品
        # 或者使用协同过滤算法

        # 使用相似产品作为交叉销售的简化实现
        return await product_search.search_similar_products(
            tenant_id=tenant_id,
            product_id=product_id,
            top_k=top_k
        )

    async def recommend_by_strategy(
        self,
        strategy: RecommendationStrategy,
        tenant_id: str,
        user_context: Optional[dict] = None,
        product_context: Optional[str] = None,
        top_k: int = 10
    ) -> list[ProductResult]:
        """
        使用单一策略推荐

        参数:
            strategy: 推荐策略
            tenant_id: 租户ID
            user_context: 用户上下文
            product_context: 产品上下文
            top_k: 返回数量

        返回:
            list[ProductResult]: 推荐产品列表
        """
        return await self._execute_strategy(
            strategy=strategy,
            tenant_id=tenant_id,
            user_context=user_context,
            product_context=product_context,
            top_k=top_k
        )


# 全局ProductRecommender实例
product_recommender = ProductRecommender()
