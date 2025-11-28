"""
Material Intent Analyzer - 素材意向分析器

负责深度分析用户对话中的素材发送意向信号，识别各种类型的素材需求。

核心功能:
- 多类型素材需求识别（图片、视频、价格、技术参数等）
- 紧急程度和优先级评估
- 具体素材需求提取
- 智能推荐最佳发送时机
"""

from typing import Dict, Any, List
import uuid
from infra.runtimes import CompletionsRequest, LLMResponse
from libs.types import Message


class MaterialIntentAnalyzer:
    """
    素材发送意向分析器

    使用大语言模型分析用户对话，识别各种类型的素材需求，
    并提供紧急程度和优先级评估。
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

        # 素材意向分析提示词
        self.analysis_prompt = """
        你是一个专业的客户素材需求分析专家，专门分析美妆/医美行业客户对各种类型素材的需求意向。

请基于提供的用户对话内容，分析用户是否需要发送任何类型的素材，包括但不限于产品图片、视频、价格信息、技术参数等。

## 素材类型分类：

### 1. 视觉素材 (Visual Materials)
- product_images: 产品图片（包装、实物展示）
- before_after: 对比图（使用前后效果对比）
- usage_videos: 使用视频（产品使用方法演示）
- treatment_process: 治疗过程图（操作流程展示）

### 2. 信息素材 (Information Materials)
- price_list: 价格表（产品价格、服务费用）
- promotion_info: 促销活动（优惠、折扣信息）
- ingredient_list: 成分表（产品成分、配方信息）
- technical_specs: 技术参数（规格、使用方法）

### 3. 证明素材 (Proof Materials)
- certificates: 证书资质（产品认证、权威证明）
- customer_reviews: 客户评价（真实使用反馈）
- clinical_data: 临床数据（试验结果、效果数据）

### 4. 服务素材 (Service Materials)
- store_info: 门店信息（地址、环境照片）
- service_menu: 服务菜单（项目介绍、套餐详情）
- appointment_guide: 预约指南（预约流程、注意事项）

## 评估维度：

### 1. 紧急程度 (Urgency Level)
- high: 用户心情很愉悦
- medium: 用户正常聊天
- low: 用户负面意向，如拒绝、不感兴趣、不需要等

### 2. 优先级评分 (Priority Score)
- 0.8-1.0: 高优先级（应立即处理）
- 0.5-0.7: 中等优先级（近期处理）
- 0.0-0.4: 低优先级（可以延后）

### 3. 置信度 (Confidence)
- 0.8-1.0: 很确信用户有此需求
- 0.5-0.7: 比较确定有需求
- 0.0-0.4: 不太确定，需要进一步确认

## 输出格式：
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
    "specific_requests": [
        "想看看产品实际效果",
        "询问价格信息"
    ],
    "recommendation": "send_soon",
    "analysis_summary": "用户在对话中表现出对产品效果图片和价格信息的明确需求，建议尽快发送相关素材。",
    "input_tokens": 180,
    "output_tokens": 250,
    "total_tokens": 430
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
"""

    async def analyze_intent(self, analysis_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析素材意向

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

            # 构建LLM请求 - 仿照sales agent简化写法
            messages = [
                Message(role="system", content=self.analysis_prompt),
                Message(role="user", content=f"请分析以下对话中的素材发送意向：\n\n{analysis_text}")
            ]

            request = CompletionsRequest(
                id=uuid.uuid4(),
                provider=self.llm_provider,  # 添加provider配置
                model=self.llm_model,
                messages=messages,
                temperature=0.1,
                max_tokens=1000
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
                "urgency_level": "low",
                "material_types": [],
                "priority_score": 0.0,
                "confidence": 0.0,
                "specific_requests": [],
                "recommendation": "no_material",
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
            f"=== 素材发送意向分析 ===",
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

        analysis_lines.extend([
            "请基于以上对话内容，分析用户对以下类型的素材需求：",
            "",
            "1. 视觉素材：产品图片、效果对比、使用视频等",
            "2. 信息素材：价格信息、成分表、技术参数等",
            "3. 证明素材：证书资质、客户评价、临床数据等",
            "4. 服务素材：门店信息、服务菜单、预约指南等",
            "",
            "重点分析：",
            "- 用户明确询问的素材类型",
            "- 用户的紧急程度和优先级",
            "- 具体的素材需求细节"
        ])

        return "\n".join(analysis_lines)

    def _parse_llm_response(self, response: LLMResponse) -> Dict[str, Any]:
        """
        解析LLM响应 - 增强版本，更好的错误处理和调试信息

        Args:
            response: LLM响应对象

        Returns:
            Dict: 解析后的结果
        """
        try:
            # 修复：直接访问 LLMResponse 的 content 属性
            content = response.content.strip() if isinstance(response.content, str) else str(response.content).strip()

            # 尝试解析JSON
            import json
            import re

            # 提取JSON部分 - 支持多种格式
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                json_content = json_match.group(1)
            else:
                # 尝试直接查找JSON对象
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    json_content = json_match.group(0)
                else:
                    json_content = content

            # 解析JSON
            result = json.loads(json_content)

            # 修复：正确获取 token 信息从 LLMResponse.usage 字典
            if hasattr(response, 'usage') and isinstance(response.usage, dict):
                result["input_tokens"] = response.usage.get("input_tokens", 0)
                result["output_tokens"] = response.usage.get("output_tokens", 0)
            else:
                result["input_tokens"] = 0
                result["output_tokens"] = 0

            if "total_tokens" not in result:
                result["total_tokens"] = result.get("input_tokens", 0) + result.get("output_tokens", 0)

            # 验证必要字段 - 使用更宽松的验证和自动填充
            required_fields = ["urgency_level", "material_types", "priority_score", "confidence", "recommendation"]
            missing_fields = []

            for field in required_fields:
                if field not in result:
                    missing_fields.append(field)
                    # 自动填充缺失字段而不是抛出异常
                    if field == "urgency_level":
                        result[field] = "medium"  # 默认中等紧急程度
                    elif field == "material_types":
                        result[field] = []
                    elif field == "priority_score":
                        result[field] = 0.5
                    elif field == "confidence":
                        result[field] = 0.5
                    elif field == "recommendation":
                        result[field] = "wait_for_confirmation"

            # 如果有缺失字段，添加到分析摘要中
            if missing_fields:
                if "analysis_summary" not in result:
                    result["analysis_summary"] = ""
                result["analysis_summary"] = f"自动填充缺失字段: {', '.join(missing_fields)}. " + result.get("analysis_summary", "")

            # 验证数值范围 - 自动修正而不是报错
            if not (0.0 <= result["priority_score"] <= 1.0):
                result["priority_score"] = max(0.0, min(1.0, result["priority_score"]))

            if not (0.0 <= result["confidence"] <= 1.0):
                result["confidence"] = max(0.0, min(1.0, result["confidence"]))

            # 验证urgency_level - 自动修正
            valid_urgency = ["high", "medium", "low"]
            if result["urgency_level"] not in valid_urgency:
                result["urgency_level"] = "medium"

            # 验证recommendation - 自动修正
            valid_recommendations = ["send_immediately", "send_soon", "wait_for_confirmation", "no_material"]
            if result["recommendation"] not in valid_recommendations:
                result["recommendation"] = "wait_for_confirmation"

            # 验证material_types结构 - 修复不完整的数据
            if isinstance(result["material_types"], list):
                for material_type in result["material_types"]:
                    if isinstance(material_type, dict):
                        # 确保必要字段存在
                        if "type" not in material_type:
                            material_type["type"] = "unknown"
                        if "category" not in material_type:
                            material_type["category"] = "unknown"
                        if "description" not in material_type:
                            material_type["description"] = ""
                        if "priority" not in material_type:
                            material_type["priority"] = 0.5
                        # 验证priority范围
                        if not (0.0 <= material_type["priority"] <= 1.0):
                            material_type["priority"] = max(0.0, min(1.0, material_type["priority"]))

            # 确保有specific_requests字段
            if "specific_requests" not in result:
                result["specific_requests"] = []

            return result

        except json.JSONDecodeError as e:
            # 修复：JSON解析失败时正确获取 token 信息
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, 'usage') and isinstance(response.usage, dict):
                input_tokens = response.usage.get("input_tokens", 0)
                output_tokens = response.usage.get("output_tokens", 0)

            return {
                "urgency_level": "medium",  # 改为默认中等而不是low
                "material_types": [],
                "priority_score": 0.5,     # 改为中等
                "confidence": 0.0,
                "specific_requests": [],
                "recommendation": "wait_for_confirmation",  # 改为等待确认而不是直接拒绝
                "analysis_summary": f"JSON解析失败，但从响应中提取了token信息: {str(e)}",
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "parse_error": str(e)
            }
        except Exception as e:
            # 其他错误 - 同样提供更好的默认值
            # 尝试获取token信息
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, 'usage') and isinstance(response.usage, dict):
                input_tokens = response.usage.get("input_tokens", 0)
                output_tokens = response.usage.get("output_tokens", 0)

            return {
                "urgency_level": "medium",
                "material_types": [],
                "priority_score": 0.5,
                "confidence": 0.0,
                "specific_requests": [],
                "recommendation": "wait_for_confirmation",
                "analysis_summary": f"响应解析失败，使用默认值: {str(e)}",
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "error": str(e)
            }