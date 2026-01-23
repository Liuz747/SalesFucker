import json
import re
from typing import Literal
from uuid import UUID

from langfuse import observe
from pydantic import ValidationError

from config import mas_config
from core.agents import BaseAgent
from core.prompts.template_loader import get_prompt_template
from infra.runtimes import CompletionsRequest, LLMResponse
from libs.types import Message, MessageParams
from models import WorkflowExecutionModel
from schemas.conversation_schema import InvitationData
from services import AssetsService
from utils import get_current_datetime, get_component_logger, get_processing_time
from utils.appointment_time_parser import parse_appointment_time
from .entities import AppointmentIntent, IntentAnalysisResult

logger = get_component_logger(__name__, "IntentAgent")


class IntentAgent(BaseAgent):
    """
    意向分析智能体

    通过单次LLM调用同时分析素材发送意向和邀约到店意向。

    设计特点：
    - 上下文共享：短期对话历史为意向分析提供充分上下文
    - 结构化输出：清晰的JSON格式，包含意向的完整分析
    - 实体提取：自动提取邀约相关的实体信息
    - 业务集成：生成CRM集成所需的business_outputs
    """

    def __init__(self):
        self.agent_name = "intent_analysis"
        super().__init__()

    @observe(name="intent-analysis", as_type="generation")
    async def process_conversation(self, state: WorkflowExecutionModel) -> dict:
        """
        处理对话状态中的意向分析

        工作流程：
        1. 检索记忆上下文（近5轮对话）
        2. 同时分析素材意向和邀约意向
        3. 提取实体信息（服务、姓名、电话、时间）
        4. 生成业务输出（CRM集成）

        参数:
            state: 当前对话状态

        返回:
            dict: 更新后的对话状态，包含 intent_analysis 信息
        """
        start_time = get_current_datetime()

        try:
            logger.info("=== Intent Analysis Agent ===")

            # 步骤1: 检索记忆上下文
            short_term_messages, _ = await self.memory_manager.retrieve_context(
                tenant_id=state.tenant_id,
                thread_id=state.thread_id
            )

            # 步骤2: 执行统一意向分析
            intent_result = await self._analyze_intent(
                inputs=short_term_messages + state.input,
                tenant_id=state.tenant_id,
                thread_id=state.thread_id,
                run_id=state.workflow_id
            )

            # 提取三种意向的结果
            assets_intent = intent_result.assets_intent
            appointment_intent = intent_result.appointment_intent
            audio_output_intent = intent_result.audio_output_intent

            logger.info(
                f"统一意向分析结果: \n"
                f"素材意向detected={assets_intent.detected}, "
                f"邀约意向detected={appointment_intent.detected}, "
                f"音频输出detected={audio_output_intent.detected}"
            )

            # 步骤3: 如果检测到素材意向，查询外部素材数据库
            assets_data = None
            if assets_intent.detected:
                logger.info("检测到素材意向，开始查询素材数据库")
                try:
                    assets_service = AssetsService(str(mas_config.CALLBACK_URL))

                    # 查询所有素材（使用缓存）
                    all_assets_data = await assets_service.query_assets(
                        tenant_id=state.tenant_id,
                        thread_id=state.thread_id,
                        assistant_id=state.assistant_id,
                        workflow_id=state.workflow_id
                    )

                    # 使用LLM提取的关键词进行搜索
                    keywords = assets_intent.keywords

                    if keywords:
                        # 使用关键词搜索过滤素材
                        filtered_assets = AssetsService.search_assets(
                            assets_data=all_assets_data,
                            keywords=keywords,
                            top_k=1,  # 返回1个最相关的素材
                            score_threshold=0.0
                        )

                        assets_data = {
                            "assets": filtered_assets,
                            "total": len(filtered_assets),
                            "from_cache": all_assets_data.get("from_cache", False)
                        }

                        logger.info(
                            f"素材搜索完成: keywords={keywords}, "
                            f"匹配{len(filtered_assets)}个相关素材"
                        )

                except Exception as e:
                    logger.error(f"素材查询失败: {e}", exc_info=True)
                    assets_data = {
                        "assets": [],
                        "total": 0,
                        "from_cache": False,
                        "error": str(e)
                    }

            # 步骤4: 更新对话状态
            updated_state = self._update_state_with_intent(intent_result, assets_data)

            processing_time = get_processing_time(start_time)
            logger.info(f"意向分析完成: 耗时{processing_time:.2f}s")
            logger.info("=== Intent Agent 处理完成 ===")

            return updated_state

        except Exception as e:
            logger.error(f"意向分析失败: {e}", exc_info=True)
            raise

    @staticmethod
    def _apply_threshold_overrides(intent_analysis: IntentAnalysisResult) -> IntentAnalysisResult:
        """
        基于配置的阈值覆盖LLM返回的detected信号

        如果启用了阈值覆盖，且分数低于配置的阈值，则将detected设为False。
        这样可以防止LLM在低置信度情况下仍然返回detected=True。

        Args:
            intent_analysis: 意图分析

        Returns:
            IntentAnalysisResult: 覆盖后的三种意向对象
        """
        if not mas_config.ENABLE_INTENT_THRESHOLD_OVERRIDE:
            logger.debug("阈值覆盖设置未启用，使用原始意图分析detected值")
            return intent_analysis

        # 素材意向阈值覆盖
        assets_intent = intent_analysis.assets_intent
        appointment_intent = intent_analysis.appointment_intent
        audio_output_intent = intent_analysis.audio_output_intent

        if assets_intent.detected and assets_intent.confidence < mas_config.ASSETS_INTENT_THRESHOLD:
            logger.info(
                f"素材意向被阈值覆盖: confidence={assets_intent.confidence:.2f} < "
                f"threshold={mas_config.ASSETS_INTENT_THRESHOLD:.2f}, detected: True -> False"
            )
            assets_intent.detected = False

        # 邀约意向阈值覆盖
        if appointment_intent.detected and appointment_intent.intent_strength < mas_config.APPOINTMENT_INTENT_THRESHOLD:
            logger.info(
                f"邀约意向被阈值覆盖: intent_strength={appointment_intent.intent_strength:.2f} < "
                f"threshold={mas_config.APPOINTMENT_INTENT_THRESHOLD:.2f}, detected: True -> False"
            )
            appointment_intent.detected = False

        # 音频输出意向阈值覆盖
        if audio_output_intent.detected and audio_output_intent.confidence < mas_config.AUDIO_OUTPUT_INTENT_THRESHOLD:
            logger.info(
                f"音频输出意向被阈值覆盖: confidence={audio_output_intent.confidence:.2f} < "
                f"threshold={mas_config.AUDIO_OUTPUT_INTENT_THRESHOLD:.2f}, detected: True -> False"
            )
            audio_output_intent.detected = False

        return intent_analysis

    async def _analyze_intent(
        self,
        inputs: MessageParams,
        tenant_id: str,
        thread_id: UUID,
        run_id: UUID
    ) -> IntentAnalysisResult:
        """
        执行统一意向分析

        Args:
            inputs: 最近用户消息 + 当前用户输入
            tenant_id: 租户ID
            thread_id: 线程ID
            run_id: 运行ID

        Returns:
            IntentAnalysisResult: 统一意向分析结果
        """
        try:
            # 构建LLM请求
            system_prompt = get_prompt_template(
                template_name="intent_analysis",
                template_file="agent_prompt.yaml"
            )
            messages = [Message(role="system", content=system_prompt), *inputs]

            request = CompletionsRequest(
                id=run_id,
                provider="openrouter",
                model="google/gemini-3-flash-preview",
                messages=messages,
                temperature=0.1,
                max_tokens=1200
            )

            # 调用LLM
            response = await self.invoke_llm(request, tenant_id, thread_id)

            # 解析响应
            return self._parse_llm_response(response)

        except Exception as e:
            logger.error(f"统一意向分析失败: {e}")
            return IntentAnalysisResult(error=str(e))

    def _parse_llm_response(self, response: LLMResponse) -> IntentAnalysisResult:
        """
        解析LLM响应

        Args:
            response: LLM响应对象

        Returns:
            IntentAnalysisResult: 解析后的统一意向结果
        """
        try:
            # 提取响应内容
            content = response.content.strip() if isinstance(response.content, str) else str(response.content).strip()

            # 提取JSON部分（支持markdown代码块格式）
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                json_content = json_match.group(1)
            else:
                # 尝试直接查找JSON对象
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                json_content = json_match.group(0) if json_match else content

            # 解析JSON
            raw_data = json.loads(json_content)

            # 验证和规范化意向
            result = IntentAnalysisResult(
                **raw_data,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens
            )

            # 应用阈值覆盖
            return self._apply_threshold_overrides(result)

        except json.JSONDecodeError as e:
            error_msg = f"JSON解析失败: {str(e)}"
            logger.warning(error_msg)
        except ValidationError as e:
            error_msg = f"数据验证失败: {str(e)}"
            logger.warning(error_msg)
        except Exception as e:
            error_msg = f"响应解析失败: {str(e)}"
            logger.error(error_msg)

        return IntentAnalysisResult(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            error=error_msg
        )

    @staticmethod
    def _generate_business_outputs(appointment_intent: AppointmentIntent) -> InvitationData:
        """
        基于邀约意向分析结果生成业务输出

        Args:
            appointment_intent: 邀约意向分析结果

        Returns:
            InvitationData: 结构化的业务输出，包含邀约信息
                格式: {status, time, service, name, phone}
                status: 0=不邀约, 1=确认邀约
                当status=1时，time必须有值（时间戳毫秒）
        """
        try:
            # 如果未检测到邀约意向，返回默认值
            if not appointment_intent.detected:
                return InvitationData()

            # 提取实体信息
            extracted_entities = appointment_intent.extracted_entities

            # 获取时间表达式
            time_expression = extracted_entities.time_expression

            # 解析时间
            parsed_time = 0
            if time_expression:
                timestamp_ms, parse_info = parse_appointment_time(time_expression)
                if timestamp_ms:
                    parsed_time = timestamp_ms
                    logger.info(f"时间解析成功: {time_expression} -> {timestamp_ms} (方法: {parse_info.get('method', 'unknown')})")
                else:
                    logger.warning(f"时间解析失败: {time_expression} - {parse_info.get('error', 'unknown error')}")

            # 确定邀约状态
            # status: 0=不邀约, 1=确认邀约
            # 确认邀约的条件：意向强度>=0.6 且 有有效时间
            intent_strength = appointment_intent.intent_strength

            # 只有当意向强度足够且时间已解析成功时，才确认邀约
            status: Literal[0, 1]
            if intent_strength >= 0.6 and parsed_time > 0:
                status = 1  # 确认邀约
            else:
                status = 0  # 不邀约
                if intent_strength >= 0.6 and parsed_time == 0:
                    logger.warning(f"意向强度足够({intent_strength})但时间未解析成功，无法确认邀约")

            # 构建邀约信息
            invitation_data = InvitationData(
                status=status,
                time=parsed_time if status == 1 else 0,
                service=extracted_entities.service,
                name=extracted_entities.name,
                phone=extracted_entities.phone
            )

            logger.info(f"生成邀约信息: {invitation_data.model_dump()}")

            return invitation_data

        except Exception as e:
            logger.error(f"生成业务输出失败: {e}", exc_info=True)
            # 返回默认的不邀约状态
            return InvitationData()

    def _update_state_with_intent(
        self,
        intent_result: IntentAnalysisResult,
        assets_data: dict | None = None
    ) -> dict:
        """
        更新状态，添加统一意向信息

        Args:
            intent_result: 统一意向分析结果
            assets_data: 素材查询结果（可选）

        Returns:
            dict: 更新后的状态
        """
        # 更新token信息
        input_tokens = intent_result.input_tokens
        output_tokens = intent_result.output_tokens

        # 生成业务输出
        business_outputs = self._generate_business_outputs(intent_result.appointment_intent)

        # 根据音频输出意向更新actions字段
        actions = []
        if intent_result.audio_output_intent.detected:
            actions.append("output_audio")

        # 构建 agent_data
        agent_data = {
            "agent_id": self.agent_name,
            "agent_type": "analytics",
            "intent_analysis": intent_result.model_dump(),
            "business_outputs": business_outputs.model_dump(),
            "timestamp": intent_result.timestamp,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        }

        logger.info(f"意向字段已添加: business_status={business_outputs.status}")

        # 构建状态更新字典
        return {
            "actions": actions,
            "assets_data": assets_data,
            "intent_analysis": intent_result.model_dump(),
            "business_outputs": business_outputs.model_dump(),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "values": {"agent_responses": {self.agent_name: agent_data}}
        }
