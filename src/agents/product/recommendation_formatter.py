"""
推荐结果格式化器
Recommendation Results Formatter

处理推荐结果的格式化和综合建议生成
"""

import logging
from typing import Dict, Any, List

from src.llm import get_multi_llm_client

logger = logging.getLogger(__name__)

class RecommendationFormatter:
    """推荐结果格式化器"""
    
    def __init__(self, tenant_id: str, agent_id: str):
        self.tenant_id = tenant_id
        self.agent_id = agent_id
        self.llm_client = get_multi_llm_client()
        self.logger = logging.getLogger(f"{__name__}.{tenant_id}")
    
    async def format_recommendations(
        self,
        recommendation_response,
        customer_input: str,
        needs_analysis: Dict[str, Any] = None,
        rag_enhanced: bool = True
    ) -> Dict[str, Any]:
        """
        格式化推荐结果为统一格式
        
        Args:
            recommendation_response: RAG引擎返回的推荐结果
            customer_input: 客户输入
            needs_analysis: 需求分析结果
            rag_enhanced: 是否为RAG增强推荐
            
        Returns:
            Dict[str, Any]: 格式化的推荐结果
        """
        try:
            products = []
            explanations = []
            
            # 格式化产品信息
            for rec in recommendation_response.recommendations:
                product_info = {
                    "id": rec.product_id,
                    "name": rec.product_data.get("name", ""),
                    "brand": rec.product_data.get("brand", ""),
                    "category": rec.product_data.get("category", ""),
                    "price": rec.product_data.get("price", 0),
                    "rating": rec.product_data.get("rating", 0),
                    "description": rec.product_data.get("description", ""),
                    "benefits": rec.product_data.get("benefits", ""),
                    "skin_type_suitability": rec.product_data.get("skin_type_suitability", ""),
                    "confidence_score": rec.confidence_score,
                    "similarity_score": getattr(rec, 'similarity_score', 0),
                    "recommendation_reason": rec.recommendation_reason
                }
                
                # 添加详细解释
                if hasattr(rec, 'explanation') and rec.explanation:
                    product_info["explanation"] = rec.explanation
                    explanations.append(rec.explanation)
                
                products.append(product_info)
            
            # 生成综合建议
            general_advice = await self._generate_general_advice(
                products, customer_input, needs_analysis, explanations
            )
            
            return {
                "products": products,
                "general_advice": general_advice,
                "recommendation_strategy": recommendation_response.recommendation_strategy,
                "total_candidates": recommendation_response.total_candidates,
                "processing_time": recommendation_response.processing_time,
                "cache_hit": getattr(recommendation_response, 'cache_hit', False),
                "confidence": self._calculate_overall_confidence(products),
                "agent_id": self.agent_id,
                "rag_enhanced": rag_enhanced,
                "metadata": getattr(recommendation_response, 'metadata', {})
            }
            
        except Exception as e:
            self.logger.error(f"推荐结果格式化失败: {e}")
            return {
                "products": [],
                "general_advice": "推荐系统暂时不可用，请告诉我您的具体需求。",
                "fallback": True,
                "error": str(e),
                "agent_id": self.agent_id,
                "rag_enhanced": False
            }
    
    async def _generate_general_advice(
        self,
        products: List[Dict[str, Any]],
        customer_input: str,
        needs_analysis: Dict[str, Any] = None,
        explanations: List[str] = None
    ) -> str:
        """
        生成综合建议
        
        Args:
            products: 推荐产品列表
            customer_input: 客户输入
            needs_analysis: 需求分析
            explanations: 产品解释列表
            
        Returns:
            str: 综合建议文本
        """
        try:
            if not products:
                return "很抱歉，暂时没有找到完全符合您需求的产品。请告诉我更多关于您的肌肤状况和偏好，我会为您提供更精准的推荐。"
            
            # 构建咨询上下文
            context_parts = [
                f"客户咨询: {customer_input}",
                f"推荐产品数量: {len(products)}"
            ]
            
            # 添加需求分析信息
            if needs_analysis:
                if concerns := needs_analysis.get("concerns"):
                    context_parts.append(f"主要关注: {', '.join(concerns)}")
                if category := needs_analysis.get("product_category"):
                    context_parts.append(f"产品类别: {category}")
                if skin_type := needs_analysis.get("skin_type"):
                    context_parts.append(f"肌肤类型: {skin_type}")
            
            # 获取产品重点信息
            product_highlights = []
            for product in products[:3]:  # 重点介绍前3个产品
                highlight = f"{product['name']} - {product.get('recommendation_reason', '智能推荐')}"
                if product.get('explanation'):
                    highlight += f" ({product['explanation']})"
                product_highlights.append(highlight)
            
            context_parts.extend(product_highlights)
            
            # 使用LLM生成个性化建议
            prompt = f"""
作为专业的美妆顾问，基于以下信息为客户提供温暖、专业的产品推荐建议（不超过100字）：

{chr(10).join(context_parts)}

请用亲切、专业的语调，重点强调产品如何满足客户需求，并提供使用建议。
"""
            
            messages = [{"role": "user", "content": prompt}]
            advice = await self.llm_client.chat_completion(
                messages, temperature=0.7, max_tokens=150
            )
            
            return advice.strip()
            
        except Exception as e:
            self.logger.error(f"综合建议生成失败: {e}")
            # 降级到模板建议
            return self._generate_template_advice(products, needs_analysis)
    
    def _generate_template_advice(
        self, 
        products: List[Dict[str, Any]], 
        needs_analysis: Dict[str, Any] = None
    ) -> str:
        """
        生成模板化建议（LLM不可用时的降级方案）
        
        Args:
            products: 推荐产品列表
            needs_analysis: 需求分析结果
            
        Returns:
            str: 模板化建议文本
        """
        if not products:
            return "请告诉我更多关于您的需求，我会为您提供更合适的推荐。"
        
        advice_parts = []
        
        # 基础推荐介绍
        advice_parts.append(f"根据您的需求，我为您推荐了{len(products)}款产品。")
        
        # 根据需求分析添加建议
        if needs_analysis:
            concerns = needs_analysis.get("concerns", [])
            if "acne" in concerns:
                advice_parts.append("这些产品都具有温和控油、抗痘功效。")
            elif "dryness" in concerns:
                advice_parts.append("这些产品都能深层补水保湿。")
            elif "aging" in concerns:
                advice_parts.append("这些产品都含有抗老成分，能改善肌肤状态。")
            elif "sensitivity" in concerns:
                advice_parts.append("这些产品都经过敏感肌测试，温和不刺激。")
            else:
                advice_parts.append("这些产品都经过精心挑选，适合您的肌肤状况。")
        
        # 使用建议
        advice_parts.append("建议您根据自己的偏好和预算选择，如有疑问随时咨询。")
        
        return "".join(advice_parts)
    
    def _calculate_overall_confidence(self, products: List[Dict[str, Any]]) -> float:
        """
        计算整体推荐置信度
        
        Args:
            products: 产品列表
            
        Returns:
            float: 置信度分数
        """
        if not products:
            return 0.0
        
        confidence_scores = [p.get("confidence_score", 0.5) for p in products]
        return sum(confidence_scores) / len(confidence_scores)
    
    def create_fallback_response(self, error_message: str = None) -> Dict[str, Any]:
        """
        创建降级响应
        
        Args:
            error_message: 错误信息
            
        Returns:
            Dict[str, Any]: 降级响应数据
        """
        return {
            "products": [],
            "general_advice": "我很乐意帮您找到合适的产品。请告诉我您的具体需求和肌肤类型。",
            "fallback": True,
            "error_recovery": True,
            "confidence": 0.0,
            "agent_id": self.agent_id,
            "rag_enhanced": False,
            "error": error_message
        }
    
    def format_product_summary(self, products: List[Dict[str, Any]]) -> str:
        """
        生成产品推荐摘要
        
        Args:
            products: 产品列表
            
        Returns:
            str: 产品摘要文本
        """
        if not products:
            return "暂无推荐产品"
        
        summary_parts = []
        for i, product in enumerate(products[:3], 1):
            name = product.get("name", "未知产品")
            brand = product.get("brand", "")
            price = product.get("price", 0)
            
            product_summary = f"{i}. {name}"
            if brand:
                product_summary += f" ({brand})"
            if price > 0:
                product_summary += f" - ¥{price}"
            
            summary_parts.append(product_summary)
        
        if len(products) > 3:
            summary_parts.append(f"...等{len(products)}款产品")
        
        return "；".join(summary_parts)