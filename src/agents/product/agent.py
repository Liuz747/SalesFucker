"""
Product Expert Agent

AI-powered product recommendation engine for beauty consultations.
Provides expert product knowledge and personalized recommendations.
"""

from typing import Dict, Any, List
import asyncio
import hashlib
from functools import lru_cache
from ..core import BaseAgent, AgentMessage, ConversationState
from src.llm import get_llm_client, get_prompt_manager
from src.utils import get_current_datetime, get_processing_time_ms


class ProductExpertAgent(BaseAgent):
    """
    产品专家智能体
    
    提供专业的美妆产品推荐和咨询服务。
    结合AI知识和产品数据库，为客户提供个性化的产品建议。
    """
    
    def __init__(self, tenant_id: str):
        super().__init__(f"product_expert_{tenant_id}", tenant_id)
        
        # LLM integration
        self.llm_client = get_llm_client()
        self.prompt_manager = get_prompt_manager()
        
        # 优化的产品知识库
        self.product_categories = {
            "skincare": ["cleanser", "moisturizer", "serum", "sunscreen", "toner"],
            "makeup": ["foundation", "concealer", "lipstick", "eyeshadow", "mascara"],
            "fragrance": ["perfume", "body_spray", "essential_oil"],
            "tools": ["brush", "sponge", "applicator", "mirror"]
        }
        
        # 性能优化组件
        self._recommendation_cache = {}  # 推荐结果缓存
        self._cache_ttl = 3600  # 1小时缓存
        self._max_cache_size = 500
        
        # 预计算的推荐模板（生产环境中会使用向量数据库）
        self._popular_products = self._init_popular_products()
        
        self.logger.info(f"产品专家智能体初始化完成: {self.agent_id}，启用性能优化")
    
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """
        处理产品咨询消息
        
        分析客户需求并提供产品推荐。
        
        参数:
            message: 包含产品咨询的消息
            
        返回:
            AgentMessage: 包含产品推荐的响应
        """
        try:
            customer_input = message.payload.get("text", "")
            customer_profile = message.context.get("customer_profile", {})
            
            product_recommendations = await self._generate_product_recommendations(
                customer_input, customer_profile
            )
            
            response_payload = {
                "product_recommendations": product_recommendations,
                "processing_agent": self.agent_id,
                "recommendation_timestamp": get_current_datetime().isoformat()
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
                "sender": message.sender
            }
            error_info = await self.handle_error(e, error_context)
            
            fallback_recommendations = {
                "products": [],
                "general_advice": "I'd be happy to help you find the perfect products. Could you tell me more about your skin type and concerns?",
                "fallback": True
            }
            
            return await self.send_message(
                recipient=message.sender,
                message_type="response",
                payload={"error": error_info, "product_recommendations": fallback_recommendations},
                context=message.context
            )
    
    async def process_conversation(self, state: ConversationState) -> ConversationState:
        """
        处理对话状态中的产品推荐
        
        在LangGraph工作流中生成产品推荐，更新对话状态。
        
        参数:
            state: 当前对话状态
            
        返回:
            ConversationState: 更新后的对话状态
        """
        start_time = get_current_datetime()
        
        try:
            customer_input = state.customer_input
            customer_profile = state.customer_profile
            
            # 分析客户需求和偏好
            needs_analysis = self._analyze_customer_needs(
                customer_input, customer_profile, state.intent_analysis
            )
            
            # 生成产品推荐
            product_recommendations = await self._generate_product_recommendations(
                customer_input, customer_profile, needs_analysis
            )
            
            # 更新对话状态
            state.agent_responses[self.agent_id] = {
                "product_recommendations": product_recommendations,
                "needs_analysis": needs_analysis,
                "processing_complete": True
            }
            state.active_agents.append(self.agent_id)
            
            # 更新处理统计
            processing_time = get_processing_time_ms(start_time)
            self.update_stats(processing_time)
            
            return state
            
        except Exception as e:
            await self.handle_error(e, {"conversation_id": state.conversation_id})
            
            # 设置降级推荐
            state.agent_responses[self.agent_id] = {
                "product_recommendations": {
                    "products": [],
                    "general_advice": "I'd be happy to help you find the perfect products for your needs.",
                    "fallback": True
                },
                "error": str(e),
                "agent_id": self.agent_id
            }
            
            return state
    
    async def _generate_product_recommendations(
        self, 
        customer_input: str, 
        customer_profile: Dict[str, Any], 
        needs_analysis: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        优化的产品推荐生成
        
        使用缓存和预计算提高性能
        
        参数:
            customer_input: 客户输入
            customer_profile: 客户档案
            needs_analysis: 需求分析结果
            
        返回:
            Dict[str, Any]: 产品推荐结果
        """
        try:
            # 1. 检查缓存
            cache_key = self._generate_cache_key(customer_input, customer_profile, needs_analysis)
            cached_result = self._get_cached_recommendation(cache_key)
            if cached_result:
                self.logger.debug(f"推荐缓存命中: {cache_key[:16]}...")
                return cached_result
            
            # 2. 快速推荐路径（简单查询）
            if self._is_simple_query(customer_input, needs_analysis):
                recommendations = await self._get_fast_recommendations(
                    customer_input, customer_profile, needs_analysis
                )
            else:
                # 3. 完整LLM推荐路径
                recommendations = await self._get_llm_recommendations(
                    customer_input, customer_profile, needs_analysis
                )
            
            # 4. 缓存结果
            self._cache_recommendation(cache_key, recommendations)
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"产品推荐生成失败: {e}")
            return self._get_fallback_recommendations(customer_profile)
    
    def _generate_cache_key(self, customer_input: str, customer_profile: Dict[str, Any], 
                          needs_analysis: Dict[str, Any] = None) -> str:
        """生成缓存键"""
        key_data = {
            "input": customer_input.lower().strip(),
            "skin_type": customer_profile.get("skin_type", ""),
            "budget": customer_profile.get("budget_preference", ""),
            "concerns": sorted(needs_analysis.get("concerns", []) if needs_analysis else [])
        }
        key_string = str(sorted(key_data.items()))
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_cached_recommendation(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """获取缓存的推荐结果"""
        if cache_key in self._recommendation_cache:
            cached_data = self._recommendation_cache[cache_key]
            # 检查TTL
            if get_current_datetime().timestamp() - cached_data["timestamp"] < self._cache_ttl:
                return cached_data["data"]
            else:
                del self._recommendation_cache[cache_key]
        return None
    
    def _cache_recommendation(self, cache_key: str, data: Dict[str, Any]):
        """缓存推荐结果"""
        if len(self._recommendation_cache) >= self._max_cache_size:
            # 移除最旧的条目
            oldest_key = min(self._recommendation_cache.keys(), 
                           key=lambda k: self._recommendation_cache[k]["timestamp"])
            del self._recommendation_cache[oldest_key]
        
        self._recommendation_cache[cache_key] = {
            "data": data,
            "timestamp": get_current_datetime().timestamp()
        }
    
    def _is_simple_query(self, customer_input: str, needs_analysis: Dict[str, Any] = None) -> bool:
        """判断是否为简单查询（可使用快速推荐）"""
        simple_keywords = ["popular", "best", "recommend", "moisturizer", "cleanser"]
        return any(keyword in customer_input.lower() for keyword in simple_keywords)
    
    async def _get_fast_recommendations(self, customer_input: str, customer_profile: Dict[str, Any], 
                                      needs_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """快速推荐（使用预计算结果）"""
        category = needs_analysis.get("product_category", "skincare") if needs_analysis else "skincare"
        
        return {
            "products": self._popular_products.get(category, [])[:3],
            "general_advice": f"这些是我们{category}类别中最受欢迎的产品",
            "recommendation_method": "fast_lookup",
            "agent_id": self.agent_id,
            "confidence": 0.8
        }
    
    async def _get_llm_recommendations(self, customer_input: str, customer_profile: Dict[str, Any], 
                                     needs_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """完整LLM推荐流程"""
        # 准备推荐上下文
        recommendation_context = self._build_recommendation_context(
            customer_profile, needs_analysis
        )
        
        # 获取产品推荐提示词
        prompt = self.prompt_manager.get_prompt(
            "sales",
            "product_recommendation",
            customer_input=customer_input,
            skin_type=customer_profile.get("skin_type", "not specified"),
            main_concerns=", ".join(needs_analysis.get("concerns", []) if needs_analysis else ["general consultation"]),
            lifestyle=customer_profile.get("lifestyle", "not specified"),
            budget_preference=customer_profile.get("budget_preference", "medium"),
            product_context=recommendation_context
        )
        
        # 调用LLM生成推荐
        messages = [{"role": "user", "content": prompt}]
        response = await self.llm_client.chat_completion(messages, temperature=0.7)
        
        # 解析推荐结果
        recommendations = self._parse_recommendation_response(response)
        
        # 添加元数据
        recommendations["agent_id"] = self.agent_id
        recommendations["recommendation_method"] = "llm_powered"
        recommendations["confidence"] = self._calculate_recommendation_confidence(
            customer_profile, needs_analysis
        )
        
        return recommendations
    
    def _init_popular_products(self) -> Dict[str, List[str]]:
        """初始化热门产品数据（生产环境中从数据库加载）"""
        return {
            "skincare": [
                "温和洁面乳 - 适合所有肤质",
                "保湿精华 - 深层水分补充",
                "防晒乳SPF50 - 日常防护必备"
            ],
            "makeup": [
                "气垫粉底液 - 轻透自然",
                "防水睡毛膏 - 持久不晕染",
                "最爱口红 - 多色可选"
            ],
            "fragrance": [
                "清香淡香水 - 日常香气",
                "身体喂嘘喂 - 清新持久"
            ]
        }
    
    def _get_fallback_recommendations(self, customer_profile: Dict[str, Any]) -> Dict[str, Any]:
        """降级推荐（错误情况下使用）"""
        return {
            "products": self._popular_products.get("skincare", [])[:2],
            "general_advice": "我很乐意为您推荐产品。请告诉我更多关于您的需求。",
            "fallback": True,
            "agent_id": self.agent_id,
            "confidence": 0.5
        }
    
    def _analyze_customer_needs(
        self, 
        customer_input: str, 
        customer_profile: Dict[str, Any], 
        intent_analysis: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        分析客户需求
        
        参数:
            customer_input: 客户输入
            customer_profile: 客户档案
            intent_analysis: 意图分析结果
            
        返回:
            Dict[str, Any]: 需求分析结果
        """
        needs = {
            "concerns": [],
            "product_category": "general",
            "urgency": "medium",
            "budget_sensitivity": "medium"
        }
        
        # 从客户输入中提取关键需求
        input_lower = customer_input.lower()
        
        # 识别皮肤问题
        skin_concerns = {
            "acne": ["acne", "pimple", "breakout", "blemish"],
            "dryness": ["dry", "flaky", "tight", "dehydrated"],
            "oily": ["oily", "greasy", "shine", "sebum"],
            "aging": ["wrinkle", "fine line", "aging", "mature"],
            "sensitivity": ["sensitive", "irritated", "red", "reactive"]
        }
        
        for concern, keywords in skin_concerns.items():
            if any(keyword in input_lower for keyword in keywords):
                needs["concerns"].append(concern)
        
        # 识别产品类别
        for category, products in self.product_categories.items():
            if any(product in input_lower for product in products):
                needs["product_category"] = category
                break
        
        # 从意图分析中获取额外信息
        if intent_analysis:
            needs["urgency"] = intent_analysis.get("urgency", "medium")
            if intent_analysis.get("category") != "general":
                needs["product_category"] = intent_analysis.get("category", "general")
        
        # 从客户档案中获取偏好
        if customer_profile:
            if customer_profile.get("budget_preference"):
                needs["budget_sensitivity"] = customer_profile["budget_preference"]
        
        return needs
    
    def _build_recommendation_context(
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
        
        # 品牌信息 (简化)
        context_parts.append(f"Brand focus: {self.tenant_id} premium beauty products")
        
        # 季节性建议 (简化)
        context_parts.append("Current season: Consider hydration for winter, sun protection for summer")
        
        return " | ".join(context_parts)
    
    def _parse_recommendation_response(self, response: str) -> Dict[str, Any]:
        """
        解析LLM推荐响应
        
        参数:
            response: LLM响应文本
            
        返回:
            Dict[str, Any]: 解析后的推荐结果
        """
        # 简化的解析逻辑 - 在真实环境中会更复杂
        recommendations = {
            "products": [],
            "general_advice": response,
            "reasoning": "AI-generated recommendation based on customer profile and needs"
        }
        
        # 尝试从响应中提取产品名称 (简化版本)
        lines = response.split('\n')
        product_lines = [line.strip() for line in lines if any(
            keyword in line.lower() for keyword in ['recommend', 'suggest', 'try', 'perfect']
        )]
        
        if product_lines:
            recommendations["products"] = product_lines[:3]  # 最多3个推荐
        
        return recommendations
    
    def _calculate_recommendation_confidence(
        self, 
        customer_profile: Dict[str, Any], 
        needs_analysis: Dict[str, Any] = None
    ) -> float:
        """
        计算推荐置信度
        
        参数:
            customer_profile: 客户档案
            needs_analysis: 需求分析结果
            
        返回:
            float: 置信度分数 (0.0-1.0)
        """
        confidence = 0.5  # 基础置信度
        
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
    
    def get_product_metrics(self) -> Dict[str, Any]:
        """
        获取产品推荐性能指标
        
        返回:
            Dict[str, Any]: 性能指标信息
        """
        return {
            "total_recommendations": self.processing_stats["messages_processed"],
            "error_rate": self.processing_stats["errors"] / max(1, self.processing_stats["messages_processed"]) * 100,
            "average_processing_time": self.processing_stats["average_response_time"],
            "last_activity": self.processing_stats["last_activity"],
            "supported_categories": list(self.product_categories.keys()),
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id
        }