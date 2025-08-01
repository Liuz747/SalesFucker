"""
Product Expert Agent

AI-powered product recommendation engine for beauty consultations.
Provides expert product knowledge and personalized recommendations.
"""

from typing import Dict, Any, List
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
        
        # Product knowledge base (simplified for now)
        self.product_categories = {
            "skincare": ["cleanser", "moisturizer", "serum", "sunscreen", "toner"],
            "makeup": ["foundation", "concealer", "lipstick", "eyeshadow", "mascara"],
            "fragrance": ["perfume", "body_spray", "essential_oil"],
            "tools": ["brush", "sponge", "applicator", "mirror"]
        }
        
        self.logger.info(f"产品专家智能体初始化完成: {self.agent_id}")
    
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
        使用LLM生成产品推荐
        
        参数:
            customer_input: 客户输入
            customer_profile: 客户档案
            needs_analysis: 需求分析结果
            
        返回:
            Dict[str, Any]: 产品推荐结果
        """
        try:
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
            
        except Exception as e:
            self.logger.error(f"产品推荐生成失败: {e}")
            return {
                "products": [],
                "general_advice": "I'd be happy to help you find the perfect products. Could you share more about your specific needs?",
                "fallback": True,
                "error": str(e),
                "agent_id": self.agent_id
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