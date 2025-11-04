"""
Utilities for adapting sales responses based on sentiment guidance.

This module centralises the strategy selection, candidate generation,
and evaluation flows that were previously embedded in the SalesAgent.
"""

from __future__ import annotations

import json
from typing import Any, Awaitable, Callable, Dict, List, Optional

from core.prompts.templates import (
    AgentType,
    PromptType,
    get_default_prompt,
    get_prompt_for_agent_collaboration,
    get_sales_prompt_by_type,
)
from utils import get_component_logger, to_isoformat


Candidate = Dict[str, Any]


class SalesResponseAdapter:
    """Helper for strategy selection, candidate generation, and evaluation."""

    _STAGE_STRATEGIES: Dict[str, List[Dict[str, str]]] = {
        "awareness": [
            {
                "name": "教育引导型",
                "tone": "professional",
                "approach": "educational",
                "focus": "介绍产品知识和解决方案,建立认知",
            },
            {
                "name": "需求激发型",
                "tone": "warm",
                "approach": "problem-focused",
                "focus": "深入挖掘客户潜在需求和痛点",
            },
            {
                "name": "信任建立型",
                "tone": "friendly",
                "approach": "trust-building",
                "focus": "分享案例和专业见解,建立可信度",
            },
        ],
        "consideration": [
            {
                "name": "对比分析型",
                "tone": "professional",
                "approach": "comparative",
                "focus": "对比不同方案优劣,帮助客户权衡选择",
            },
            {
                "name": "价值强化型",
                "tone": "energetic",
                "approach": "value-driven",
                "focus": "强调产品独特价值和长期收益",
            },
            {
                "name": "个性化推荐型",
                "tone": "warm",
                "approach": "personalized",
                "focus": "基于客户具体情况给出针对性建议",
            },
        ],
        "decision": [
            {
                "name": "促成引导型",
                "tone": "energetic",
                "approach": "action-oriented",
                "focus": "给出明确建议,降低决策门槛",
            },
            {
                "name": "保障强调型",
                "tone": "professional",
                "approach": "assurance-focused",
                "focus": "强调售后保障和风险控制",
            },
            {
                "name": "紧迫感营造型",
                "tone": "friendly",
                "approach": "urgency-building",
                "focus": "适度营造稀缺性和时机感",
            },
        ],
        "retention": [
            {
                "name": "关怀回访型",
                "tone": "warm",
                "approach": "caring",
                "focus": "关注使用体验,提供后续指导",
            },
            {
                "name": "增值服务型",
                "tone": "professional",
                "approach": "service-oriented",
                "focus": "介绍配套产品和增值服务",
            },
            {
                "name": "忠诚培养型",
                "tone": "friendly",
                "approach": "loyalty-building",
                "focus": "分享专属权益,培养长期关系",
            },
        ],
    }

    _PRIORITY_MAP: Dict[str, List[str]] = {
        "awareness": ["教育引导型", "需求激发型", "信任建立型"],
        "consideration": ["个性化推荐型", "对比分析型", "价值强化型"],
        "decision": ["促成引导型", "保障强调型", "紧迫感营造型"],
        "retention": ["关怀回访型", "增值服务型", "忠诚培养型"],
    }

    def __init__(
        self,
        completion_fn: Callable[..., Awaitable[str]],
        logger=None,
        word_limit: int = 130,
    ) -> None:
        self._completion_fn = completion_fn
        self._word_limit = word_limit
        self.logger = logger or get_component_logger(__name__)

    def select_strategies(self, decision_stage: str) -> List[Dict[str, str]]:
        """Return strategy configurations for the given decision stage."""
        prompts = self._STAGE_STRATEGIES.get(
            decision_stage, self._STAGE_STRATEGIES["consideration"]
        )
        self.logger.info(
            "为决策阶段 '%s' 选择了 %d 个提示词变体",
            decision_stage,
            len(prompts),
        )
        return prompts

    async def generate_candidates(
        self,
        prompt_configs: List[Dict[str, str]],
        customer_input: str,
        sentiment_analysis: Dict[str, Any],
        intent_analysis: Dict[str, Any],
        customer_profile: Dict[str, Any],
    ) -> List[Candidate]:
        """Generate candidate responses concurrently."""
        if not prompt_configs:
            return []

        tasks = [
            self._generate_single_candidate(
                config,
                customer_input,
                sentiment_analysis,
                intent_analysis,
                customer_profile,
            )
            for config in prompt_configs
        ]
        self.logger.info("开始并行生成 %d 个候选回复", len(tasks))
        results = await self._gather_with_exceptions(tasks)

        valid_candidates: List[Candidate] = []
        for index, candidate in enumerate(results, start=1):
            if isinstance(candidate, Exception):
                self.logger.warning("候选 %d 生成失败: %s", index, candidate)
                continue
            if candidate and candidate.get("response"):
                valid_candidates.append(candidate)

        self.logger.info(
            "成功生成 %d/%d 个候选回复",
            len(valid_candidates),
            len(prompt_configs),
        )
        return valid_candidates

    async def evaluate_candidates(
        self,
        candidates: List[Candidate],
        customer_input: str,
        sentiment_analysis: Dict[str, Any],
        intent_analysis: Dict[str, Any],
    ) -> Candidate:
        """Evaluate candidate responses and select the best one."""
        if not candidates:
            raise ValueError("没有可评估的候选回复")

        if len(candidates) == 1:
            self.logger.info("只有一个候选,直接返回")
            return {
                **candidates[0],
                "score": 1.0,
                "reasoning": "唯一候选",
            }

        prompt_template = get_default_prompt(
            AgentType.SALES,
            PromptType.SALES_EVALUATION,
        )
        prompt = prompt_template.format(
            customer_input=customer_input,
            sentiment=sentiment_analysis.get("sentiment", "neutral"),
            satisfaction=sentiment_analysis.get("satisfaction", "unknown"),
            decision_stage=intent_analysis.get("decision_stage", "awareness"),
            intent=intent_analysis.get("intent", "browsing"),
            candidates_text=self._build_candidates_text(candidates),
            candidate_count=len(candidates),
        )

        messages = [
            {
                "role": "system",
                "content": "你是美妆销售领域的资深专家评委,擅长评估销售话术质量",
            },
            {"role": "user", "content": prompt},
        ]

        evaluation_result = await self._completion_fn(
            messages,
            temperature=0.3,
            max_tokens=300,
        )
        if not evaluation_result:
            raise ValueError("评估 LLM 返回空结果")

        eval_data = self._parse_evaluation_result(evaluation_result)
        best_index = max(0, min(len(candidates) - 1, eval_data.get("index", 0)))
        best_candidate = candidates[best_index]

        self.logger.info(
            "选择了候选 %d: %s, 评分: %s",
            best_index + 1,
            best_candidate["config"]["name"],
            eval_data.get("score", "N/A"),
        )

        return {
            **best_candidate,
            "evaluation_score": eval_data.get("score", 0),
            "evaluation_reasoning": eval_data.get("reasoning", ""),
            "detailed_scores": eval_data.get("scores", {}),
            "total_candidates": len(candidates),
        }

    def heuristic_selection(
        self,
        candidates: List[Candidate],
        sentiment_analysis: Dict[str, Any],
        intent_analysis: Dict[str, Any],
    ) -> Candidate:
        """Fallback selection using heuristic rules."""
        if not candidates:
            raise ValueError("没有候选回复可供选择")

        decision_stage = intent_analysis.get("decision_stage", "consideration")
        priorities = self._PRIORITY_MAP.get(
            decision_stage, self._PRIORITY_MAP["consideration"]
        )

        for priority_name in priorities:
            for candidate in candidates:
                if candidate["config"]["name"] == priority_name:
                    self.logger.info("启发式选择: %s", priority_name)
                    return {
                        **candidate,
                        "evaluation_score": 75,
                        "evaluation_reasoning": f"基于决策阶段({decision_stage})的启发式选择",
                        "selection_method": "heuristic",
                    }

        self.logger.info("使用第一个候选作为默认")
        return {
            **candidates[0],
            "evaluation_score": 70,
            "evaluation_reasoning": "默认选择",
            "selection_method": "default",
        }

    async def _generate_single_candidate(
        self,
        config: Dict[str, str],
        customer_input: str,
        sentiment_analysis: Dict[str, Any],
        intent_analysis: Dict[str, Any],
        customer_profile: Dict[str, Any],
    ) -> Candidate:
        prompt_template = get_default_prompt(
            AgentType.SALES,
            PromptType.SALES_STRATEGY_VARIANT,
        )

        intent_profile = intent_analysis.get("customer_profile", {}) or {}
        prompt = prompt_template.format(
            strategy_name=config["name"],
            tone=config["tone"],
            approach=config["approach"],
            focus=config["focus"],
            customer_input=customer_input,
            sentiment=sentiment_analysis.get("sentiment", "neutral"),
            sentiment_score=sentiment_analysis.get("score", 0.0),
            satisfaction=sentiment_analysis.get("satisfaction", "unknown"),
            emotions=", ".join(sentiment_analysis.get("emotions", ["无明显情绪"])),
            intent=intent_analysis.get("intent", "browsing"),
            decision_stage=intent_analysis.get("decision_stage", "awareness"),
            urgency=sentiment_analysis.get("urgency", "medium"),
            skin_type=customer_profile.get("skin_type", "未知"),
            skin_concerns=", ".join(
                intent_profile.get("skin_concerns", ["一般咨询"])
            ),
            budget_range=customer_profile.get("budget_range", "中等"),
            experience_level=intent_profile.get("experience_level", "中级"),
            word_limit=self._word_limit,
        )

        messages = [
            {
                "role": "system",
                "content": "你是专业的美妆销售顾问,善于根据不同策略调整沟通方式",
            },
            {"role": "user", "content": prompt},
        ]

        response = await self._completion_fn(
            messages,
            temperature=0.9,
            max_tokens=400,
        )
        if not response:
            raise ValueError("LLM 返回空响应")

        return {
            "response": response,
            "config": config,
            "metadata": {
                "decision_stage": intent_analysis.get("decision_stage", "awareness"),
                "sentiment": sentiment_analysis.get("sentiment", "neutral"),
                "generated_at": to_isoformat(),
            },
        }

    async def _gather_with_exceptions(
        self,
        tasks: List[Awaitable[Any]],
    ) -> List[Any]:
        # asyncio.gather with return_exceptions=True while keeping local import
        import asyncio

        return await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    def _build_candidates_text(candidates: List[Candidate]) -> str:
        parts = []
        for index, candidate in enumerate(candidates, start=1):
            parts.append(
                f"\n\n【候选回复 {index}】({candidate['config']['name']})\n{candidate['response']}"
            )
        return "".join(parts)

    @staticmethod
    def _parse_evaluation_result(raw_result: str) -> Dict[str, Any]:
        text = raw_result.strip()
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in text:
            text = text.split("```", 1)[1].split("```", 1)[0].strip()

        data = json.loads(text)
        index = int(data.get("best_candidate", 1)) - 1
        return {
            "index": index,
            "score": data.get("score", 0),
            "reasoning": data.get("reasoning", ""),
            "scores": data.get("scores", {}),
        }

    # ===== 新增的响应生成方法 =====

    async def generate_sentiment_based_response(
        self,
        customer_input: str,
        sentiment_analysis: Dict[str, Any],
        intent_analysis: Dict[str, Any],
        state: dict,
    ) -> str:
        """
        基于情感分析结果生成个性化响应（增强版）

        整合了原有的单一生成逻辑和候选生成评估逻辑
        """
        try:
            decision_stage = intent_analysis.get("decision_stage", "consideration")
            self.logger.info(f"客户决策阶段: {decision_stage}")

            # 使用候选生成和评估机制
            prompt_configs = self.select_strategies(decision_stage)
            customer_profile = state.get("customer_profile", {})

            # 生成候选回复
            candidates = await self.generate_candidates(
                prompt_configs,
                customer_input,
                sentiment_analysis,
                intent_analysis,
                customer_profile,
            )

            if not candidates:
                self.logger.warning("候选生成失败，使用单一生成逻辑")
                return await self._generate_single_sentiment_response(
                    customer_input, sentiment_analysis, intent_analysis, state
                )

            # 评估候选并选择最佳
            try:
                best_result = await self.evaluate_candidates(
                    candidates,
                    customer_input,
                    sentiment_analysis,
                    intent_analysis,
                )
            except Exception as exc:
                self.logger.error(f"候选评估失败: {exc}, 使用启发式方案")
                best_result = self.heuristic_selection(
                    candidates,
                    sentiment_analysis,
                    intent_analysis,
                )

            # 更新状态中的候选信息
            self._update_response_candidates_state(state, candidates, best_result)

            return best_result["response"]

        except Exception as e:
            self.logger.error(f"情感驱动响应生成失败: {e}")
            return self._generate_fallback_response("consultation")

    async def generate_standard_response(
        self,
        customer_input: str,
        needs: dict,
        stage: str,
        strategy: dict,
        state: dict
    ) -> str:
        """
        生成标准销售响应（不基于情感分析）

        使用templates.py中的标准模板
        """
        try:
            # 使用新的提示词服务
            prompt_template = get_sales_prompt_by_type(
                PromptType.SALES_STANDARD_RESPONSE,
                {
                    "customer_input": customer_input,
                    "skin_type": state.get("customer_profile", {}).get("skin_type", "未知"),
                    "skin_concerns": ", ".join(needs.get("skin_concerns", ["一般咨询"])),
                    "budget_range": state.get("customer_profile", {}).get("budget_range", "中等"),
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

            response = await self._completion_fn(
                messages,
                temperature=0.8,
                max_tokens=512
            )

            if response:
                return response
            else:
                self.logger.warning("标准响应生成失败，使用降级响应")
                return self._generate_fallback_response(stage)

        except Exception as e:
            self.logger.error(f"标准响应生成失败: {e}")
            return self._generate_fallback_response(stage)

    async def generate_collaborative_response(
        self,
        customer_input: str,
        sentiment_guidance: dict,
        state: dict
    ) -> str:
        """
        使用共享提示词模块生成增强响应

        整合了原有的generate_enhanced_response_with_shared_prompts逻辑
        """
        try:
            # 提取情感映射和响应适配信息
            emotion_mapping = sentiment_guidance.get("emotion_mapping", {})
            response_adaptation = sentiment_guidance.get("response_adaptation", {})
            contextual_insights = sentiment_guidance.get("contextual_insights", {})

            # 使用协作提示词模板
            collaboration_prompt = get_prompt_for_agent_collaboration(
                AgentType.SALES,
                PromptType.SHARED_RESPONSE_ADAPTATION,
                customer_input=customer_input,
                current_emotion=emotion_mapping.get("current_emotion", "neutral"),
                purchase_intent=state.get("purchase_intent", "browsing"),
                decision_stage=state.get("decision_stage", "awareness"),
                content_focus=response_adaptation.get("content_focus", "基础咨询"),
                style_adjustment=response_adaptation.get("style_adjustment", "适度详细"),
                detail_level=response_adaptation.get("detail_level", "medium"),
                tone_requirement=emotion_mapping.get("recommended_tone", "专业友好"),
                next_actions=", ".join(contextual_insights.get("next_best_actions", []))
            )

            # 构建完整的上下文提示词
            enhanced_prompt = f"""
{collaboration_prompt}

## 当前任务上下文
客户输入：{customer_input}

## Sentiment Agent指导建议
情感状态：{emotion_mapping.get("current_emotion", "neutral")}
推荐语调：{emotion_mapping.get("recommended_tone", "专业友好")}
推荐方法：{emotion_mapping.get("recommended_approach", "教育引导")}
内容重点：{response_adaptation.get("content_focus", "基础咨询")}
风格调整：{response_adaptation.get("style_adjustment", "适度详细")}

## 关键考虑因素
{chr(10).join([f"- {consideration}" for consideration in contextual_insights.get("key_considerations", [])])}

## 建议的下一步行动
{chr(10).join([f"- {action}" for action in contextual_insights.get("next_best_actions", [])])}

请基于以上指导和协作原则，为客户提供个性化的专业建议。确保：
1. 严格遵循情感状态调整语调和方式
2. 应用推荐的销售方法和内容重点
3. 体现关键考虑因素
4. 朝着建议的下一步行动引导对话

回复要求：自然流畅的中文，体现专业性和亲和力。
"""

            # 调用LLM生成响应
            messages = [{"role": "user", "content": enhanced_prompt}]
            response = await self._completion_fn(
                messages,
                temperature=0.7,
                max_tokens=600
            )

            response_content = response.strip() if response else ""
            self.logger.info("成功使用共享提示词模块生成增强响应")
            return response_content

        except Exception as e:
            self.logger.error(f"共享提示词增强响应生成失败: {e}")
            return self._generate_fallback_response("standard")

    async def generate_response_from_context(
        self,
        customer_input: str,
        context: Dict[str, Any]
    ) -> str:
        """
        根据完整上下文生成响应的主要入口点

        根据上下文中的情感分析结果决定使用哪种响应生成策略
        """
        try:
            sentiment_analysis = context.get("sentiment_analysis", {})
            intent_analysis = context.get("intent_analysis", {})
            needs = context.get("needs", {})
            strategy = context.get("strategy", {})
            stage = context.get("stage", "consultation")

            # 检查是否有情感分析结果
            if sentiment_analysis and sentiment_analysis.get("sentiment"):
                # 使用情感驱动的响应生成
                return await self.generate_sentiment_based_response(
                    customer_input, sentiment_analysis, intent_analysis, context
                )
            else:
                # 使用标准响应生成
                return await self.generate_standard_response(
                    customer_input, needs, stage, strategy, context
                )

        except Exception as e:
            self.logger.error(f"响应生成失败: {e}")
            return self._generate_fallback_response("consultation")

    # ===== 辅助方法 =====

    async def _generate_single_sentiment_response(
        self,
        customer_input: str,
        sentiment_analysis: dict,
        intent_analysis: dict,
        state: dict
    ) -> str:
        """
        单一生成逻辑（降级方案）

        使用templates.py中的CHAT_WITH_SENTIMENT模板
        """
        try:
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
                    "skin_type": state.get("customer_profile", {}).get("skin_type", "未知"),
                    "skin_concerns": ", ".join(intent_analysis.get("customer_profile", {}).get("skin_concerns", ["一般咨询"])),
                    "budget_range": state.get("customer_profile", {}).get("budget_range", "中等"),
                    "experience_level": intent_analysis.get("customer_profile", {}).get("experience_level", "中级"),
                    "intent": intent_analysis.get("intent", "browsing"),
                    "decision_stage": intent_analysis.get("decision_stage", "awareness")
                }
            )

            messages = [
                {"role": "system", "content": "你是专业的美妆销售顾问，善于根据客户情绪状态调整沟通方式"},
                {"role": "user", "content": prompt_template}
            ]

            response = await self._completion_fn(
                messages,
                temperature=0.8,
                max_tokens=512
            )

            return response or self._generate_fallback_response("consultation")

        except Exception as e:
            self.logger.error(f"单一生成逻辑失败: {e}")
            return self._generate_fallback_response("consultation")

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

    def _generate_fallback_response(self, stage: str) -> str:
        """生成降级响应"""
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

    def _update_response_candidates_state(self, state: dict, candidates: List[Candidate], best_result: Candidate) -> None:
        """更新状态中的候选响应信息"""
        state["response_candidates"] = {
            "total": len(candidates),
            "selected": best_result["config"]["name"],
            "evaluation_score": best_result.get("evaluation_score", 0),
            "all_candidates": [
                {
                    "name": candidate["config"]["name"],
                    "response_preview": candidate["response"][:50] + "...",
                }
                for candidate in candidates
            ],
        }
        if best_result.get("evaluation_reasoning"):
            state["response_candidates"]["evaluation_reasoning"] = best_result["evaluation_reasoning"]

    def integrate_sentiment_guidance(self, state: dict, sentiment_guidance: dict) -> dict:
        """
        将sentiment agent的指导建议整合到sales agent的状态中

        整合了原有的integrate_sentiment_guidance逻辑
        """
        try:
            # 提取关键指导信息
            emotion_mapping = sentiment_guidance.get("emotion_mapping", {})
            response_adaptation = sentiment_guidance.get("response_adaptation", {})
            contextual_insights = sentiment_guidance.get("contextual_insights", {})

            # 更新sales agent的策略状态
            state["sales_guidance"] = {
                "recommended_tone": emotion_mapping.get("recommended_tone", "专业友好"),
                "recommended_approach": emotion_mapping.get("recommended_approach", "教育引导"),
                "content_focus": response_adaptation.get("content_focus", "基础咨询"),
                "urgency_level": response_adaptation.get("urgency_level", "medium"),
                "key_considerations": contextual_insights.get("key_considerations", []),
                "next_best_actions": contextual_insights.get("next_best_actions", []),
                "customer_state_summary": contextual_insights.get("customer_state_summary", ""),
                "guidance_timestamp": to_isoformat()
            }

            # 更新销售策略优先级
            if emotion_mapping.get("recommended_approach"):
                state["strategy_priority"] = emotion_mapping.get("recommended_approach")

            # 设置响应风格偏好
            if response_adaptation.get("style_adjustment"):
                state["response_style"] = response_adaptation.get("style_adjustment")

            self.logger.info("成功整合sentiment agent指导建议到sales状态")
            return state

        except Exception as e:
            self.logger.error(f"整合sentiment指导失败: {e}")
            return state
