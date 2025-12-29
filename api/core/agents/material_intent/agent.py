"""
Material Intent Analysis Agent - 素材发送意向分析智能体

专注于分析客户的素材发送意向，基于历史对话内容判断用户是否需要产品图片、价格信息、技术参数等素材。

核心职责:
- 基于近3轮对话分析素材需求意向
- 多类型素材需求识别（图片、价格、技术参数等）
- 紧急程度和优先级判断
- 为sales agent提供对应素材提示词，以衔接回复
"""

import json
import re
from uuid import UUID
from typing import Any

from langfuse import observe

from core.agents import BaseAgent
from core.entities import WorkflowExecutionModel
from core.memory import StorageManager
from infra.runtimes import CompletionsRequest, LLMResponse
from libs.types import Message
from utils import get_current_datetime, get_component_logger

logger = get_component_logger(__name__, "IntentAgent")


class MaterialIntentAgent(BaseAgent):
    """
    素材发送意向分析智能体

    基于用户近3轮对话内容，智能分析用户是否需要各种类型的素材。
    支持产品图片、价格信息、技术参数等多种素材类型的识别。

    设计特点：
    - 多类型素材识别：全面覆盖各种素材需求
    - 优先级评估：判断素材需求的紧急程度
    - 精准匹配：识别具体的素材类型要求
    - 记忆集成：利用系统记忆进行上下文分析
    """

    def __init__(self):
        super().__init__()
        self.memory_manager = StorageManager()

    @observe(name="material-intent-analysis", as_type="generation")
    async def process_conversation(self, state: WorkflowExecutionModel) -> dict:
        """
        处理对话状态中的素材发送意向分析

        工作流程：
        1. 检索记忆上下文（近3轮对话）
        2. 分析各种类型的素材需求意向
        3. 判断紧急程度和优先级
        4. 生成素材需求报告
        5. 更新状态传递给sales agent

        参数:
            state: 当前对话状态，包含 customer_input, tenant_id, thread_id

        返回:
            dict: 更新后的对话状态，包含 material_intent 信息
        """
        start_time = get_current_datetime()

        try:
            logger.info("=== Material Intent Agent ===")
            logger.debug(f"分析素材意向 - 输入: {str(state.input)[:100]}...")

            # 步骤1: 检索记忆上下文（近3轮对话）
            user_text = self._input_to_text(state.input)
            short_term_messages, _ = await self.memory_manager.retrieve_context(
                tenant_id=state.tenant_id,
                thread_id=state.thread_id,
                query_text=user_text,
            )

            # 提取近3轮用户消息用于分析
            recent_user_messages = self._extract_recent_user_messages(
                short_term_messages, max_rounds=3
            )

            logger.info(f"记忆检索完成 - 分析轮次: {len(recent_user_messages)}")

            # 步骤2: 执行素材意向分析
            intent_result = await self._analyze_material_intent(
                current_input=user_text,
                recent_messages=recent_user_messages,
                tenant_id=state.tenant_id,
                thread_id=state.thread_id,
                run_id=state.workflow_id
            )

            logger.info(f"素材意向分析结果 - 紧急程度: {intent_result.get('urgency_level', 'low')}, "
                           f"素材类型数: {len(intent_result.get('material_types', []))}, "
                           f"tokens_used: {intent_result.get('total_tokens', 0)}")

            # 步骤3: 更新对话状态
            updated_state = self._update_state_with_intent(
                intent_result, recent_user_messages
            )

            processing_time = (get_current_datetime() - start_time).total_seconds()
            logger.info(f"素材意向分析完成: 耗时{processing_time:.2f}s, "
                           f"紧急程度={intent_result.get('urgency_level', 'low')}")
            logger.info("=== Material Intent Agent 处理完成 ===")

            return updated_state

        except Exception as e:
            logger.error(f"素材意向分析失败: {e}", exc_info=True)
            logger.error(f"失败时的输入: {state.input}")
            raise

    def _extract_recent_user_messages(self, messages: list, max_rounds: int = 3) -> list[str]:
        """
        从记忆中提取最近N轮用户消息

        Args:
            messages: 短期记忆消息列表
            max_rounds: 最大提取轮数

        Returns:
            List[str]: 用户消息内容列表
        """
        try:
            recent_messages = []
            user_message_count = 0

            # 从最新消息开始倒序提取
            for msg in reversed(messages):
                if user_message_count >= max_rounds:
                    break

                # 处理不同格式的消息对象
                if isinstance(msg, dict):
                    role = msg.get("role")
                    content = msg.get("content")
                elif hasattr(msg, 'role'):
                    role = msg.role
                    content = getattr(msg, 'content', None)
                else:
                    continue

                if role == "user" and content and str(content).strip():
                    recent_messages.insert(0, str(content))
                    user_message_count += 1

            logger.debug(f"提取用户消息: {len(recent_messages)}轮")
            return recent_messages

        except Exception as e:
            logger.error(f"提取用户消息失败: {e}")
            return []

    async def _analyze_material_intent(
        self,
        current_input: str,
        recent_messages: list[str],
        tenant_id: str,
        thread_id: UUID,
        run_id: UUID
    ) -> dict[str, Any]:
        """
        分析素材发送意向

        Args:
            current_input: 当前用户输入
            recent_messages: 最近用户消息列表
            tenant_id: 租户ID
            thread_id: 线程ID

        Returns:
            dict: 意向分析结果
        """
        try:
            # 构建分析文本
            analysis_text = self._build_analysis_text(current_input, recent_messages)

            # 构建LLM请求
            messages = [
                Message(role="system", content=self._get_analysis_prompt()),
                Message(role="user", content=analysis_text)
            ]

            request = CompletionsRequest(
                id=run_id,
                provider="openrouter",
                model="anthropic/claude-haiku-4.5",
                messages=messages,
                temperature=0.1,
                max_tokens=800
            )

            # 调用LLM
            response = await self.invoke_llm(request, tenant_id, thread_id)

            # 解析响应
            result = self._parse_llm_response(response)

            # 添加分析元数据
            result["analysis_metadata"] = {
                "analyzed_messages": len(recent_messages),
                "analysis_timestamp": get_current_datetime().isoformat(),
                "input_length": len(current_input),
                "analysis_type": "material_intent"
            }

            return result

        except Exception as e:
            logger.error(f"素材意向分析失败: {e}")
            # 返回默认的无需求结果
            return self._get_fallback_result(error=str(e))

    def _get_analysis_prompt(self) -> str:
        return """你是一个专业的客户素材需求分析专家，专门分析客户对各种类型素材的需求意向。

请基于提供的用户对话内容，分析用户是否需要发送任何类型的素材，包括但不限于产品图片、视频、价格信息、技术参数等。

## 素材类型分类：

### 1. 视觉素材 (visual)
- product_images: 产品图片（包装、实物展示）
- before_after: 对比图（使用前后效果对比）
- usage_videos: 使用视频（产品使用方法演示）
- treatment_process: 治疗过程图（操作流程展示）

### 2. 信息素材 (information)
- price_list: 价格表（产品价格、服务费用）
- promotion_info: 促销活动（优惠、折扣信息）
- ingredient_list: 成分表（产品成分、配方信息）
- technical_specs: 技术参数（规格、使用方法）

### 3. 证明素材 (proof)
- certificates: 证书资质（产品认证、权威证明）
- customer_reviews: 客户评价（真实使用反馈）
- clinical_data: 临床数据（试验结果、效果数据）

### 4. 服务素材 (service)
- store_info: 门店信息（地址、环境照片）
- service_menu: 服务菜单（项目介绍、套餐详情）
- appointment_guide: 预约指南（预约流程、注意事项）

## 评估维度：

1. **紧急程度 (urgency_level)**: "high" (用户心情愉悦) | "medium" (正常聊天) | "low" (负面意向/拒绝)
2. **优先级评分 (priority_score)**: 0.0-1.0 数值
3. **置信度 (confidence)**: 0.0-1.0，表示分析的确定程度
4. **推荐建议 (recommendation)**: "send_immediately" | "send_soon" | "wait_for_confirmation" | "no_material"

## 输出格式（严格JSON）
请严格按照以下JSON格式输出分析结果：

```json
{
    "urgency_level": "medium",
    "material_types": [
        {
            "type": "product_images",
            "category": "visual",
            "description": "用户想看产品的实际效果图片",
            "priority": 0.8,
            "specifics": ["产品包装图", "使用效果对比图"]
        },
        {
            "type": "price_list",
            "category": "information",
            "description": "询问产品价格和套餐费用",
            "priority": 0.7,
            "specifics": ["单品价格", "套餐优惠"]
        }
    ],
    "priority_score": 0.75,
    "confidence": 0.85,
    "specific_requests": ["想看产品实际效果", "询问价格信息"],
    "recommendation": "send_soon",
    "analysis_summary": "用户在对话中表现出对产品效果图片和价格信息的明确需求，建议尽快发送相关素材。"
}
```
## 推荐建议 (recommendation)：
- send_immediately: 立即发送（高紧急程度）
- send_soon: 近期发送（中等紧急程度）
- wait_for_confirmation: 等待确认（低置信度）
- no_material: 无需发送（无明确需求）

## 重要提醒：
1. urgency_level只能是: "high", "medium", "low" 之一
2. priority_score必须是0.0-1.0之间的数值
3. material_types数组包含所有识别到的素材类型
4. each material_type必须包含: type, category, description, priority
5. 必须包含准确的token使用统计
6. confidence表示你对分析的置信度

请基于对话内容返回JSON格式的分析结果。"""

    def _build_analysis_text(self, current_input: str, recent_messages: list[str]) -> str:
        """
        构建分析文本

        Args:
            current_input: 当前用户输入
            recent_messages: 最近用户消息列表

        Returns:
            str: 格式化的分析文本
        """
        lines = [
            "=== 素材发送意向分析 ===",
            f"分析轮次: {len(recent_messages)}轮对话",
            f"当前用户输入: {current_input}",
            ""
        ]

        if recent_messages:
            lines.append("历史对话内容:")
            for i, message in enumerate(recent_messages, 1):
                lines.append(f"第{i}轮: {message}")
            lines.append("")
        else:
            lines.append("无历史对话记录")
            lines.append("")

        lines.extend([
            "请基于以上对话内容，分析用户对以下类型的素材需求：",
            "",
            "1. 视觉素材：产品图片、效果对比、使用视频等",
            "2. 信息素材：价格信息、成分表、技术参数等",
            "3. 证明素材：证书资质、客户评价、临床数据等",
            "4. 服务素材：门店信息、服务菜单、预约指南等",
            "",
            "请分析用户对以上素材类型的需求，重点关注：",
            "- 用户明确询问的素材类型",
            "- 用户的紧急程度和优先级",
            "- 具体的素材需求细节"
        ])

        return "\n".join(lines)

    def _parse_llm_response(self, response: LLMResponse) -> dict[str, Any]:
        """
        解析LLM响应

        Args:
            response: LLM响应对象

        Returns:
            dict: 解析后的结果
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

            # 添加token信息
            result["input_tokens"] = response.usage.input_tokens
            result["output_tokens"] = response.usage.output_tokens
            result["total_tokens"] = result["input_tokens"] + result["output_tokens"]

            # 验证和规范化字段
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
        # 验证urgency_level
        valid_urgency = ["high", "medium", "low"]
        if result.get("urgency_level") not in valid_urgency:
            result["urgency_level"] = "medium"

        # 验证recommendation
        valid_recommendations = ["send_immediately", "send_soon", "wait_for_confirmation", "no_material"]
        if result.get("recommendation") not in valid_recommendations:
            result["recommendation"] = "wait_for_confirmation"

        # 验证数值范围
        result["priority_score"] = max(0.0, min(1.0, result.get("priority_score", 0.5)))
        result["confidence"] = max(0.0, min(1.0, result.get("confidence", 0.5)))

        # 确保必要字段存在
        result.setdefault("material_types", [])
        result.setdefault("specific_requests", [])
        result.setdefault("analysis_summary", "")

        return result

    def _get_fallback_result(self, response: LLMResponse = None, error: str = "") -> dict:
        """
        获取降级结果

        Args:
            response: LLM响应对象（可选）
            error: 错误信息

        Returns:
            dict: 降级结果
        """
        result = {
            "urgency_level": "medium",
            "material_types": [],
            "priority_score": 0.5,
            "confidence": 0.0,
            "specific_requests": [],
            "recommendation": "wait_for_confirmation",
            "analysis_summary": f"分析失败，使用默认值: {error}",
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        }

        # 如果有响应对象，提取token信息
        if response and hasattr(response, 'usage'):
            result["input_tokens"] = response.usage.input_tokens
            result["output_tokens"] = response.usage.output_tokens
            result["total_tokens"] = result["input_tokens"] + result["output_tokens"]

        return result

    def _update_state_with_intent(
        self,
        intent_result: dict,
        recent_messages: list[str]
    ) -> dict:
        """
        更新状态，添加素材意向信息

        Args:
            intent_result: 意向分析结果
            recent_messages: 分析用的消息列表

        Returns:
            dict: 更新后的状态
        """
        current_time = get_current_datetime()

        # 更新token信息
        token_info = {
            "input_tokens": intent_result.get("input_tokens", 0),
            "output_tokens": intent_result.get("output_tokens", 0),
            "total_tokens": intent_result.get("total_tokens", intent_result.get("tokens_used", 0))
        }

        # 核心传递字段：material_intent
        material_intent = {
            "urgency_level": intent_result.get("urgency_level", "low"),
            "material_types": intent_result.get("material_types", []),
            "priority_score": intent_result.get("priority_score", 0.0),
            "confidence": intent_result.get("confidence", 0.0),
            "specific_requests": intent_result.get("specific_requests", []),
            "recommendation": intent_result.get("recommendation", "no_material"),
            "analyzed_message_count": len(recent_messages),
            "analysis_timestamp": current_time.isoformat()
        }

        # 构建 agent_data
        agent_data = {
            "agent_type": "material_intent",
            "material_intent": material_intent,
            "intent_result": intent_result,
            "analyzed_messages": recent_messages,
            "timestamp": current_time,
            "token_usage": token_info,
            "tokens_used": token_info["total_tokens"],
            "response_length": len(str(intent_result))
        }

        logger.info(f"material intent 字段已添加: urgency={material_intent['urgency_level']}, "
                        f"types={len(material_intent['material_types'])}")

        # 返回增量更新字典，让 LangGraph 的 Reducer 正确合并状态
        return {
            "material_intent": material_intent,
            "input_tokens": token_info["input_tokens"],
            "output_tokens": token_info["output_tokens"],
            "values": {"agent_responses": {self.agent_id: agent_data}},
            "active_agents": [self.agent_id]
        }
