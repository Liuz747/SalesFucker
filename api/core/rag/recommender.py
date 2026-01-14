"""
Clean recommendation engine with multiple strategies
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from libs.factory import infra_registry
from .search import ProductSearch, SearchQuery
from .vector_db import MilvusDB


class RecommendationType(Enum):
    SIMILAR = "similar"
    PERSONALIZED = "personalized"
    TRENDING = "trending"
    CROSS_SELL = "cross_sell"
    QUERY_BASED = "query_based"


@dataclass
class RecommendationRequest:
    customer_id: str
    tenant_id: str
    rec_type: RecommendationType
    context: dict[str, Any] = None
    max_results: int = 10


@dataclass
class Recommendation:
    product_id: str
    product_data: dict[str, Any]
    score: float
    reason: str


class ProductRecommender:
    """Fast, multi-strategy product recommender"""
    
    def __init__(self, tenant_id: str = None):
        self.tenant_id = tenant_id
        self.search = ProductSearch()
        self.vector_db = MilvusDB()
        self.redis_client = infra_registry.get_cached_clients().redis
        
        # Strategy weights
        self.strategy_weights = {
            RecommendationType.SIMILAR: 1.0,
            RecommendationType.PERSONALIZED: 0.8,
            RecommendationType.TRENDING: 0.6,
            RecommendationType.CROSS_SELL: 0.7,
            RecommendationType.QUERY_BASED: 0.9
        }
        self._initialized = False
    
    async def initialize(self):
        """初始化推荐引擎"""
        try:
            # 在MVP中简化初始化
            await self.search.initialize()
            self._initialized = True
            return True
        except Exception as e:
            print(f"ProductRecommender initialization failed: {e}")
            return False
    
    async def recommend(self, request: RecommendationRequest) -> list[Recommendation]:
        """Main recommendation interface"""
        if request.rec_type == RecommendationType.SIMILAR:
            return await self._similar_products(request)
        elif request.rec_type == RecommendationType.PERSONALIZED:
            return await self._personalized_recommendations(request)
        elif request.rec_type == RecommendationType.TRENDING:
            return await self._trending_products(request)
        elif request.rec_type == RecommendationType.CROSS_SELL:
            return await self._cross_sell_recommendations(request)
        else:
            return []
    
    async def _similar_products(self, request: RecommendationRequest) -> list[Recommendation]:
        """Find similar products based on context"""
        context = request.context or {}
        
        # Get reference product
        if "product_id" in context:
            # Similar to specific product
            product_data = context.get("product_data", {})
            if not product_data:
                return []
            
            results = await self.search.search_by_product(
                tenant_id=request.tenant_id,
                product_data=product_data,
                top_k=request.max_results
            )
        else:
            # Similar to query/preference
            query_text = context.get("query", "")
            if not query_text:
                return []
            
            query = SearchQuery(
                text=query_text,
                tenant_id=request.tenant_id,
                top_k=request.max_results
            )
            response = await self.search.search(query)
            results = response.results
        
        return [
            Recommendation(
                product_id=r.product_id,
                product_data=r.product_data,
                score=r.score * self.strategy_weights[RecommendationType.SIMILAR],
                reason="Similar to your preferences"
            )
            for r in results
        ]
    
    async def _personalized_recommendations(self, request: RecommendationRequest) -> list[Recommendation]:
        """Personalized recommendations based on customer profile"""
        context = request.context or {}
        profile = context.get("customer_profile", {})
        
        if not profile:
            return []
        
        # Build personalized query from profile
        query_parts = []
        
        # Add preferences
        if skin_type := profile.get("skin_type"):
            query_parts.append(f"suitable for {skin_type} skin")
        
        if concerns := profile.get("skin_concerns"):
            if isinstance(concerns, list):
                query_parts.extend(concerns)
            else:
                query_parts.append(str(concerns))
        
        if age_group := profile.get("age_group"):
            query_parts.append(f"for {age_group}")
        
        if not query_parts:
            return []
        
        query = SearchQuery(
            text=" ".join(query_parts),
            tenant_id=request.tenant_id,
            top_k=request.max_results,
            filters=self._build_profile_filters(profile)
        )
        
        response = await self.search.search(query)
        
        return [
            Recommendation(
                product_id=r.product_id,
                product_data=r.product_data,
                score=r.score * self.strategy_weights[RecommendationType.PERSONALIZED],
                reason="Personalized for your skin profile"
            )
            for r in response.results
        ]
    
    async def _trending_products(self, request: RecommendationRequest) -> list[Recommendation]:
        """Get trending/popular products"""
        # Use cached trending products
        cache_key = f"trending:{request.tenant_id}"
        
        try:
            cached = await self.redis_client.get(cache_key)
            if cached:
                trending_ids = eval(cached)
                
                # Get product details (simplified - in real app would batch fetch)
                recommendations = []
                for product_id in trending_ids[:request.max_results]:
                    # This would be replaced with actual product fetch
                    recommendations.append(
                        Recommendation(
                            product_id=product_id,
                            product_data={"id": product_id, "name": f"Trending Product {product_id}"},
                            score=0.9 * self.strategy_weights[RecommendationType.TRENDING],
                            reason="Currently trending"
                        )
                    )
                return recommendations
        except:
            pass
        
        return []
    
    async def _cross_sell_recommendations(self, request: RecommendationRequest) -> list[Recommendation]:
        """Cross-sell recommendations based on purchase history"""
        context = request.context or {}
        purchased_products = context.get("purchased_products", [])
        
        if not purchased_products:
            return []
        
        # Find complementary products
        all_recommendations = []
        
        for product in purchased_products:
            # Create query for complementary products
            category = product.get("category", "")
            brand = product.get("brand", "")
            
            # Simple cross-sell logic
            if category == "cleanser":
                query_text = f"{brand} moisturizer toner serum"
            elif category == "moisturizer":
                query_text = f"{brand} cleanser sunscreen mask"
            else:
                query_text = f"{brand} skincare routine"
            
            query = SearchQuery(
                text=query_text,
                tenant_id=request.tenant_id,
                top_k=5,
                filters={"brand": brand} if brand else None
            )
            
            response = await self.search.search(query)
            
            for r in response.results:
                # Skip if already purchased
                if r.product_id not in [p.get("id") for p in purchased_products]:
                    all_recommendations.append(
                        Recommendation(
                            product_id=r.product_id,
                            product_data=r.product_data,
                            score=r.score * self.strategy_weights[RecommendationType.CROSS_SELL],
                            reason=f"Complements your {product.get('name', 'purchase')}"
                        )
                    )
        
        # Sort by score and deduplicate
        seen = set()
        unique_recs = []
        for rec in sorted(all_recommendations, key=lambda x: x.score, reverse=True):
            if rec.product_id not in seen:
                seen.add(rec.product_id)
                unique_recs.append(rec)
                if len(unique_recs) >= request.max_results:
                    break
        
        return unique_recs
    
    def _build_profile_filters(self, profile: dict[str, Any]) -> dict[str, Any]:
        """Build search filters from customer profile"""
        filters = {}
        
        if skin_type := profile.get("skin_type"):
            filters["skin_type_suitability"] = skin_type
        
        if price_range := profile.get("price_range"):
            if isinstance(price_range, dict):
                filters["price"] = price_range
        
        return filters if filters else None