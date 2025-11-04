"""
Sales Agent 统一响应生成服务

该服务为SalesAgent提供统一的响应生成接口，整合了情感驱动响应、
标准响应和协作响应的生成逻辑，简化了销售智能体的调用方式。

主要功能:
- 统一的响应生成入口
- 多种响应策略的协调
- 上下文管理和错误处理
- 性能监控和日志记录
"""

from typing import Dict, Any, Optional, List
from uuid import uuid4
from utils import get_component_logger

from core.prompts.templates import (
    get_sales_prompt_by_type,
    get_prompt_for_agent_collaboration,
    AgentType,
    PromptType
)
from infra.runtimes import CompletionsRequest
from libs.types import Message


class SalesResponseService:
    """
    统一的响应生成服务

    负责协调各种响应生成策略，为SalesAgent提供简洁的接口。
    """

    def __init__(self, completion_fn, llm_provider: str = "openai", llm_model: str = "openai/gpt-5-chat"):
        self.completion_fn = completion_fn
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.logger = get_component_logger(__name__)

        # 响应生成统计
        self.stats = {
            "total_requests": 0,
            "successful_responses": 0,
            "failed_responses": 0,
            "average_response_time": 0.0
        }

    async def generate_response(
        self,
        customer_input: str,
        context: Dict[str, Any],
        strategy: str = "auto"
    ) -> str:
        """
        统一的响应生成入口

        根据上下文和策略生成销售响应

        参数:
            customer_input: 客户输入
            context: 完整的上下文信息
            strategy: 响应策略 ("auto", "sentiment_driven", "standard", "collaborative")

        返回:
            str: 生成的销售响应
        """
        import time
        start_time = time.time()

        try:
            self.stats["total_requests"] += 1
            self.logger.info(f"开始生成响应，策略: {strategy}")

            # 根据策略选择响应生成方法
            if strategy == "auto":
                response = await self._generate_auto_response(customer_input, context)
            elif strategy == "sentiment_driven":
                response = await self._generate_sentiment_driven_response(customer_input, context)
            elif strategy == "standard":
                response = await self._generate_standard_response(customer_input, context)
            elif strategy == "collaborative":
                response = await self._generate_collaborative_response(customer_input, context)
            else:
                raise ValueError(f"不支持的响应策略: {strategy}")

            # 更新统计信息
            self.stats["successful_responses"] += 1
            response_time = time.time() - start_time
            self.stats["average_response_time"] = (
                (self.stats["average_response_time"] * (self.stats["successful_responses"] - 1) + response_time)
                / self.stats["successful_responses"]
            )

            self.logger.info(f"响应生成成功，耗时: {response_time:.2f}秒")
            return response

        except Exception as e:
            self.stats["failed_responses"] += 1
            self.logger.error(f"响应生成失败: {e}")

            # 降级响应
            return self._get_fallback_response(context.get("stage", "consultation"))

    async def _generate_auto_response(
        self,
        customer_input: str,
        context: Dict[str, Any]
    ) -> str:
        """
        自动选择最合适的响应策略

        根据上下文中的情感分析结果自动选择响应策略
        """
        sentiment_analysis = context.get("sentiment_analysis", {})

        if sentiment_analysis and sentiment_analysis.get("sentiment"):
            # 有情感分析结果，使用情感驱动响应
            return await self._generate_sentiment_driven_response(customer_input, context)
        else:
            # 没有情感分析结果，使用标准响应
            return await self._generate_standard_response(customer_input, context)

    async def _generate_sentiment_driven_response(
        self,
        customer_input: str,
        context: Dict[str, Any]
    ) -> str:
        """
        基于情感分析的响应生成

        使用情感分析结果来调整响应的语调、内容和风格
        """
        try:
            sentiment_analysis = context.get("sentiment_analysis", {})
            intent_analysis = context.get("intent_analysis", {})
            stage = context.get("stage", "consultation")

            # 获取情感驱动的聊天提示词
            prompt_template = get_sales_prompt_by_type(
                PromptType.CHAT_WITH_SENTIMENT,
                {
                    "customer_input": customer_input,
                    "sentiment": sentiment_analysis.get("sentiment", "neutral"),
                    "sentiment_score": sentiment_analysis.get("score", 0.0),
                    "satisfaction": sentiment_analysis.get("satisfaction", "unknown"),
                    "urgency": sentiment_analysis.get("urgency", "medium"),
                    "emotions": ", ".join(sentiment_analysis.get("emotions", ["无明显情绪"])),
                    "skin_type": context.get("customer_profile", {}).get("skin_type", "未知"),
                    "skin_concerns": ", ".join(intent_analysis.get("customer_profile", {}).get("skin_concerns", ["一般咨询"])),
                    "budget_range": context.get("customer_profile", {}).get("budget_range", "中等"),
                    "experience_level": intent_analysis.get("customer_profile", {}).get("experience_level", "中级"),
                    "intent": intent_analysis.get("intent", "browsing"),
                    "decision_stage": intent_analysis.get("decision_stage", "awareness")
                }
            )

            messages = [
                {"role": "system", "content": "你是专业的美妆销售顾问，善于根据客户情绪状态调整沟通方式"},
                {"role": "user", "content": prompt_template}
            ]

            response = await self.completion_fn(
                messages,
                temperature=0.8,
                max_tokens=512
            )

            return response or self._get_fallback_response(stage)

        except Exception as e:
            self.logger.error(f"情感驱动响应生成失败: {e}")
            return self._get_fallback_response(context.get("stage", "consultation"))

    async def _generate_standard_response(
        self,
        customer_input: str,
        context: Dict[str, Any]
    ) -> str:
        """
        标准销售响应生成

        使用标准的销售对话模板生成响应
        """
        try:
            needs = context.get("needs", {})
            strategy = context.get("strategy", {})
            stage = context.get("stage", "consultation")

            # 获取标准销售响应提示词
            prompt_template = get_sales_prompt_by_type(
                PromptType.SALES_STANDARD_RESPONSE,
                {
                    "customer_input": customer_input,
                    "skin_type": context.get("customer_profile", {}).get("skin_type", "未知"),
                    "skin_concerns": ", ".join(needs.get("skin_concerns", ["一般咨询"])),
                    "budget_range": context.get("customer_profile", {}).get("budget_range", "中等"),
                    "experience_level": needs.get("experience_level", "中级"),
                    "tone": strategy.get("tone", "friendly"),
                    "tone_description": self._get_tone_description(strategy.get("tone", "friendly")),
                    "approach": strategy.get("approach", "咨询式"),
                    "stage": stage,
                }
            )

            messages = [
                {"role": "system", "content": "你是专业的美妆销售顾问"},
                {"role": "user", "content": prompt_template}
            ]

            response = await self.completion_fn(
                messages,
                temperature=0.8,
                max_tokens=512
            )

            return response or self._get_fallback_response(stage)

        except Exception as e:
            self.logger.error(f"标准响应生成失败: {e}")
            return self._get_fallback_response(context.get("stage", "consultation"))

    async def _generate_collaborative_response(
        self,
        customer_input: str,
        context: Dict[str, Any]
    ) -> str:
        """
        协作响应生成

        使用多个智能体协作的方式来生成响应
        """
        try:
            sentiment_guidance = context.get("sentiment_guidance", {})

            # 获取协作提示词
            collaboration_prompt = get_prompt_for_agent_collaboration(
                AgentType.SALES,
                PromptType.SHARED_RESPONSE_ADAPTATION,
                customer_input=customer_input,
                current_emotion=sentiment_guidance.get("emotion_mapping", {}).get("current_emotion", "neutral"),
                purchase_intent=context.get("purchase_intent", "browsing"),
                decision_stage=context.get("decision_stage", "awareness"),
                content_focus=sentiment_guidance.get("response_adaptation", {}).get("content_focus", "基础咨询"),
                style_adjustment=sentiment_guidance.get("response_adaptation", {}).get("style_adjustment", "适度详细"),
                detail_level=sentiment_guidance.get("response_adaptation", {}).get("detail_level", "medium"),
                tone_requirement=sentiment_guidance.get("emotion_mapping", {}).get("recommended_tone", "专业友好"),
                next_actions=", ".join(sentiment_guidance.get("contextual_insights", {}).get("next_best_actions", []))
            )

            # 构建完整的上下文提示词
            enhanced_prompt = f"""
{collaboration_prompt}

## 当前任务上下文
客户输入：{customer_input}

## Sentiment Agent指导建议
情感状态：{sentiment_guidance.get('emotion_mapping', {}).get('current_emotion', 'neutral')}
推荐语调：{sentiment_guidance.get('emotion_mapping', {}).get('recommended_tone', '专业友好')}
推荐方法：{sentiment_guidance.get('emotion_mapping', {}).get('recommended_approach', '教育引导')}
内容重点：{sentiment_guidance.get('response_adaptation', {}).get('content_focus', '基础咨询')}
风格调整：{sentiment_guidance.get('response_adaptation', {}).get('style_adjustment', '适度详细')}

## 关键考虑因素
{chr(10).join([f"- {consideration}" for consideration in sentiment_guidance.get('contextual_insights', {}).get('key_considerations', [])])}

## 建议的下一步行动
{chr(10).join([f"- {action}" for action in sentiment_guidance.get('contextual_insights', {}).get('next_best_actions', [])])}

请基于以上指导和协作原则，为客户提供个性化的专业建议。确保：
1. 严格遵循情感状态调整语调和方式
2. 应用推荐的销售方法和内容重点
3. 体现关键考虑因素
4. 朝着建议的下一步行动引导对话

回复要求：自然流畅的中文，体现专业性和亲和力。
"""

            messages = [{"role": "user", "content": enhanced_prompt}]

            response = await self.completion_fn(
                messages,
                temperature=0.7,
                max_tokens=600
            )

            return response.strip() if response else self._get_fallback_response("standard")

        except Exception as e:
            self.logger.error(f"协作响应生成失败: {e}")
            return self._get_fallback_response("standard")

    def _get_tone_description(self, tone: str) -> str:
        """获取语调描述"""
        tone_descriptions = {
            "sophisticated": "elegant and refined",
            "energetic": "enthusiastic and exciting",
            "professional": "expert and authoritative",
            "warm": "caring and personal",
            "friendly": "approachable and helpful"
        }
        return tone_descriptions.get(tone, "professional and helpful")

    def _get_fallback_response(self, stage: str) -> str:
        """获取降级响应"""
        fallback_responses = {
            "greeting": "Hello! Welcome! I'm excited to help you find the perfect beauty products today. What brings you here?",
            "consultation": "I'd love to help you find products that work perfectly for your needs. Could you tell me more about what you're looking for?",
            "standard": "Thank you for your interest! How can I help you with your beauty needs today?",
            "decision": "I understand this is an important decision. Let me help you with any questions you might have.",
            "awareness": "Great to connect with you! I'm here to help you discover the perfect beauty solutions for your needs.",
            "consideration": "I appreciate your interest in our products. Let me provide you with detailed information to help with your decision.",
            "retention": "It's wonderful to see you again! I'm here to ensure you're getting the most from your beauty products."
        }
        return fallback_responses.get(stage, "Thank you for your interest! How can I help you with your beauty needs today?")

    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        success_rate = (self.stats["successful_responses"] / max(1, self.stats["total_requests"])) * 100

        return {
            "total_requests": self.stats["total_requests"],
            "successful_responses": self.stats["successful_responses"],
            "failed_responses": self.stats["failed_responses"],
            "success_rate": f"{success_rate:.1f}%",
            "average_response_time": f"{self.stats['average_response_time']:.2f}s",
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model
        }

    def reset_stats(self) -> None:
        """重置性能统计"""
        self.stats = {
            "total_requests": 0,
            "successful_responses": 0,
            "failed_responses": 0,
            "average_response_time": 0.0
        }
        self.logger.info("性能统计已重置")


# 导出便利函数
__all__ = ["SalesResponseService"]