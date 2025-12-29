import json
import re
from typing import Any, Optional
from uuid import UUID

from langfuse import observe

from core.entities import WorkflowExecutionModel
from core.prompts.template_loader import get_prompt_template
from infra.runtimes import CompletionsRequest, LLMResponse
from libs.types import Message, MessageParams
from utils import get_current_datetime, get_component_logger, get_processing_time
from utils.appointment_time_parser import parse_appointment_time
from ..base import BaseAgent

logger = get_component_logger(__name__, "IntentAgent")


class IntentAgent(BaseAgent):
    """
    意向分析智能体

    通过单次LLM调用同时分析素材发送意向和邀约到店意向。

    设计特点：
    - 上下文共享：5轮对话历史为两种意向提供充分上下文
    - 结构化输出：清晰的JSON格式，包含两种意向的完整分析
    - 实体提取：自动提取邀约相关的实体信息
    - 业务集成：生成CRM集成所需的business_outputs
    """

    def __init__(self):
        super().__init__()

        self.agent_name = "intent_analysis"

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
            state: 当前对话状态，包含 customer_input, tenant_id, thread_id

        返回:
            dict: 更新后的对话状态，包含 intent_analysis 信息
        """
        start_time = get_current_datetime()

        try:
            logger.info("=== Intent Analysis Agent ===")
            logger.debug(f"分析意向 - 输入: {str(state.input)[:100]}...")

            # 步骤1: 检索记忆上下文
            short_term_messages, _ = await self.memory_manager.retrieve_context(
                tenant_id=state.tenant_id,
                thread_id=state.thread_id
            )

            # 提取用户消息用于分析
            recent_user_messages = [msg for msg in short_term_messages if msg.role == "user"]

            # 步骤2: 执行统一意向分析
            intent_result = await self._analyze_intent(
                inputs=recent_user_messages + state.input,
                tenant_id=state.tenant_id,
                thread_id=state.thread_id,
                run_id=state.workflow_id
            )

            # 提取两种意向的结果
            assets_intent = intent_result.get("assets_intent", {})
            appointment_intent = intent_result.get("appointment_intent", {})

            logger.info(
                f"统一意向分析结果 - "
                f"素材意向detected={assets_intent.get('detected', False)}, "
                f"urgency={assets_intent.get('urgency_level', 'low')}, "
                f"邀约意向detected={appointment_intent.get('detected', False)}, "
                f"strength={appointment_intent.get('intent_strength', 0)}"
            )

            # 步骤3: 更新对话状态
            updated_state = self._update_state_with_intent(intent_result, recent_user_messages)

            processing_time = get_processing_time(start_time)
            logger.info(f"意向分析完成: 耗时{processing_time:.2f}s")
            logger.info("=== Intent Agent 处理完成 ===")

            return updated_state

        except Exception as e:
            logger.error(f"意向分析失败: {e}", exc_info=True)
            logger.error(f"失败时的输入: {state.input}")
            raise

    async def _analyze_intent(
        self,
        inputs: MessageParams,
        tenant_id: str,
        thread_id: UUID,
        run_id: UUID
    ) -> dict[str, Any]:
        """
        执行统一意向分析

        Args:
            inputs: 最近用户消息 + 当前用户输入
            tenant_id: 租户ID
            thread_id: 线程ID
            run_id: 运行ID

        Returns:
            dict: 统一意向分析结果，包含assets_intent和appointment_intent
        """
        try:
            # 构建LLM请求
            system_prompt = [Message(role="system", content=get_prompt_template("intent_analysis"))]

            request = CompletionsRequest(
                id=run_id,
                provider="openrouter",
                model="anthropic/claude-haiku-4.5",
                messages=system_prompt + inputs,
                temperature=0.1,
                max_tokens=1200
            )

            # 调用LLM
            response = await self.invoke_llm(request, tenant_id, thread_id)

            # 解析响应
            result = self._parse_llm_response(response)

            result.update({
                "timestamp": get_current_datetime().isoformat(),
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            })

            return result

        except Exception as e:
            logger.error(f"统一意向分析失败: {e}")
            # 返回默认的无需求结果
            return self._get_fallback_result(error=str(e))

    def _parse_llm_response(self, response: LLMResponse) -> dict[str, Any]:
        """
        解析LLM响应

        Args:
            response: LLM响应对象

        Returns:
            dict: 解析后的统一意向结果
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
            result = json.loads(json_content)

            # 验证和规范化两种意向
            result = self._validate_and_normalize(result)

            return result

        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {e}")
            return self._get_fallback_result(
                response=response,
                error=f"JSON解析失败: {str(e)}"
            )
        except Exception as e:
            logger.error(f"响应解析失败: {e}")
            return self._get_fallback_result(
                response=response,
                error=str(e)
            )

    def _validate_and_normalize(self, result: dict) -> dict:
        """
        验证和规范化分析结果

        Args:
            result: 原始分析结果

        Returns:
            dict: 验证后的结果
        """
        # 验证素材意向
        asset = result.get("assets_intent", {})

        # 验证urgency_level
        valid_urgency = ["high", "medium", "low"]
        if asset.get("urgency_level") not in valid_urgency:
            asset["urgency_level"] = "medium"

        # 验证recommendation
        valid_recommendations = ["send_immediately", "send_soon", "wait_for_confirmation", "no_material"]
        if asset.get("recommendation") not in valid_recommendations:
            asset["recommendation"] = "wait_for_confirmation"

        # 验证数值范围
        asset["priority_score"] = max(0.0, min(1.0, asset.get("priority_score", 0.5)))
        asset["confidence"] = max(0.0, min(1.0, asset.get("confidence", 0.5)))

        # 确保必要字段存在
        asset.setdefault("detected", False)
        asset.setdefault("asset_types", [])
        asset.setdefault("specific_requests", [])
        asset.setdefault("summary", "")

        # 验证邀约意向
        appointment = result.get("appointment_intent", {})

        # 验证time_window
        valid_windows = ["immediate", "this_week", "this_month", "unknown"]
        if appointment.get("time_window") not in valid_windows:
            appointment["time_window"] = "unknown"

        # 验证recommendation
        valid_recommendations = ["suggest_appointment", "wait_signal", "no_appointment"]
        if appointment.get("recommendation") not in valid_recommendations:
            appointment["recommendation"] = "wait_signal"

        # 验证数值范围
        appointment["intent_strength"] = max(0.0, min(1.0, appointment.get("intent_strength", 0.0)))
        appointment["confidence"] = max(0.0, min(1.0, appointment.get("confidence", 0.5)))

        # 确保必要字段存在
        appointment.setdefault("detected", False)
        appointment.setdefault("signals", [])
        appointment.setdefault("extracted_entities", {})
        appointment.setdefault("summary", "")

        return result

    def _get_fallback_result(self, response: LLMResponse = None, error: str = "") -> dict:
        """
        获取降级结果

        Args:
            response: LLM响应对象（可选）
            error: 错误信息

        Returns:
            dict: 降级结果，包含两种意向的默认值
        """
        return {
            "assets_intent": {
                "detected": False,
                "recommendation": "wait_for_confirmation"
            },
            "appointment_intent": {
                "detected": False,
                "recommendation": "no_appointment"
            },
            "timestamp": get_current_datetime().isoformat(),
            "input_tokens": response.usage.input_tokens if response else 0,
            "output_tokens": response.usage.output_tokens if response else 0,
            "error": error
        }

    def _generate_business_outputs(self, intent_result: dict) -> dict:
        """
        基于邀约意向分析结果生成业务输出

        Args:
            intent_result: 统一意向分析结果

        Returns:
            dict: 结构化的业务输出，包含邀约信息
                格式: {status, time, service, name, phone}
                status: 0=不邀约, 1=确认邀约
                当status=1时，time必须有值（时间戳毫秒）
        """
        try:
            appointment_intent = intent_result.get("appointment_intent")

            # 如果未检测到邀约意向，返回默认值
            if not appointment_intent.get("detected", False):
                return {
                    "status": 0,
                    "time": 0,
                    "service": None,
                    "name": None,
                    "phone": None
                }

            # 提取实体信息
            extracted_entities = appointment_intent.get("extracted_entities", {})
            entity_confidence = extracted_entities.get("entity_confidence", {})

            # 获取时间表达式
            time_expression = extracted_entities.get("time_expression")

            # 解析时间
            parsed_time = 0
            if time_expression:
                time_confidence = entity_confidence.get("time_expression", 0)
                timestamp_ms, parse_info = parse_appointment_time(time_expression)
                if timestamp_ms:
                    parsed_time = timestamp_ms
                    logger.info(f"时间解析成功: {time_expression} -> {timestamp_ms} (置信度: {time_confidence}, 方法: {parse_info.get('method', 'unknown')})")
                else:
                    logger.warning(f"时间解析失败: {time_expression} - {parse_info.get('error', 'unknown error')}")

            # 确定邀约状态
            # status: 0=不邀约, 1=确认邀约
            # 确认邀约的条件：意向强度>=0.6 且 有有效时间
            intent_strength = appointment_intent.get("intent_strength", 0)

            # 只有当意向强度足够且时间已解析成功时，才确认邀约
            if intent_strength >= 0.6 and parsed_time > 0:
                status = 1  # 确认邀约
            else:
                status = 0  # 不邀约
                if intent_strength >= 0.6 and parsed_time == 0:
                    logger.warning(f"意向强度足够({intent_strength})但时间未解析成功，无法确认邀约")

            # 构建简洁的邀约信息
            invitation_data = {
                "status": status,
                "time": parsed_time if status == 1 else 0,  # 只有确认邀约时才返回时间
                "service": extracted_entities.get("service"),
                "name": extracted_entities.get("name"),
                "phone": self._parse_phone_number(extracted_entities.get("phone")) if extracted_entities.get("phone") else None
            }

            logger.info(f"生成邀约信息: status={invitation_data['status']}, "
                       f"time={invitation_data['time']}, "
                       f"service={invitation_data['service']}, "
                       f"name={invitation_data['name']}, "
                       f"phone={invitation_data['phone']}")

            return invitation_data

        except Exception as e:
            logger.error(f"生成业务输出失败: {e}", exc_info=True)
            # 返回默认的不邀约状态
            return {
                "status": 0,
                "time": 0,
                "service": None,
                "name": None,
                "phone": None
            }

    def _parse_phone_number(self, phone_str: str) -> Optional[int]:
        """
        解析电话号码为整数

        Args:
            phone_str: 电话号码字符串

        Returns:
            Optional[int]: 解析后的电话号码，失败返回None
        """
        if not phone_str:
            return None

        try:
            # 移除所有非数字字符
            clean_phone = ''.join(c for c in str(phone_str) if c.isdigit())

            # 验证手机号格式（中国手机号11位）
            if len(clean_phone) == 11 and clean_phone.startswith('1'):
                return int(clean_phone)
            else:
                logger.warning(f"无效的手机号格式: {phone_str} -> {clean_phone}")
                return None
        except (ValueError, TypeError) as e:
            logger.warning(f"电话号码解析失败: {phone_str} - {e}")
            return None

    def _update_state_with_intent(
        self,
        intent_result: dict,
        recent_messages: list[Message]
    ) -> dict:
        """
        更新状态，添加统一意向信息

        Args:
            intent_result: 统一意向分析结果
            recent_messages: 分析用的消息列表

        Returns:
            dict: 更新后的状态，包含intent_analysis和向后兼容字段
        """
        # 更新token信息
        input_tokens = intent_result.get("input_tokens")
        output_tokens = intent_result.get("output_tokens")

        # 生成业务输出
        business_outputs = self._generate_business_outputs(intent_result)

        # 构建 agent_data
        agent_data = {
            "agent_name": self.agent_name,
            "intent_analysis": intent_result,
            "business_outputs": business_outputs,
            "analyzed_messages": recent_messages,
            "timestamp": intent_result.get("timestamp"),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        }

        logger.info(f"意向字段已添加: business_status={business_outputs.get('status', 0)}")

        # 返回增量更新字典，让 LangGraph 的 Reducer 正确合并状态
        return {
            "intent_analysis": intent_result,
            "business_outputs": business_outputs,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "values": {"agent_responses": {self.agent_name: agent_data}},
            "active_agents": [self.agent_name]
        }
