"""
客户需求分析器
Customer Needs Analyzer

提供基础和语义增强的客户需求分析功能
"""

import logging
from typing import Dict, Any, List

from core.rag import ProductSearch, SearchQuery

logger = logging.getLogger(__name__)

class CustomerNeedsAnalyzer:
    """客户需求分析器"""
    
    def __init__(self):
        self.product_search = ProductSearch()
        self.logger = logging.getLogger(__name__)
        self.semantic_analysis_enabled = False
    
    async def initialize(self) -> None:
        """初始化需求分析器"""
        try:
            await self.product_search.initialize()
            self.semantic_analysis_enabled = True
            self.logger.info("需求分析器初始化完成")
        except Exception as e:
            self.logger.warning(f"语义分析初始化失败，使用基础分析: {e}")
            self.semantic_analysis_enabled = False
    
    async def analyze_customer_needs(
        self,
        customer_input: str,
        customer_profile: Dict[str, Any],
        intent_analysis: dict = None
    ) -> dict:
        """
        分析客户需求（增强版）
        
        Args:
            customer_input: 客户输入
            customer_profile: 客户档案
            intent_analysis: 意图分析结果
            
        Returns:
            Dict[str, Any]: 需求分析结果
        """
        # 基础需求分析
        basic_needs = self._analyze_basic_needs(
            customer_input, customer_profile, intent_analysis
        )
        
        # 语义增强分析
        # if self.semantic_analysis_enabled:
        #     try:
        #         semantic_insights = await self._analyze_semantic_needs(customer_input)
        #         basic_needs.update(semantic_insights)
        #         basic_needs["semantic_analysis_available"] = True
        #     except Exception as e:
        #         self.logger.warning(f"语义需求分析失败: {e}")
        #         basic_needs["semantic_analysis_available"] = False
        # else:
        #     basic_needs["semantic_analysis_available"] = False
        
        return basic_needs
    
    def _analyze_basic_needs(
        self,
        customer_input: str,
        customer_profile: Dict[str, Any],
        intent_analysis: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        基础客户需求分析
        
        Args:
            customer_input: 客户输入
            customer_profile: 客户档案
            intent_analysis: 意图分析结果
            
        Returns:
            Dict[str, Any]: 基础需求分析结果
        """
        needs = {
            "concerns": [],
            "product_category": "general",
            "urgency": "medium",
            "budget_sensitivity": "medium",
            "analysis_type": "basic"
        }
        
        input_lower = customer_input.lower()
        
        # 识别皮肤问题
        skin_concerns = {
            "acne": ["acne", "pimple", "breakout", "blemish", "痘痘", "粉刺"],
            "dryness": ["dry", "flaky", "tight", "dehydrated", "干燥", "缺水"],
            "oily": ["oily", "greasy", "shine", "sebum", "油性", "出油"],
            "aging": ["wrinkle", "fine line", "aging", "mature", "皱纹", "抗老"],
            "sensitivity": ["sensitive", "irritated", "red", "reactive", "敏感", "过敏"]
        }
        
        for concern, keywords in skin_concerns.items():
            if any(keyword in input_lower for keyword in keywords):
                needs["concerns"].append(concern)
        
        # 识别产品类别
        product_categories = {
            "skincare": ["cleanser", "moisturizer", "serum", "sunscreen", "洁面", "保湿", "精华", "防晒"],
            "makeup": ["foundation", "concealer", "lipstick", "eyeshadow", "粉底", "遮瑕", "口红", "眼影"],
            "fragrance": ["perfume", "body spray", "香水", "香氛"],
            "tools": ["brush", "sponge", "applicator", "刷子", "美妆蛋"]
        }
        
        for category, keywords in product_categories.items():
            if any(keyword in input_lower for keyword in keywords):
                needs["product_category"] = category
                break
        
        # 识别紧急程度
        urgency_indicators = {
            "high": ["urgent", "asap", "immediately", "emergency", "急需", "紧急", "马上"],
            "low": ["whenever", "eventually", "no rush", "不急", "随时", "慢慢来"]
        }
        
        for urgency_level, keywords in urgency_indicators.items():
            if any(keyword in input_lower for keyword in keywords):
                needs["urgency"] = urgency_level
                break
        
        # 从意图分析获取信息
        if intent_analysis:
            needs["urgency"] = intent_analysis.get("urgency", needs["urgency"])
            if intent_analysis.get("category") != "general":
                needs["product_category"] = intent_analysis.get("category", needs["product_category"])
        
        # 从客户档案获取偏好
        if customer_profile:
            if customer_profile.get("budget_preference"):
                needs["budget_sensitivity"] = customer_profile["budget_preference"]
            if customer_profile.get("skin_type"):
                needs["skin_type"] = customer_profile["skin_type"]
            if customer_profile.get("preferred_brands"):
                needs["preferred_brands"] = customer_profile["preferred_brands"]
        
        return needs
    
    async def _analyze_semantic_needs(self, customer_input: str) -> Dict[str, Any]:
        """
        语义需求分析
        
        Args:
            customer_input: 客户输入
            
        Returns:
            Dict[str, Any]: 语义分析洞察
        """
        try:
            # 使用语义检索理解客户需求
            search_query = SearchQuery(
                text=customer_input,
                tenant_id=self.tenant_id,
                top_k=3
            )
            
            search_result = await self.product_search.search(search_query)
            
            # 从检索结果中提取需求洞察
            semantic_insights = {"analysis_type": "semantic"}
            
            if search_result.results:
                insights = self._extract_semantic_insights(search_result.results)
                semantic_insights.update(insights)
            
            return semantic_insights
            
        except Exception as e:
            self.logger.error(f"语义需求分析失败: {e}")
            return {"analysis_type": "semantic_failed", "error": str(e)}
    
    def _extract_semantic_insights(self, products) -> Dict[str, Any]:
        """
        从语义检索结果中提取需求洞察
        
        Args:
            products: 检索到的产品列表
            
        Returns:
            Dict[str, Any]: 语义洞察结果
        """
        insights = {}
        
        # 分析产品类别分布
        categories = [p.product_data.get("category", "") for p in products]
        if categories:
            most_common_category = max(set(categories), key=categories.count)
            insights["semantic_category"] = most_common_category
        
        # 分析肌肤类型偏好
        skin_types = [p.product_data.get("skin_type_suitability", "") for p in products]
        if skin_types:
            valid_skin_types = list(filter(None, skin_types))
            if valid_skin_types:
                most_common_skin_type = max(set(valid_skin_types), key=skin_types.count, default="")
                if most_common_skin_type:
                    insights["semantic_skin_type"] = most_common_skin_type
        
        # 分析价格范围偏好
        prices = [p.product_data.get("price", 0) for p in products if p.product_data.get("price")]
        if prices:
            avg_price = sum(prices) / len(prices)
            if avg_price < 100:
                insights["semantic_budget"] = "budget"
            elif avg_price < 500:
                insights["semantic_budget"] = "medium"
            else:
                insights["semantic_budget"] = "premium"
        
        # 分析品牌偏好
        brands = [p.product_data.get("brand", "") for p in products if p.product_data.get("brand")]
        if brands:
            brand_counts = {}
            for brand in brands:
                brand_counts[brand] = brand_counts.get(brand, 0) + 1
            
            if brand_counts:
                most_common_brand = max(brand_counts, key=brand_counts.get)
                insights["semantic_preferred_brand"] = most_common_brand
        
        # 分析功效偏好
        benefits = []
        for p in products:
            product_benefits = p.product_data.get("benefits", "")
            if product_benefits:
                benefits.extend(product_benefits.split("，"))
        
        if benefits:
            benefit_counts = {}
            for benefit in benefits:
                clean_benefit = benefit.strip()
                if clean_benefit:
                    benefit_counts[clean_benefit] = benefit_counts.get(clean_benefit, 0) + 1
            
            if benefit_counts:
                top_benefits = sorted(benefit_counts.items(), key=lambda x: x[1], reverse=True)[:3]
                insights["semantic_desired_benefits"] = [benefit for benefit, _ in top_benefits]
        
        return insights
    
    def get_analysis_summary(self, needs_analysis: Dict[str, Any]) -> str:
        """
        生成需求分析总结
        
        Args:
            needs_analysis: 需求分析结果
            
        Returns:
            str: 需求总结文本
        """
        summary_parts = []
        
        # 基础需求总结
        if needs_analysis.get("concerns"):
            concerns_text = "、".join(needs_analysis["concerns"])
            summary_parts.append(f"主要关注: {concerns_text}")
        
        if needs_analysis.get("product_category") != "general":
            summary_parts.append(f"产品类别: {needs_analysis['product_category']}")
        
        if needs_analysis.get("urgency") != "medium":
            urgency_map = {"high": "紧急", "low": "不急", "medium": "一般"}
            summary_parts.append(f"紧急程度: {urgency_map.get(needs_analysis['urgency'], '一般')}")
        
        # 语义分析总结
        if needs_analysis.get("semantic_analysis_available"):
            if needs_analysis.get("semantic_category"):
                summary_parts.append(f"语义类别: {needs_analysis['semantic_category']}")
            
            if needs_analysis.get("semantic_budget"):
                budget_map = {"budget": "经济实惠", "medium": "中等价位", "premium": "高端产品"}
                summary_parts.append(f"价格偏好: {budget_map.get(needs_analysis['semantic_budget'])}")
        
        if summary_parts:
            return "；".join(summary_parts)
        else:
            return "一般护肤咨询"