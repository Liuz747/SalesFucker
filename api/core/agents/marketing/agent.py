import json
from uuid import uuid4

from langfuse import observe

from core.agents import BaseAgent
from core.memory import ConversationStore
from infra.runtimes import CompletionsRequest, LLMResponse
from libs.types import Message
from schemas.marketing_schema import MarketingPlanRequest, MarketingPlanResponse
from utils import get_component_logger

logger = get_component_logger(__name__)


class MarketingAgent(BaseAgent):
    """
    营销专家智能体

    负责生成营销策略和内容营销计划，为用户提供：
    1. 自然语言叙述分析
    2. 3个结构化的营销方案选项

    特点：
    - 独立运行（非工作流集成）
    - 预留产品目录集成能力
    """

    def __init__(self):
        super().__init__()
        self.short_memory_manager = ConversationStore()

        # 预留：未来产品目录集成
        # self.product_recommender = ProductRecommender()
        # self.product_search = ProductSearch()

    async def process_conversation(self, state: dict) -> dict:
        """
        实现BaseAgent的抽象方法（用于工作流集成）

        注意：当前营销agent是独立运行的，不通过工作流调用。
        此方法保留用于未来可能的工作流集成。

        参数:
            state: 工作流状态（未使用）

        返回:
            dict: 状态更新（空）
        """
        logger.warning("MarketingAgent.process_conversation called but not implemented for workflow")
        return {}

    @observe(name="marketing-plan-generation", as_type="span")
    async def generate_marketing_plans(
        self,
        request: MarketingPlanRequest,
        tenant_id: str
    ) -> MarketingPlanResponse:
        """
        生成营销计划（自然语言叙述 + 3个结构化选项）

        参数:
            request: 营销计划请求
            tenant_id: 租户ID

        返回:
            MarketingPlanResponse
        """
        try:
            logger.info(f"开始生成营销计划 - tenant: {tenant_id}")

            # 1. 加载会话历史（如果提供了request_id）
            conversation_history = []
            if request.request_id:
                conversation_history = await self.short_memory_manager.get_recent(
                    thread_id=request.request_id,
                    limit=10
                )
                logger.info(f"加载了 {len(conversation_history)} 条历史消息")

            # 2. 构建营销提示词
            marketing_prompt = self._build_marketing_prompt(content=request.content)

            conversation_history.append(
                Message(role="user", content=marketing_prompt)
            )

            # 3. 调用LLM生成计划
            llm_response = await self._generate_plans(conversation_history, tenant_id)

            # 4. 解析结构化输出
            response, plan_options = self._parse_structured_output(llm_response.content)

            # 5. 保存本轮对话
            await self.short_memory_manager.append_messages(
                thread_id=request.request_id if request.request_id else llm_response.id,
                messages=[
                    Message(role="user", content=request.content),
                    Message(role="assistant", content=llm_response.content)
                ]
            )

            logger.info(
                f"营销计划生成成功 - options: {len(plan_options)}, "
            )

            return MarketingPlanResponse(
                request_id=llm_response.id,
                response=response,
                options=plan_options,
                input_tokens=llm_response.usage.input_tokens,
                output_tokens=llm_response.usage.output_tokens
            )

        except Exception as e:
            logger.error(f"营销计划生成失败: {e}", exc_info=True)
            raise

    @staticmethod
    def _build_marketing_prompt(content: str) -> str:
        """
        构建营销提示词

        参数:
            content: 营销方案描述

        返回:
            str: 完整的提示词
        """
        return (
            f"你是资深美妆行业营销策略专家，精通小红书/抖音/微博等平台的数字营销和内容创作。\n\n"
            f"## 用户需求\n"
            f"{content}\n\n"
            f"## 任务要求\n"
            f"基于用户需求，设计3个差异化营销方案：\n"
            f"- 方案1：社交媒体内容营销\n"
            f"- 方案2：线下体验活动营销\n"
            f"- 方案3：线上线下O2O整合\n\n"
            f"## 输出格式（严格遵循JSON）\n"
            f'{{\n'
            f'    "response": "200-300字分析：解读用户需求，说明3个方案的选择理由和差异点",\n'
            f'    "options": [\n'
            f'        {{"option_id": 1, "content": "具体可执行的方案内容（不要泛泛而谈）"}},\n'
            f'        {{"option_id": 2, "content": "具体可执行的方案内容（不要泛泛而谈）"}},\n'
            f'        {{"option_id": 3, "content": "具体可执行的方案内容（不要泛泛而谈）"}}\n'
            f'    ]\n'
            f'}}\n\n'
            f"注意：必须输出有效JSON，确保3个方案有明显差异。"
        )

    @observe(name="llm-generation", as_type="generation")
    async def _generate_plans(self, user_input: list, tenant_id: str) -> LLMResponse:
        """
        调用LLM生成营销计划

        参数:
            user_input: 完整提示词
            tenant_id: 租户ID

        返回:
            LLMResponse
        """
        try:
            # 构建LLM请求
            request_id = uuid4()
            request = CompletionsRequest(
                id=request_id,
                provider="openrouter",
                model="openai/gpt-oss-120b:exacto",
                temperature=0.7,
                messages=user_input,
                # 注意：response_format JSON mode 需要provider支持
                # 这里先不使用，后续可以根据provider能力优化
            )

            # 调用LLM
            return await self.invoke_llm(
                request=request,
                tenant_id=tenant_id,
                thread_id=request_id
            )

        except Exception as e:
            logger.error(f"LLM调用失败: {e}", exc_info=True)
            raise

    @staticmethod
    def _parse_structured_output(llm_response: str) -> tuple[str, list[dict]]:
        """
        解析LLM的结构化输出

        参数:
            llm_response: LLM返回的内容

        返回:
            tuple: (response, plan_options)
        """
        try:
            # 尝试直接解析JSON
            response_data = json.loads(llm_response)

            response = response_data.get("response", "")
            options = response_data.get("options", [])

            # 确保每个option都有option_id
            for i, option in enumerate(options, 1):
                if "option_id" not in option:
                    option["option_id"] = i

            return response, options

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            # 尝试提取JSON部分（可能LLM返回包含了额外文本）
            try:
                # 查找第一个 { 和最后一个 }
                start_idx = llm_response.find("{")
                end_idx = llm_response.rfind("}") + 1

                if start_idx != -1 and end_idx > start_idx:
                    json_str = llm_response[start_idx:end_idx]
                    response_data = json.loads(json_str)
                    response = response_data.get("response", "")
                    options = response_data.get("options", [])[:3]
                    return response, options
            except:
                pass

            # 解析失败
            logger.error("无法解析LLM输出")
            raise ValueError("Failed to parse LLM response")
