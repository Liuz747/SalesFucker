"""
RAG增强的产品专家智能体
RAG-Enhanced Product Expert Agent

结合向量检索和智能推荐的增强版产品专家智能体 - 重构版本
"""

import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime

from src.agents.base import BaseAgent, AgentMessage, ConversationState
from utils import get_current_datetime, get_processing_time_ms

# 导入重构后的模块
from .recommendation_engine import RAGRecommendationEngine
from src.rag import RecommendationType, RecommendationRequest, SearchQuery
from .needs_analyzer import CustomerNeedsAnalyzer
from .recommendation_formatter import RecommendationFormatter
from .fallback_system import FallbackRecommendationSystem
from .product_indexer import ProductIndexManager

logger = logging.getLogger(__name__)

class RAGEnhancedProductExpertAgent(BaseAgent):
    """
    RAG增强的产品专家智能体 (重构版本)
    
    作为轻量级编排器，协调各个专门模块：
    - RAG推荐引擎
    - 客户需求分析器
    - 推荐结果格式化器
    - 降级推荐系统
    - 产品索引管理器
    """
    
    def __init__(self, tenant_id: str, enable_fallback: bool = True):
        super().__init__(f"rag_product_expert_{tenant_id}", tenant_id)
        
        # 系统配置
        self.enable_fallback = enable_fallback
        self.rag_initialized = False
        
        # 初始化各个专门模块
        self.recommendation_engine = RAGRecommendationEngine(tenant_id)
        self.needs_analyzer = CustomerNeedsAnalyzer(tenant_id)
        self.formatter = RecommendationFormatter(tenant_id, self.agent_id)
        self.fallback_system = FallbackRecommendationSystem(tenant_id, self.agent_id)
        self.product_indexer = ProductIndexManager(tenant_id)
        
        self.logger.info(f"RAG增强产品专家智能体初始化: {self.agent_id}")
        
        # 异步初始化RAG系统
        asyncio.create_task(self._initialize_rag_system())
    
    async def _initialize_rag_system(self) -> None:
        """异步初始化RAG系统"""
        try:
            # 初始化各个模块
            await self.recommendation_engine.initialize()
            await self.needs_analyzer.initialize()
            await self.product_indexer.initialize()
            
            self.rag_initialized = True
            self.logger.info(f"RAG系统初始化完成: {self.agent_id}")
            
        except Exception as e:
            self.logger.error(f"RAG系统初始化失败: {e}")
            if self.enable_fallback:
                self.logger.info("启用降级模式，使用基础产品推荐")
            else:
                raise
    
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """
        处理产品咨询消息（RAG增强版）
        
        Args:
            message: 包含产品咨询的消息
            
        Returns:
            AgentMessage: 包含智能推荐的响应
        """
        try:
            customer_input = message.payload.get("text", "")
            customer_profile = message.context.get("customer_profile", {})
            customer_history = message.context.get("customer_history", [])
            
            # 检查RAG系统是否可用
            if not self.rag_initialized and not self.enable_fallback:
                raise RuntimeError("RAG系统未初始化")
            
            # 生成智能推荐
            recommendations = await self._orchestrate_recommendation_process(
                customer_input, customer_profile, customer_history
            )
            
            response_payload = {
                "product_recommendations": recommendations,
                "processing_agent": self.agent_id,
                "recommendation_timestamp": get_current_datetime().isoformat(),
                "rag_enabled": self.rag_initialized
            }
            
            return await self.send_message(
                recipient=message.sender,
                message_type="response",
                payload=response_payload,
                context=message.context
            )
            
        except Exception as e:
            error_context = {
                "message_id": message.message_id,
                "sender": message.sender,
                "rag_initialized": self.rag_initialized
            }
            error_info = await self.handle_error(e, error_context)
            
            # 使用格式化器创建紧急响应
            emergency_recommendations = self.formatter.create_fallback_response(str(e))
            
            return await self.send_message(
                recipient=message.sender,
                message_type="response",
                payload={
                    "error": error_info,
                    "product_recommendations": emergency_recommendations
                },
                context=message.context
            )
    
    async def process_conversation(self, state: ConversationState) -> ConversationState:
        """
        处理对话状态中的产品推荐（RAG增强版）
        
        Args:
            state: 当前对话状态
            
        Returns:
            ConversationState: 更新后的对话状态
        """
        start_time = get_current_datetime()
        
        try:
            customer_input = state.customer_input
            customer_profile = state.customer_profile
            customer_history = getattr(state, 'customer_history', [])
            
            # 分析客户需求
            needs_analysis = await self.needs_analyzer.analyze_customer_needs(
                customer_input, customer_profile, state.intent_analysis
            )
            
            # 生成推荐
            recommendations = await self._orchestrate_recommendation_process(
                customer_input, customer_profile, customer_history, needs_analysis
            )
            
            # 更新对话状态
            state.agent_responses[self.agent_id] = {
                "product_recommendations": recommendations,
                "needs_analysis": needs_analysis,
                "processing_complete": True,
                "rag_enhanced": self.rag_initialized,
                "recommendation_metadata": {
                    "engine_version": "rag_enhanced_v2.0_refactored",
                    "processing_time_ms": get_processing_time_ms(start_time),
                    "fallback_used": not self.rag_initialized
                }
            }
            state.active_agents.append(self.agent_id)
            
            # 更新处理统计
            processing_time = get_processing_time_ms(start_time)
            self.update_stats(processing_time)
            
            return state
            
        except Exception as e:
            await self.handle_error(e, {"conversation_id": state.conversation_id})
            
            # 使用格式化器创建错误响应
            error_recommendations = self.formatter.create_fallback_response(str(e))
            
            state.agent_responses[self.agent_id] = {
                "product_recommendations": error_recommendations,
                "error": str(e),
                "agent_id": self.agent_id,
                "rag_enhanced": False
            }
            
            return state
    
    async def _generate_rag_recommendations(
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
            Dict[str, Any]: 智能推荐结果
        """
        try:
            # 根据上下文选择推荐策略
            recommendation_type = self._determine_recommendation_strategy(
                customer_input, customer_profile, needs_analysis
            )
            
            # 构建推荐请求
            request = RecommendationRequest(
                customer_id=customer_profile.get("customer_id", "anonymous"),
                request_type=recommendation_type,
                context={
                    "query": customer_input,
                    "needs_analysis": needs_analysis or {},
                    "conversation_context": True
                },
                max_results=self.max_recommendations,
                include_explanations=True
            )
            
            # 获取智能推荐
            recommendation_response = await asyncio.wait_for(
                self.recommendation_engine.get_recommendations(
                    request, customer_profile, customer_history
                ),
                timeout=self.response_timeout
            )
            
            # 转换为统一格式
            formatted_recommendations = await self._format_recommendations(
                recommendation_response, customer_input, needs_analysis
            )
            
            return formatted_recommendations
            
        except asyncio.TimeoutError:
            self.logger.warning(f"RAG推荐超时，使用降级推荐")
            return await self._generate_fallback_recommendations(
                customer_input, customer_profile, needs_analysis
            )
        except Exception as e:
            self.logger.error(f"RAG推荐生成失败: {e}")
            if self.enable_fallback:
                return await self._generate_fallback_recommendations(
                    customer_input, customer_profile, needs_analysis
                )
            else:
                raise
    
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
            return RecommendationType.SIMILAR_PRODUCTS
        
        # 热门推荐
        if any(keyword in input_lower for keyword in [
            "popular", "trending", "best seller", "top rated"
        ]):
            return RecommendationType.TRENDING
        
        # 复购推荐
        if customer_profile.get("purchase_history") and any(keyword in input_lower for keyword in [
            "reorder", "buy again", "same as before", "usual"
        ]):
            return RecommendationType.REPLENISHMENT
        
        # 默认使用个性化推荐
        return RecommendationType.PERSONALIZED
    
    async def _format_recommendations(
        self,
        recommendation_response,
        customer_input: str,
        needs_analysis: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        格式化推荐结果为统一格式
        
        Args:
            recommendation_response: RAG引擎返回的推荐结果
            customer_input: 客户输入
            needs_analysis: 需求分析结果
            
        Returns:
            Dict[str, Any]: 格式化的推荐结果
        """
        try:
            products = []
            explanations = []
            
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
                    "similarity_score": rec.similarity_score,
                    "recommendation_reason": rec.recommendation_reason
                }
                
                if rec.explanation:
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
                "cache_hit": recommendation_response.cache_hit,
                "confidence": self._calculate_overall_confidence(products),
                "agent_id": self.agent_id,
                "rag_enhanced": True,
                "metadata": recommendation_response.metadata
            }
            
        except Exception as e:
            self.logger.error(f"推荐结果格式化失败: {e}")
            return {
                "products": [],
                "general_advice": "推荐系统暂时不可用，请告诉我您的具体需求。",
                "fallback": True,
                "error": str(e)
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
            
            if needs_analysis:
                if concerns := needs_analysis.get("concerns"):
                    context_parts.append(f"主要关注: {', '.join(concerns)}")
                if category := needs_analysis.get("product_category"):
                    context_parts.append(f"产品类别: {category}")
            
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
            
            # LLM调用暂时禁用，使用简化建议
            advice = "基于您的需求，建议选择适合您肤质的产品。"
            
            return advice.strip()
            
        except Exception as e:
            self.logger.error(f"综合建议生成失败: {e}")
            # 降级到模板建议
            if products:
                return f"根据您的需求，我为您推荐了{len(products)}款产品。这些产品都经过精心挑选，非常适合您的肌肤状况。建议您根据自己的偏好和预算选择。"
            else:
                return "请告诉我更多关于您的需求，我会为您提供更合适的推荐。"
    
    def _calculate_overall_confidence(self, products: List[Dict[str, Any]]) -> float:
        """计算整体推荐置信度"""
        if not products:
            return 0.0
        
        confidence_scores = [p.get("confidence_score", 0.5) for p in products]
        return sum(confidence_scores) / len(confidence_scores)
    
    async def _analyze_customer_needs_enhanced(
        self,
        customer_input: str,
        customer_profile: Dict[str, Any],
        intent_analysis: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        增强版客户需求分析
        
        在原有分析基础上增加语义理解
        """
        # 保留原有基础分析逻辑
        basic_needs = self._analyze_customer_needs_basic(
            customer_input, customer_profile, intent_analysis
        )
        
        # 如果RAG系统可用，增加语义分析
        if self.rag_initialized:
            try:
                # 使用语义检索理解客户需求
                search_query = SearchQuery(
                    text=customer_input,
                    tenant_id=self.tenant_id,
                    top_k=3
                )
                
                search_result = await self.product_search.search(search_query)
                
                # 从检索结果中提取需求洞察
                if search_result.results:
                    semantic_insights = self._extract_semantic_insights(search_result.results)
                    basic_needs.update(semantic_insights)
                    basic_needs["semantic_analysis_available"] = True
                
            except Exception as e:
                self.logger.warning(f"语义需求分析失败，使用基础分析: {e}")
                basic_needs["semantic_analysis_available"] = False
        
        return basic_needs
    
    def _analyze_customer_needs_basic(
        self,
        customer_input: str,
        customer_profile: Dict[str, Any],
        intent_analysis: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """基础客户需求分析（原有逻辑）"""
        needs = {
            "concerns": [],
            "product_category": "general",
            "urgency": "medium",
            "budget_sensitivity": "medium"
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
        
        # 从意图分析获取信息
        if intent_analysis:
            needs["urgency"] = intent_analysis.get("urgency", "medium")
            if intent_analysis.get("category") != "general":
                needs["product_category"] = intent_analysis.get("category", "general")
        
        # 从客户档案获取偏好
        if customer_profile:
            if customer_profile.get("budget_preference"):
                needs["budget_sensitivity"] = customer_profile["budget_preference"]
        
        return needs
    
    def _extract_semantic_insights(self, products) -> Dict[str, Any]:
        """从语义检索结果中提取需求洞察"""
        insights = {}
        
        # 分析产品类别分布
        categories = [p.product_data.get("category", "") for p in products]
        if categories:
            most_common_category = max(set(categories), key=categories.count)
            insights["semantic_category"] = most_common_category
        
        # 分析肌肤类型偏好
        skin_types = [p.product_data.get("skin_type_suitability", "") for p in products]
        if skin_types:
            most_common_skin_type = max(set(filter(None, skin_types)), key=skin_types.count, default="")
            if most_common_skin_type:
                insights["semantic_skin_type"] = most_common_skin_type
        
        # 分析价格范围
        prices = [p.product_data.get("price", 0) for p in products if p.product_data.get("price")]
        if prices:
            avg_price = sum(prices) / len(prices)
            if avg_price < 100:
                insights["semantic_budget"] = "budget"
            elif avg_price < 500:
                insights["semantic_budget"] = "medium"
            else:
                insights["semantic_budget"] = "premium"
        
        return insights
    
    async def _generate_fallback_recommendations(
        self,
        customer_input: str,
        customer_profile: Dict[str, Any],
        needs_analysis: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        生成降级推荐（基础版本）
        
        当RAG系统不可用时使用
        """
        try:
            # 使用简化的推荐逻辑
            fallback_products = [
                {
                    "id": "fallback_001",
                    "name": "温和保湿洁面乳",
                    "brand": "经典品牌",
                    "category": "skincare",
                    "price": 88.0,
                    "rating": 4.5,
                    "description": "适合所有肌肤类型的温和洁面产品",
                    "benefits": "温和清洁，保持肌肤水分平衡",
                    "confidence_score": 0.7,
                    "recommendation_reason": "基础护肤推荐"
                },
                {
                    "id": "fallback_002", 
                    "name": "多效保湿精华",
                    "brand": "经典品牌",
                    "category": "skincare",
                    "price": 168.0,
                    "rating": 4.3,
                    "description": "深层补水保湿，改善肌肤状态",
                    "benefits": "补水保湿，提升肌肤光泽",
                    "confidence_score": 0.6,
                    "recommendation_reason": "通用保湿护理"
                }
            ]
            
            # 根据客户档案调整推荐
            if customer_profile.get("skin_type"):
                skin_type = customer_profile["skin_type"]
                fallback_products[0]["skin_type_suitability"] = skin_type
                fallback_products[1]["skin_type_suitability"] = skin_type
            
            return {
                "products": fallback_products,
                "general_advice": "这些是我们的经典推荐产品，适合大多数客户。如需更精准的推荐，请告诉我您的具体需求。",
                "fallback": True,
                "confidence": 0.6,
                "agent_id": self.agent_id,
                "rag_enhanced": False
            }
            
        except Exception as e:
            self.logger.error(f"降级推荐生成失败: {e}")
            return {
                "products": [],
                "general_advice": "系统暂时不可用，请稍后再试或联系客服获得帮助。",
                "fallback": True,
                "error": str(e),
                "confidence": 0.0
            }
    
    # 产品索引管理方法
    async def index_products(
        self, 
        products_data: List[Dict[str, Any]],
        update_existing: bool = False
    ) -> Dict[str, Any]:
        """
        索引产品数据到RAG系统
        
        Args:
            products_data: 产品数据列表
            update_existing: 是否更新已存在的产品
            
        Returns:
            Dict[str, Any]: 索引结果统计
        """
        if not self.rag_initialized:
            return {
                "success": False,
                "error": "RAG系统未初始化",
                "stats": None
            }
        
        try:
            stats = await self.indexing_pipeline.index_products_from_data(
                products_data, update_existing
            )
            
            self.logger.info(
                f"产品索引完成: 成功 {stats.successfully_indexed}/"
                f"{stats.total_products}, 耗时 {stats.processing_time:.2f}s"
            )
            
            return {
                "success": True,
                "stats": {
                    "total_products": stats.total_products,
                    "successfully_indexed": stats.successfully_indexed,
                    "failed_indexing": stats.failed_indexing,
                    "processing_time": stats.processing_time,
                    "errors": stats.errors
                }
            }
            
        except Exception as e:
            self.logger.error(f"产品索引失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "stats": None
            }
    
    async def get_rag_stats(self) -> Dict[str, Any]:
        """获取RAG系统统计信息"""
        try:
            if not self.rag_initialized:
                return {
                    "rag_initialized": False,
                    "error": "RAG系统未初始化"
                }
            
            # 获取各组件统计
            recommendation_stats = await self.recommendation_engine.get_recommendation_stats()
            retrieval_stats = await self.product_retriever.get_retrieval_stats()
            indexing_stats = await self.indexing_pipeline.get_indexing_stats()
            
            return {
                "rag_initialized": True,
                "agent_id": self.agent_id,
                "tenant_id": self.tenant_id,
                "recommendation_engine": recommendation_stats,
                "retrieval_engine": retrieval_stats,
                "indexing_pipeline": indexing_stats,
                "system_config": {
                    "max_recommendations": self.max_recommendations,
                    "similarity_threshold": self.similarity_threshold,
                    "response_timeout": self.response_timeout,
                    "fallback_enabled": self.enable_fallback
                },
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"获取RAG统计失败: {e}")
            return {
                "rag_initialized": self.rag_initialized,
                "error": str(e)
            }
    
    def get_enhanced_metrics(self) -> Dict[str, Any]:
        """
        获取增强版性能指标
        
        Returns:
            Dict[str, Any]: 包含RAG信息的性能指标
        """
        base_metrics = {
            "total_recommendations": self.processing_stats["messages_processed"],
            "error_rate": self.processing_stats["errors"] / max(1, self.processing_stats["messages_processed"]) * 100,
            "average_processing_time": self.processing_stats["average_response_time"],
            "last_activity": self.processing_stats["last_activity"],
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id
        }
        
        # 添加RAG增强信息
        base_metrics.update({
            "rag_enhanced": True,
            "rag_initialized": self.rag_initialized,
            "fallback_enabled": self.enable_fallback,
            "supported_recommendation_types": [t.value for t in self.default_recommendation_types],
            "max_recommendations": self.max_recommendations,
            "similarity_threshold": self.similarity_threshold
        })
        
        return base_metrics