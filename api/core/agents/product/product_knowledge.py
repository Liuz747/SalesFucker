"""
产品知识管理器
Product Knowledge Manager

管理产品分类、知识库和基础产品信息
"""

import logging
from typing import Dict, Any, List
from functools import lru_cache

logger = logging.getLogger(__name__)

class ProductKnowledgeManager:
    """产品知识管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}")
        
        # 产品分类体系
        self.product_categories = {
            "skincare": ["cleanser", "moisturizer", "serum", "sunscreen", "toner"],
            "makeup": ["foundation", "concealer", "lipstick", "eyeshadow", "mascara"],
            "fragrance": ["perfume", "body_spray", "essential_oil"],
            "tools": ["brush", "sponge", "applicator", "mirror"]
        }
        
        # 预计算的热门产品（生产环境中会从数据库加载）
        self._popular_products = self._init_popular_products()
        
        self.logger.info(f"产品知识管理器初始化完成")
    
    def get_product_categories(self) -> Dict[str, List[str]]:
        """获取产品分类"""
        return self.product_categories.copy()
    
    def get_category_products(self, category: str) -> List[str]:
        """获取指定分类的产品类型"""
        return self.product_categories.get(category, [])
    
    def identify_product_category(self, text: str) -> str:
        """
        从文本中识别产品分类
        
        参数:
            text: 输入文本
            
        返回:
            str: 产品分类名称
        """
        text_lower = text.lower()
        
        for category, products in self.product_categories.items():
            if any(product in text_lower for product in products):
                return category
        
        return "general"
    
    @lru_cache(maxsize=128)
    def get_popular_products(self, category: str = None) -> List[Dict[str, Any]]:
        """
        获取热门产品列表
        
        参数:
            category: 产品分类，None则返回所有
            
        返回:
            List[Dict[str, Any]]: 热门产品列表
        """
        if category and category in self._popular_products:
            return [
                {"name": name, "category": category, "type": "popular"}
                for name in self._popular_products[category]
            ]
        elif category is None:
            # 返回所有分类的热门产品
            all_products = []
            for cat, products in self._popular_products.items():
                all_products.extend([
                    {"name": name, "category": cat, "type": "popular"}
                    for name in products
                ])
            return all_products
        else:
            return []
    
    def build_recommendation_context(
        self, 
        customer_profile: Dict[str, Any], 
        needs_analysis: Dict[str, Any] = None
    ) -> str:
        """
        构建推荐上下文信息
        
        参数:
            customer_profile: 客户档案
            needs_analysis: 需求分析结果
            
        返回:
            str: 格式化的上下文信息
        """
        context_parts = []
        
        # 产品类别信息
        category = needs_analysis.get("product_category", "general") if needs_analysis else "general"
        if category in self.product_categories:
            available_products = self.product_categories[category]
            context_parts.append(f"Available {category} products: {', '.join(available_products)}")
        
        # 品牌信息
        context_parts.append(f"Brand focus: premium beauty products")
        
        # 季节性建议
        context_parts.append("Current season: Consider hydration for winter, sun protection for summer")
        
        # 客户偏好信息
        if customer_profile:
            if skin_type := customer_profile.get("skin_type"):
                context_parts.append(f"Customer skin type: {skin_type}")
            if budget := customer_profile.get("budget_preference"):
                context_parts.append(f"Budget preference: {budget}")
        
        return " | ".join(context_parts)
    
    def calculate_recommendation_confidence(
        self, 
        customer_profile: Dict[str, Any], 
        needs_analysis: Dict[str, Any] = None,
        base_confidence: float = 0.5
    ) -> float:
        """
        计算推荐置信度
        
        参数:
            customer_profile: 客户档案
            needs_analysis: 需求分析结果
            base_confidence: 基础置信度
            
        返回:
            float: 置信度分数 (0.0-1.0)
        """
        confidence = base_confidence
        
        # 根据客户档案完整度调整
        if customer_profile:
            if customer_profile.get("skin_type"):
                confidence += 0.2
            if customer_profile.get("purchase_history"):
                confidence += 0.2
            if customer_profile.get("preferences"):
                confidence += 0.1
        
        # 根据需求分析调整
        if needs_analysis:
            if needs_analysis.get("concerns"):
                confidence += 0.1
            if needs_analysis.get("product_category") != "general":
                confidence += 0.1
        
        return min(1.0, confidence)
    
    def is_simple_query(self, customer_input: str, needs_analysis: Dict[str, Any] = None) -> bool:
        """
        判断是否为简单查询（可使用快速推荐）
        
        参数:
            customer_input: 客户输入
            needs_analysis: 需求分析结果
            
        返回:
            bool: 是否为简单查询
        """
        simple_keywords = [
            "popular", "best", "recommend", "热门", "推荐", "好用",
            "moisturizer", "cleanser", "保湿", "洁面"
        ]
        return any(keyword in customer_input.lower() for keyword in simple_keywords)
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        total_products = sum(len(products) for products in self._popular_products.values())
        
        return {
            "total_categories": len(self.product_categories),
            "category_details": {
                cat: len(products) for cat, products in self.product_categories.items()
            },
            "popular_products_count": total_products,
            "supported_categories": list(self.product_categories.keys())
        }
    
    def _init_popular_products(self) -> Dict[str, List[str]]:
        """初始化热门产品数据（生产环境中从数据库加载）"""
        return {
            "skincare": [
                "温和洁面乳 - 适合所有肤质",
                "保湿精华 - 深层水分补充", 
                "防晒乳SPF50 - 日常防护必备",
                "维C精华 - 美白抗氧化",
                "玻尿酸面霜 - 深层保湿"
            ],
            "makeup": [
                "气垫粉底液 - 轻透自然",
                "防水睫毛膏 - 持久不晕染",
                "雾面口红 - 多色可选",
                "遮瑕膏 - 完美覆盖",
                "眉笔 - 自然塑形"
            ],
            "fragrance": [
                "清香淡香水 - 日常香气",
                "身体喷雾 - 清新持久",
                "固体香膏 - 便携持香"
            ],
            "tools": [
                "美妆蛋 - 完美上妆",
                "化妆刷套装 - 专业工具",
                "睫毛夹 - 卷翘效果"
            ]
        }