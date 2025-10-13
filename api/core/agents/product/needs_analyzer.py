"""
客户需求分析器
Customer Needs Analyzer

提供基础和语义增强的客户需求分析功能。
整合了 SentimentAnalysisAgent 提供的情感与意图综合分析结果。
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class CustomerNeedsAnalyzer:
    """
    客户需求分析器（适配 SentimentAnalysisAgent 的综合分析结果）

    功能：
    - 从 intent_analysis 提取结构化需求信息
    - 基于关键词的兜底分析
    - 整合客户档案和历史偏好

    注意：
    intent_analysis 由 SentimentAnalysisAgent 统一提供，
    包含情感和意图的综合分析结果。
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # 语义分析已由情感与意图分析合并提供，这里仅做适配与兜底
        self.semantic_analysis_enabled = False
    
    async def initialize(self) -> None:
        """保持兼容的空初始化"""
        self.semantic_analysis_enabled = False
        self.logger.info("需求分析器已就绪（使用 SentimentAnalysisAgent 的综合分析结果）")
    
    async def analyze_customer_needs(
        self,
        customer_input: str,
        customer_profile: Dict[str, Any],
        intent_analysis: dict = None
    ) -> dict:
        """
        分析客户需求（增强版）

        从 SentimentAnalysisAgent 提供的 intent_analysis 中提取需求信息。

        Args:
            customer_input: 客户输入
            customer_profile: 客户档案
            intent_analysis: 情感与意图综合分析结果（由 SentimentAnalysisAgent 提供）

        Returns:
            Dict[str, Any]: 需求分析结果
        """
        # 基于意图分析构建需求，并结合关键词兜底
        return self._analyze_basic_needs(
            customer_input, customer_profile, intent_analysis
        )
    
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
            intent_analysis: 情感与意图综合分析结果（由 SentimentAnalysisAgent 提供）

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
        
        # 从情感与意图综合分析获取结构化信息
        # 注意：intent_analysis 由 SentimentAnalysisAgent 统一提供
        if intent_analysis:
            # 顶层字段（与 SentimentAnalysisAgent 输出对齐）
            needs["urgency"] = intent_analysis.get("urgency", needs["urgency"])
            category = intent_analysis.get("category")
            if category and category != "general":
                needs["product_category"] = category

            # 直接的客户需求关键词
            if isinstance(intent_analysis.get("needs"), list):
                # 将 LLM 抽取的需要映射到 concerns（与推荐过滤保持兼容）
                normalized = [str(x).strip().lower() for x in intent_analysis["needs"] if x]
                if normalized:
                    needs["concerns"].extend(list({n for n in normalized}))

            # 嵌套的客户档案信息
            profile_from_intent = intent_analysis.get("customer_profile", {}) or {}
            if isinstance(profile_from_intent, dict):
                # 皮肤问题
                skin_concerns = profile_from_intent.get("skin_concerns", [])
                if isinstance(skin_concerns, list):
                    needs["concerns"].extend([str(x).strip().lower() for x in skin_concerns if x])

                # 预算信号 -> 预算敏感度（取首个强信号作为偏好）
                budget_signals = profile_from_intent.get("budget_signals", [])
                if isinstance(budget_signals, list) and budget_signals:
                    needs["budget_sensitivity"] = str(budget_signals[0]).strip().lower()

                # 可能的肤质推断
                inferred_skin_type = profile_from_intent.get("skin_type") or profile_from_intent.get("skin_type_indicators", [None])[0]
                if inferred_skin_type:
                    needs["skin_type"] = str(inferred_skin_type).strip().lower()
        
        # 从客户档案获取偏好
        if customer_profile:
            if customer_profile.get("budget_preference"):
                needs["budget_sensitivity"] = customer_profile["budget_preference"]
            if customer_profile.get("skin_type"):
                needs["skin_type"] = customer_profile["skin_type"]
            if customer_profile.get("preferred_brands"):
                needs["preferred_brands"] = customer_profile["preferred_brands"]
        
        return needs
    
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