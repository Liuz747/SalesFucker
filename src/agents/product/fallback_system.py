"""
降级推荐系统
Fallback Recommendation System

当RAG系统不可用时提供基础推荐功能
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class FallbackRecommendationSystem:
    """降级推荐系统"""
    
    def __init__(self, tenant_id: str, agent_id: str):
        self.tenant_id = tenant_id
        self.agent_id = agent_id
        self.logger = logging.getLogger(f"{__name__}.{tenant_id}")
        
        # 基础产品库
        self.fallback_products = self._init_fallback_products()
    
    def _init_fallback_products(self) -> List[Dict[str, Any]]:
        """初始化基础产品库"""
        return [
            {
                "id": "fallback_001",
                "name": "温和保湿洁面乳",
                "brand": "经典品牌",
                "category": "skincare",
                "subcategory": "cleanser",
                "price": 88.0,
                "rating": 4.5,
                "description": "适合所有肌肤类型的温和洁面产品",
                "benefits": "温和清洁，保持肌肤水分平衡",
                "skin_type_suitability": "all",
                "concerns": ["daily_care"],
                "confidence_score": 0.7,
                "recommendation_reason": "基础护肤推荐"
            },
            {
                "id": "fallback_002", 
                "name": "多效保湿精华",
                "brand": "经典品牌",
                "category": "skincare",
                "subcategory": "serum",
                "price": 168.0,
                "rating": 4.3,
                "description": "深层补水保湿，改善肌肤状态",
                "benefits": "补水保湿，提升肌肤光泽",
                "skin_type_suitability": "dry,normal",
                "concerns": ["dryness", "hydration"],
                "confidence_score": 0.6,
                "recommendation_reason": "通用保湿护理"
            },
            {
                "id": "fallback_003",
                "name": "清爽控油乳液",
                "brand": "经典品牌",
                "category": "skincare",
                "subcategory": "moisturizer",
                "price": 128.0,
                "rating": 4.2,
                "description": "控制油脂分泌，保持肌肤清爽",
                "benefits": "控油平衡，收敛毛孔",
                "skin_type_suitability": "oily,combination",
                "concerns": ["oily", "pores"],
                "confidence_score": 0.65,
                "recommendation_reason": "油性肌肤护理"
            },
            {
                "id": "fallback_004",
                "name": "温和祛痘凝胶",
                "brand": "经典品牌",
                "category": "skincare",
                "subcategory": "treatment",
                "price": 98.0,
                "rating": 4.1,
                "description": "温和祛痘，减少炎症",
                "benefits": "祛痘消炎，预防痘痘复发",
                "skin_type_suitability": "acne_prone,oily",
                "concerns": ["acne", "inflammation"],
                "confidence_score": 0.68,
                "recommendation_reason": "痘痘肌护理"
            },
            {
                "id": "fallback_005",
                "name": "抗老紧致面霜",
                "brand": "经典品牌",
                "category": "skincare",
                "subcategory": "moisturizer",
                "price": 298.0,
                "rating": 4.4,
                "description": "抗衰老，紧致肌肤",
                "benefits": "减少细纹，提升肌肤弹性",
                "skin_type_suitability": "mature,dry",
                "concerns": ["aging", "wrinkles"],
                "confidence_score": 0.72,
                "recommendation_reason": "抗老护理"
            },
            {
                "id": "fallback_006",
                "name": "敏感肌舒缓霜",
                "brand": "经典品牌",
                "category": "skincare",
                "subcategory": "moisturizer",
                "price": 158.0,
                "rating": 4.6,
                "description": "专为敏感肌设计，舒缓镇静",
                "benefits": "舒缓敏感，增强肌肤屏障",
                "skin_type_suitability": "sensitive,reactive",
                "concerns": ["sensitivity", "irritation"],
                "confidence_score": 0.75,
                "recommendation_reason": "敏感肌护理"
            }
        ]
    
    async def generate_fallback_recommendations(
        self,
        customer_input: str,
        customer_profile: Dict[str, Any],
        needs_analysis: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        生成降级推荐
        
        Args:
            customer_input: 客户输入
            customer_profile: 客户档案
            needs_analysis: 需求分析结果
            
        Returns:
            Dict[str, Any]: 降级推荐结果
        """
        try:
            # 根据需求筛选产品
            filtered_products = self._filter_products_by_needs(
                customer_input, customer_profile, needs_analysis
            )
            
            # 根据客户档案个性化调整
            personalized_products = self._personalize_products(
                filtered_products, customer_profile
            )
            
            # 限制推荐数量
            final_products = personalized_products[:5]
            
            # 生成建议
            general_advice = self._generate_fallback_advice(
                final_products, customer_input, needs_analysis
            )
            
            return {
                "products": final_products,
                "general_advice": general_advice,
                "fallback": True,
                "confidence": self._calculate_fallback_confidence(final_products),
                "agent_id": self.agent_id,
                "rag_enhanced": False,
                "recommendation_strategy": "fallback_rule_based"
            }
            
        except Exception as e:
            self.logger.error(f"降级推荐生成失败: {e}")
            return self._create_emergency_response(str(e))
    
    def _filter_products_by_needs(
        self,
        customer_input: str,
        customer_profile: Dict[str, Any],
        needs_analysis: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        根据需求筛选产品
        
        Args:
            customer_input: 客户输入
            customer_profile: 客户档案
            needs_analysis: 需求分析结果
            
        Returns:
            List[Dict[str, Any]]: 筛选后的产品列表
        """
        filtered_products = []
        input_lower = customer_input.lower()
        
        for product in self.fallback_products:
            score = 0
            
            # 基于关键词匹配
            if any(keyword in input_lower for keyword in [
                product["name"].lower(), 
                product["subcategory"], 
                *product["benefits"].lower().split("，")
            ]):
                score += 3
            
            # 基于肌肤问题匹配
            if needs_analysis and needs_analysis.get("concerns"):
                for concern in needs_analysis["concerns"]:
                    if concern in product.get("concerns", []):
                        score += 2
            
            # 基于产品类别匹配
            if needs_analysis and needs_analysis.get("product_category"):
                if needs_analysis["product_category"] == product["category"]:
                    score += 2
            
            # 基于肌肤类型匹配
            customer_skin_type = customer_profile.get("skin_type", "").lower()
            if customer_skin_type:
                skin_suitability = product.get("skin_type_suitability", "").lower()
                if customer_skin_type in skin_suitability or skin_suitability == "all":
                    score += 1
            
            # 设置匹配分数
            product_copy = product.copy()
            product_copy["match_score"] = score
            
            # 只保留有一定匹配度的产品
            if score > 0:
                filtered_products.append(product_copy)
        
        # 按匹配分数排序
        filtered_products.sort(key=lambda x: x["match_score"], reverse=True)
        
        # 如果没有匹配的产品，返回通用推荐
        if not filtered_products:
            return self.fallback_products[:3]
        
        return filtered_products
    
    def _personalize_products(
        self, 
        products: List[Dict[str, Any]], 
        customer_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        根据客户档案个性化产品信息
        
        Args:
            products: 产品列表
            customer_profile: 客户档案
            
        Returns:
            List[Dict[str, Any]]: 个性化后的产品列表
        """
        personalized_products = []
        
        for product in products:
            personalized_product = product.copy()
            
            # 根据客户肌肤类型调整适用性描述
            if customer_skin_type := customer_profile.get("skin_type"):
                personalized_product["skin_type_suitability"] = customer_skin_type
            
            # 根据预算偏好调整推荐理由
            budget_preference = customer_profile.get("budget_preference", "medium")
            price = product.get("price", 0)
            
            if budget_preference == "budget" and price > 200:
                personalized_product["confidence_score"] *= 0.8
                personalized_product["recommendation_reason"] += " (高性价比选择)"
            elif budget_preference == "premium" and price < 100:
                personalized_product["confidence_score"] *= 0.9
                personalized_product["recommendation_reason"] += " (经济实惠)"
            
            # 根据品牌偏好调整
            preferred_brands = customer_profile.get("preferred_brands", [])
            if preferred_brands and product.get("brand") in preferred_brands:
                personalized_product["confidence_score"] *= 1.2
                personalized_product["recommendation_reason"] += " (您偏爱的品牌)"
            
            personalized_products.append(personalized_product)
        
        return personalized_products
    
    def _generate_fallback_advice(
        self,
        products: List[Dict[str, Any]],
        customer_input: str,
        needs_analysis: Dict[str, Any] = None
    ) -> str:
        """
        生成降级建议文本
        
        Args:
            products: 推荐产品列表
            customer_input: 客户输入
            needs_analysis: 需求分析结果
            
        Returns:
            str: 建议文本
        """
        if not products:
            return "系统暂时不可用，请稍后再试或联系客服获得帮助。"
        
        advice_parts = []
        
        # 基础介绍
        advice_parts.append(f"根据您的咨询，我为您推荐了{len(products)}款经典产品。")
        
        # 根据需求添加针对性建议
        if needs_analysis:
            concerns = needs_analysis.get("concerns", [])
            if "acne" in concerns:
                advice_parts.append("这些产品都有温和祛痘功效，适合痘痘肌使用。")
            elif "dryness" in concerns:
                advice_parts.append("这些产品都能有效补水保湿，改善干燥问题。")
            elif "oily" in concerns:
                advice_parts.append("这些产品都有控油平衡功效，让肌肤保持清爽。")
            elif "aging" in concerns:
                advice_parts.append("这些产品都含有抗老成分，帮助延缓肌肤衰老。")
            elif "sensitivity" in concerns:
                advice_parts.append("这些产品都经过敏感肌测试，温和不刺激。")
            else:
                advice_parts.append("这些都是我们的经典推荐产品，适合大多数客户。")
        else:
            advice_parts.append("这些都是我们的热门产品，口碑很好。")
        
        # 使用建议
        advice_parts.append("建议您根据自己的偏好和预算选择。如需更精准的推荐，请告诉我您的具体需求。")
        
        return "".join(advice_parts)
    
    def _calculate_fallback_confidence(self, products: List[Dict[str, Any]]) -> float:
        """计算降级推荐的置信度"""
        if not products:
            return 0.0
        
        # 降级推荐的基础置信度较低
        base_confidence = 0.6
        
        # 根据匹配分数调整
        if products and products[0].get("match_score", 0) > 2:
            base_confidence = 0.7
        
        return base_confidence
    
    def _create_emergency_response(self, error_message: str) -> Dict[str, Any]:
        """创建紧急降级响应"""
        return {
            "products": [],
            "general_advice": "系统暂时不可用，请稍后再试或联系客服获得帮助。",
            "fallback": True,
            "error": error_message,
            "confidence": 0.0,
            "agent_id": self.agent_id,
            "rag_enhanced": False,
            "emergency_response": True
        }
    
    def get_fallback_stats(self) -> Dict[str, Any]:
        """获取降级系统统计信息"""
        return {
            "system_type": "fallback",
            "available_products": len(self.fallback_products),
            "tenant_id": self.tenant_id,
            "agent_id": self.agent_id,
            "product_categories": list(set(p["category"] for p in self.fallback_products)),
            "supported_concerns": list(set(
                concern for p in self.fallback_products 
                for concern in p.get("concerns", [])
            ))
        }