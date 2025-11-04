"""
销售智能体 - 轻量级核心模块

该模块作为销售智能体的核心，遵循模块化设计原则。
专注于智能体核心逻辑，将模板、策略等功能分离到专门模块。

核心功能:
- 智能体核心逻辑
- 对话协调和状态管理
- 模块间集成和错误处理
- LangGraph工作流节点处理
"""

from typing import Dict, Any, Optional, List, Union
from uuid import uuid4

from ..base import BaseAgent
from .sales_strategies import get_sales_strategies, analyze_customer_segment, get_strategy_for_segment, adapt_strategy_to_context
from .response_service import SalesResponseService
from core.agents.sentiment import SalesResponseAdapter
from utils import to_isoformat
from config import mas_config
from infra.runtimes import CompletionsRequest
from libs.types import Message


class SalesAgent(BaseAgent):
    """
    销售智能体 - 核心控制器
    
    负责协调各个销售模块，保持轻量级核心设计。
    
    职责:
    - 智能体生命周期管理
    - 模块间协调和集成
    - 对话状态管理
    - 错误处理和降级
    """
    
    def __init__(self):
        # 简化初始化
        super().__init__()

        # Strategy management
        self.sales_strategies = get_sales_strategies()

        # 使用配置文件中的默认provider和对应的模型
        self.llm_provider = mas_config.DEFAULT_LLM_PROVIDER 

        # 根据provider选择合适的模型
        if self.llm_provider == "openrouter":
            self.llm_model = "google/gemini-2.5-flash-preview-09-2025"  # openrouter中可用的模型
        elif self.llm_provider == "zenmux":
            self.llm_model = "openai/gpt-5-chat"  # zenmux中的模型
        else:
            self.llm_model = "gpt-4o-mini"  # 默认OpenAI模型

        # 统一响应生成服务 - 管理所有响应生成逻辑
        self.response_service = SalesResponseService(
            completion_fn=self._invoke_text_completion,
            llm_provider=self.llm_provider,
            llm_model=self.llm_model
        )

        # 兼容性：保留response_adapter以支持现有代码
        self.response_adapter = SalesResponseAdapter(
            completion_fn=self._invoke_text_completion,
            logger=self.logger,
        )

        self.logger.info(f"销售智能体初始化完成: {self.agent_id}, 重构后的模块化架构")

    async def _invoke_text_completion(
        self,
        messages: List[Union[Message, dict[str, str]]],
        *,
        temperature: float,
        max_tokens: Optional[int] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """构造统一的 CompletionsRequest 并返回文本内容。"""
        normalized_messages: List[Message] = []
        for message in messages:
            if isinstance(message, Message):
                normalized_messages.append(message)
            else:
                normalized_messages.append(
                    Message(role=message["role"], content=message["content"])
                )

        request = CompletionsRequest(
            id=uuid4(),
            provider=(provider or self.llm_provider),
            model=(model or self.llm_model),
            temperature=temperature,
            max_tokens=max_tokens,
            messages=normalized_messages,
        )

        llm_response = await self.invoke_llm(request)

        if llm_response and isinstance(llm_response.content, str):
            return llm_response.content

        return "" if not llm_response else str(llm_response.content)
    
    
    async def process_conversation(self, state: dict) -> dict:
        """
        处理对话状态（LangGraph工作流节点）

        重构后的简化的对话处理逻辑，专注于流程控制和状态管理。
        响应生成逻辑委托给response_adapter。

        参数:
            state: 当前对话状态

        返回:
            ThreadState: 更新后的对话状态
        """
        try:
            customer_input = state.get("customer_input", "")

            # 从IntentAnalysisAgent获取增强的客户分析数据
            intent_analysis = state.get("intent_analysis", {}) or {}
            customer_profile_data = intent_analysis.get("customer_profile", {})

            # 提取客户需求信息 (来自LLM分析)
            needs = {
                "skin_concerns": customer_profile_data.get("skin_concerns", []),
                "product_interests": customer_profile_data.get("product_interests", []),
                "urgency": customer_profile_data.get("urgency", "normal"),
                "experience_level": customer_profile_data.get("experience_level", "intermediate"),
                "budget_signals": customer_profile_data.get("budget_signals", [])
            }

            # 获取对话阶段 (来自LLM分析)
            stage_value = intent_analysis.get("conversation_stage", "consultation")

            # 使用LLM提取的信息丰富客户档案
            state.setdefault("customer_profile", {})
            if customer_profile_data.get("skin_type_indicators"):
                state["customer_profile"]["inferred_skin_type"] = customer_profile_data["skin_type_indicators"][0]
            if customer_profile_data.get("budget_signals"):
                state["customer_profile"]["budget_preference"] = customer_profile_data["budget_signals"][0]
            if customer_profile_data.get("experience_level"):
                state["customer_profile"]["experience_level"] = customer_profile_data["experience_level"]

            # 客户细分和策略选择
            customer_segment = analyze_customer_segment(state["customer_profile"])
            strategy = get_strategy_for_segment(customer_segment)

            # 根据上下文调整策略
            context = {
                "sentiment": (state.get("sentiment_analysis", {}) or {}).get("sentiment", "neutral"),
                "urgency": needs.get("urgency", "normal"),
                "purchase_intent": state.get("purchase_intent", "browsing")
            }
            adapted_strategy = adapt_strategy_to_context(strategy, context)

            # 构建完整的响应生成上下文
            response_context = {
                "customer_input": customer_input,
                "sentiment_analysis": state.get("sentiment_analysis", {}),
                "intent_analysis": intent_analysis,
                "needs": needs,
                "strategy": adapted_strategy,
                "stage": stage_value,
                "customer_profile": state["customer_profile"],
                "purchase_intent": state.get("purchase_intent", "browsing"),
                "decision_stage": intent_analysis.get("decision_stage", "awareness")
            }

            # 使用新的统一响应生成服务
            response = await self.response_service.generate_response(
                customer_input, response_context, strategy="auto"
            )

            # 更新对话状态
            state["sales_response"] = response
            state.setdefault("active_agents", []).append(self.agent_id)
            state.setdefault("conversation_history", []).extend([
                {"role": "user", "content": customer_input},
                {"role": "assistant", "content": response}
            ])

            return state

        except Exception as e:
            self.logger.error(f"Agent processing failed: {e}", exc_info=True)
            state["error_state"] = "sales_processing_error"
            return state
    
    # ===== 新增的便利方法 =====
    # 这些方法现在委托给response_adapter和templates模块

    async def get_greeting_message(self, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        获取个性化问候消息（委托给templates模块）

        参数:
            context: 上下文信息

        返回:
            str: 个性化问候消息
        """
        try:
            from core.prompts.templates import get_greeting_prompt
            return get_greeting_prompt(context or {})
        except Exception as e:
            self.logger.warning(f"获取问候消息失败: {e}")
            return "您好！欢迎来到我们的美妆专柜，有什么可以帮助您的吗？"

    async def get_product_recommendation_prompt(self, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        获取产品推荐提示词（委托给templates模块）

        参数:
            context: 推荐上下文信息

        返回:
            str: 产品推荐提示词
        """
        try:
            from core.prompts.templates import get_product_recommendation_prompt
            return get_product_recommendation_prompt(context or {})
        except Exception as e:
            self.logger.warning(f"获取产品推荐模板失败: {e}")
            return None

    async def get_objection_handling_prompt(self, objection_type: str, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        获取异议处理提示词（委托给templates模块）

        参数:
            objection_type: 异议类型
            context: 异议上下文信息

        返回:
            str: 异议处理提示词
        """
        try:
            from core.prompts.templates import get_objection_handling_prompt
            full_context = {'objection_type': objection_type}
            if context:
                full_context.update(context)
            return get_objection_handling_prompt(full_context)
        except Exception as e:
            self.logger.warning(f"获取异议处理提示词失败: {e}")

            # 降级处理：基础异议回应
            basic_responses = {
                'price': '我理解您对价格的考虑。让我为您介绍一下这个产品的价值所在...',
                'quality': '您的担心很有道理。让我详细为您介绍产品的品质保证...',
                'need': '我明白您可能觉得不太需要。让我们一起分析一下您的实际情况...',
                'trust': '建立信任确实需要时间。让我为您展示一些客户的真实反馈...',
                'timing': '时机确实很重要。我们来看看什么时候开始使用效果最佳...'
            }
            return basic_responses.get(objection_type, '我理解您的顾虑，让我们一起来讨论一下...')

    def integrate_sentiment_guidance(self, state: dict, sentiment_guidance: dict) -> dict:
        """
        将sentiment agent的指导建议整合到sales agent的状态中（委托给response_adapter）

        参数:
            state: 当前对话状态
            sentiment_guidance: sentiment agent提供的指导建议

        返回:
            dict: 更新后的状态
        """
        try:
            return self.response_adapter.integrate_sentiment_guidance(state, sentiment_guidance)
        except Exception as e:
            self.logger.error(f"整合sentiment指导失败: {e}")
            return state

    async def generate_enhanced_response_with_shared_prompts(
            self,
            customer_input: str,
            sentiment_guidance: dict,
            state: dict
    ) -> str:
        """
        使用共享提示词模块生成增强响应（委托给response_adapter）

        参数:
            customer_input: 客户输入
            sentiment_guidance: sentiment agent提供的指导建议
            state: 对话状态

        返回:
            str: 增强的销售响应
        """
        try:
            return await self.response_adapter.generate_collaborative_response(
                customer_input, sentiment_guidance, state
            )
        except Exception as e:
            self.logger.error(f"生成增强响应失败: {e}")
            return "我操，太HIFI了"

    def get_shared_prompt_summary(self) -> dict:
        """
        获取当前可用共享提示词的摘要信息

        返回:
            dict: 共享提示词摘要
        """
        try:
            return {
                "available_shared_prompts": [
                    {
                        "type": "SHARED_EMOTION_MAPPING",
                        "description": "情感状态映射策略指导",
                        "use_case": "根据情感分析结果调整销售策略"
                    },
                    {
                        "type": "SHARED_RESPONSE_ADAPTATION",
                        "description": "响应内容适配指导",
                        "use_case": "根据客户状态调整回复风格和内容"
                    },
                    {
                        "type": "SHARED_CONTEXT_ANALYSIS",
                        "description": "客户上下文综合分析框架",
                        "use_case": "多维度理解客户全貌"
                    },
                    {
                        "type": "SHARED_CUSTOMER_UNDERSTANDING",
                        "description": "客户理解传递模板",
                        "use_case": "agents间共享客户理解信息"
                    }
                ],
                "collaboration_functions": [
                    "get_greeting_prompt() - 获取问候提示词",
                    "get_product_recommendation_prompt() - 获取产品推荐提示词",
                    "get_objection_handling_prompt() - 获取异议处理提示词",
                    "generate_enhanced_response_with_shared_prompts() - 生成增强响应",
                    "integrate_sentiment_guidance() - 整合sentiment指导"
                ],
                "usage_examples": {
                    "greeting": "await get_greeting_message(context)",
                    "product_recommendation": "await get_product_recommendation_prompt(context)",
                    "objection_handling": "await get_objection_handling_prompt('price', context)",
                    "enhanced_response": "await generate_enhanced_response_with_shared_prompts(customer_input, sentiment_guidance, state)"
                }
            }
        except Exception as e:
            self.logger.error(f"获取共享提示词摘要失败: {e}")
            return {"error": str(e)}

    # ===== 新增的性能监控方法 =====

    def get_response_service_metrics(self) -> Dict[str, Any]:
        """获取响应生成服务的性能指标"""
        return self.response_service.get_performance_metrics()

    def reset_response_service_stats(self) -> None:
        """重置响应生成服务的统计信息"""
        self.response_service.reset_stats()

    # ===== 新增的响应生成策略方法 =====

    async def generate_sentiment_response(
        self,
        customer_input: str,
        context: Dict[str, Any]
    ) -> str:
        """生成情感驱动的响应"""
        return await self.response_service.generate_response(
            customer_input, context, strategy="sentiment_driven"
        )

    async def generate_standard_response(
        self,
        customer_input: str,
        context: Dict[str, Any]
    ) -> str:
        """生成标准销售响应"""
        return await self.response_service.generate_response(
            customer_input, context, strategy="standard"
        )

    async def generate_collaborative_response(
        self,
        customer_input: str,
        context: Dict[str, Any]
    ) -> str:
        """生成协作响应"""
        return await self.response_service.generate_response(
            customer_input, context, strategy="collaborative"
        )
