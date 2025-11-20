"""
Appointment Intent Analyzer - 邀约意向分析器

负责深度分析用户对话中的邀约到店意向信号，提供量化的意向评估。

核心功能:
- 多轮对话语义分析
- 邀约信号识别和分类
- 时间窗口预测
- 意向强度量化
"""

from typing import Dict, Any, List
from infra.runtimes import CompletionsRequest, LLMResponse


class AppointmentIntentAnalyzer:
    """
    邀约到店意向分析器

    使用大语言模型分析用户对话，识别邀约到店的各种信号，
    并提供量化的意向评估和时间窗口预测。
    """

    def __init__(self, llm_provider: str, llm_model: str, invoke_llm_fn):
        """
        初始化意向分析器

        Args:
            llm_provider: LLM提供商标识
            llm_model: 模型名称
            invoke_llm_fn: LLM调用函数
        """
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.invoke_llm = invoke_llm_fn

        # 邀约意向分析提示词
        self.analysis_prompt = """你是一个专业的客户邀约意向分析专家，专门分析美妆/医美行业客户的到店意向。

请基于提供的用户对话内容，分析用户是否有到店咨询或体验的意向。

## 分析维度：

### 1. 意向强度 (Intent Strength)
- 0.0-0.2: 无明显意向
- 0.3-0.5: 弱意向（略有兴趣）
- 0.6-0.7: 中等意向（有兴趣但犹豫）
- 0.8-0.9: 强意向（明确表示考虑）
- 1.0: 非常强意向（主动询问或表达强烈需求）

### 2. 时间窗口 (Time Window)
- immediate: 表示立即或尽快到店
- this_week: 本周内到店
- this_month: 本月内到店
- unknown: 时间不明确

### 3. 邀约信号类型
- 咨询类：询问门店地址、营业时间、服务项目
- 体验类：表示想要试用、体验、看效果
- 价格类：询问到店服务的价格、套餐
- 便利性：询问是否需要预约、等待时间等
- 直接表达：明确说想来看看、了解一下

## 输出格式：
请严格按照以下JSON格式输出分析结果：

```json
{
    "intent_strength": 0.8,
    "time_window": "this_week",
    "confidence": 0.85,
    "signals": [
        {
            "type": "咨询类",
            "content": "询问门店营业时间",
            "strength": 0.7
        }
    ],
    "recommendation": "suggest_appointment",
    "analysis_summary": "用户在第3轮对话中明确询问了门店的具体地址和营业时间，表现出较强的到店意向。建议主动邀约用户本周内到店体验。",
    "input_tokens": 150,
    "output_tokens": 200,
    "total_tokens": 350
}
```

## 重要提醒：
1. intent_strength必须是0.0-1.0之间的数值
2. confidence表示你对分析的置信度
3. signals数组包含所有检测到的意向信号
4. recommendation只能是: "suggest_appointment", "wait_signal", "no_appointment" 之一
5. 必须包含准确的token使用统计
"""

    async def analyze_intent(self, analysis_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析邀约意向

        Args:
            analysis_context: 分析上下文，包含：
                - current_input: 当前用户输入
                - recent_messages: 最近用户消息列表
                - message_count: 消息数量

        Returns:
            Dict: 意向分析结果
        """
        try:
            # 构建分析文本
            analysis_text = self._build_analysis_text(analysis_context)

            # 构建LLM请求
            request = CompletionsRequest(
                model=self.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": self.analysis_prompt
                    },
                    {
                        "role": "user",
                        "content": f"请分析以下对话中的邀约到店意向：\n\n{analysis_text}"
                    }
                ],
                temperature=0.1,  # 使用较低温度保证一致性
                max_tokens=800
            )

            # 调用LLM
            response = await self.invoke_llm(request)

            # 解析响应
            result = self._parse_llm_response(response)

            # 添加分析元数据
            result["analysis_context"] = {
                "message_count": analysis_context.get("message_count", 0),
                "current_input_length": len(analysis_context.get("current_input", "")),
                "total_analysis_text_length": len(analysis_text)
            }

            return result

        except Exception as e:
            # 错误处理
            return {
                "intent_strength": 0.0,
                "time_window": "unknown",
                "confidence": 0.0,
                "signals": [],
                "recommendation": "no_appointment",
                "analysis_summary": f"分析失败: {str(e)}",
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "error": str(e)
            }

    def _build_analysis_text(self, context: Dict[str, Any]) -> str:
        """
        构建分析文本

        Args:
            context: 分析上下文

        Returns:
            str: 格式化的分析文本
        """
        current_input = context.get("current_input", "")
        recent_messages = context.get("recent_messages", [])
        message_count = context.get("message_count", len(recent_messages))

        analysis_lines = [
            f"=== 邀约到店意向分析 ===",
            f"分析轮次: {message_count}轮对话",
            f"当前用户输入: {current_input}",
            ""
        ]

        if recent_messages:
            analysis_lines.append("历史对话内容:")
            for i, message in enumerate(recent_messages, 1):
                analysis_lines.append(f"第{i}轮: {message}")
            analysis_lines.append("")
        else:
            analysis_lines.append("无历史对话记录")
            analysis_lines.append("")

        analysis_lines.append("请基于以上对话内容，分析用户的到店意向。")

        return "\n".join(analysis_lines)

    def _parse_llm_response(self, response: LLMResponse) -> Dict[str, Any]:
        """
        解析LLM响应

        Args:
            response: LLM响应对象

        Returns:
            Dict: 解析后的结果
        """
        try:
            content = response.choices[0].message.content.strip()

            # 尝试解析JSON
            import json
            import re

            # 提取JSON部分
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                json_content = json_match.group(1)
            else:
                json_content = content

            # 解析JSON
            result = json.loads(json_content)

            # 确保包含token信息
            if "input_tokens" not in result:
                result["input_tokens"] = getattr(response, "prompt_tokens", 0)
            if "output_tokens" not in result:
                result["output_tokens"] = getattr(response, "completion_tokens", 0)
            if "total_tokens" not in result:
                result["total_tokens"] = result.get("input_tokens", 0) + result.get("output_tokens", 0)

            # 验证必要字段
            required_fields = ["intent_strength", "time_window", "confidence", "recommendation"]
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Missing required field: {field}")

            # 验证数值范围
            if not (0.0 <= result["intent_strength"] <= 1.0):
                result["intent_strength"] = max(0.0, min(1.0, result["intent_strength"]))

            if not (0.0 <= result["confidence"] <= 1.0):
                result["confidence"] = max(0.0, min(1.0, result["confidence"]))

            return result

        except json.JSONDecodeError as e:
            # JSON解析失败，返回默认值
            return {
                "intent_strength": 0.0,
                "time_window": "unknown",
                "confidence": 0.0,
                "signals": [],
                "recommendation": "no_appointment",
                "analysis_summary": f"JSON解析失败: {str(e)}",
                "input_tokens": getattr(response, "prompt_tokens", 0),
                "output_tokens": getattr(response, "completion_tokens", 0),
                "total_tokens": getattr(response, "prompt_tokens", 0) + getattr(response, "completion_tokens", 0),
                "parse_error": str(e)
            }
        except Exception as e:
            # 其他错误
            return {
                "intent_strength": 0.0,
                "time_window": "unknown",
                "confidence": 0.0,
                "signals": [],
                "recommendation": "no_appointment",
                "analysis_summary": f"响应解析失败: {str(e)}",
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "error": str(e)
            }