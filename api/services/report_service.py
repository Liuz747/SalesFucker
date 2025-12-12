"""
报告生成服务

负责处理用户分析报告的生成逻辑，包括：
1. 获取对话记忆上下文
2. 组装分析 Prompt
3. 调用 LLM 生成报告
"""

import json
import re
import time
from uuid import UUID, uuid4
from typing import Optional, List, Dict, Any

from core.memory import StorageManager
from infra.runtimes import LLMClient, CompletionsRequest
from libs.types import Message
from utils import get_component_logger

logger = get_component_logger(__name__, "ReportService")


def _log_step_time(step_name: str, start_time: float, thread_id: UUID):
    """记录步骤耗时"""
    elapsed_ms = (time.time() - start_time) * 1000
    logger.info(f"[{thread_id}] {step_name} 耗时: {elapsed_ms:.2f}ms")

class ReportService:
    """
    报告生成服务类
    """
    
    @staticmethod
    async def generate_user_analysis(tenant_id: str, thread_id: UUID) -> Dict[str, Any]:
        """
        生成用户分析报告
        
        Args:
            tenant_id: 租户ID
            thread_id: 线程ID
            
        Returns:
            Dict[str, Any]: 生成的报告结果，包含 report_result, report_tokens, error_message
        """
        try:
            total_start = time.time()
            logger.info(f"[{thread_id}] 开始生成报告")

            # 1. 初始化记忆管理器
            memory_manager = StorageManager()

            # 2. 获取记忆 (Short-term + Long-term)
            step_start = time.time()
            short_term_messages, long_term_memories = await memory_manager.retrieve_context(
                tenant_id=tenant_id,
                thread_id=thread_id,
                query_text=None
            )
            _log_step_time("获取记忆上下文", step_start, thread_id)

            # 3. 格式化记忆内容
            formatted_history = []
            
            # 添加长期记忆
            if long_term_memories:
                formatted_history.append("【长期记忆】")
                for m in long_term_memories:
                    content = m.get('content', '')
                    if content:
                        formatted_history.append(f"- {content}")
                formatted_history.append("") # 空行分隔
            
            # 添加短期对话
            formatted_history.append("【短期对话】")
            for msg in short_term_messages:
                # 角色映射
                role_label = "【未知】"
                if msg.role == "user":
                    role_label = "【客户】"
                elif msg.role == "assistant":
                    role_label = "【客服】"
                elif msg.role == "system":
                    continue # 跳过系统消息，避免干扰分析
                else:
                    role_label = f"【{msg.role}】"
                
                formatted_history.append(f"{role_label}: {msg.content}")
            
            memory_content = "\n".join(formatted_history)
            
            # 4. 构建 System Prompt
            system_prompt = f"""# 🎯 **客户综合分析专家**

你是一名刑侦专家级别的专业客户分析师，擅长全方位分析客户画像和心理测写。请基于对话内容、系统指标和社交媒体数据，对客户进行综合分析。

## 📋 **输入数据**

### 对话内容

```
{memory_content}
```

## 🎯 **分析维度**

请分析以下所有字段，重点关注整合所有信息生成**综合总结**。请返回一个标准的 JSON 对象，包含以下 Key：

[
    {{"key": "name", "label": "姓名/称呼", "description": "客户的姓名或常用称呼"}},
    {{"key": "gender", "label": "性别", "description": "客户的性别"}},
    {{"key": "age", "label": "年龄", "description": "客户的年龄（6-90）"}},
    {{"key": "birthday", "label": "生日", "description": "客户生日（如8月2日）"}},
    {{"key": "city", "label": "城市/住址", "description": "客户所在的城市或住址"}},
    {{"key": "phone", "label": "手机号", "description": "客户的手机号码"}},
    {{"key": "zodiac", "label": "星座", "description": "客户的星座"}},
    {{"key": "occupation", "label": "职业", "description": "客户的职业"}},
    {{"key": "identity_label", "label": "身份标签", "description": "客户的社会身份标签（如白领/宝妈/学生）"}},
    {{"key": "spouse_job", "label": "配偶职业", "description": "客户配偶的职业"}},
    {{"key": "children_job", "label": "子女职业", "description": "客户子女的职业/学业状况"}},
    {{"key": "assets", "label": "资产状况", "description": "客户综合消费能力概述"}},
    {{"key": "health_status", "label": "客户健康状况", "description": "身体健康状况和注意事项"}},
    {{"key": "special_period", "label": "客户特殊时期", "description": "特殊生理/心理状态或时期"}},
    {{"key": "special_beliefs", "label": "客户特殊信仰事宜", "description": "客户的特殊信仰/习惯"}},

    {{"key": "source_channel", "label": "客户来源渠道", "description": "客户来源渠道（如小红书/朋友推荐/抖音）"}},
    {{"key": "customer_level", "label": "客户分级", "description": "客户需求明确程度（0-3）"}},
    {{"key": "customer_journey", "label": "客户里程", "description": "邀约/到店/消费进度（0-3）"}},

    {{"key": "desired_products", "label": "客户想预约的产品/服务", "description": "客户明确想要的产品或服务"}},
    {{"key": "needs", "label": "客户需求", "description": "客户表达的需求（如改善、提升）"}},
    {{"key": "pain_points", "label": "客户痛点", "description": "客户具体问题或困扰"}},
    {{"key": "emotional_motivation", "label": "客户需求的情绪动机", "description": "客户需求背后的情绪动机"}},
    {{"key": "expected_effect", "label": "客户期望效果", "description": "客户期望达到的效果"}},
    {{"key": "past_experiences", "label": "客户相关历史经历", "description": "客户过往的相关经历"}},
    {{"key": "satisfaction_with_past", "label": "客户对过往经历的满意度", "description": "对历史经历的满意度评价"}},
    {{"key": "adverse_experience", "label": "客户的不良体验", "description": "过往的不良体验"}},
    {{"key": "service_providers", "label": "客户接触过的服务商", "description": "历史服务提供商名称"}},
    {{"key": "service_frequency", "label": "客户服务频率", "description": "历史服务的时间频率"}},
    {{"key": "risk_aversion", "label": "客户风险抗拒情绪", "description": "对风险/不确定性的抗拒情绪"}},
    {{"key": "risk_items", "label": "风险项", "description": "相关风险项评估"}},

    {{"key": "budget_range", "label": "客户预算区间", "description": "客户的预算范围"}},
    {{"key": "decision_deadline", "label": "客户决策时限", "description": "客户的决策周期（如1-2周）"}},
    {{"key": "willingness_to_pay", "label": "客户支付意愿", "description": "客户的支付意愿（高/中/低）"}},
    {{"key": "payment_barriers", "label": "阻碍客户支付的原因", "description": "客户的支付障碍（如价格/恢复期）"}},
    {{"key": "lead_score", "label": "综合成交可能性分数", "description": "0-100分的成交可能性评估"}},
    {{"key": "repurchase_potential_12m", "label": "十二个月复购潜力", "description": "未来12个月复购潜力"}},
    {{"key": "spending_autonomy", "label": "客户自主消费能力", "description": "客户的消费决策权程度"}},
    {{"key": "avg_spend_medical_beauty", "label": "客户业务平均消费金额", "description": "业务相关的平均消费水平"}},
    {{"key": "loyalty", "label": "客户对店忠诚度", "description": "客户对门店的忠诚度"}},

    {{"key": "chat_topics", "label": "客户聊天兴趣话题", "description": "聊天关注的话题"}},
    {{"key": "chat_keywords", "label": "客户聊天高频关键词", "description": "聊天中的高频词"}},
    {{"key": "moments_interaction_direction", "label": "朋友圈互动方向", "description": "朋友圈与助手的互动统计与方向"}},
    {{"key": "moments_interest_topics", "label": "朋友圈兴趣主题", "description": "朋友圈体现的兴趣主题"}},
    {{"key": "moments_summary", "label": "朋友圈画像总结", "description": "朋友圈内容所体现的人设/画像总结"}},

    {{"key": "emotion_score", "label": "客户情绪评分", "description": "客户的情绪评分（1-100）"}},
    {{"key": "personality_brief", "label": "客户性格", "description": "基于MBTI维度的性格分析"}},
    {{"key": "decision_style", "label": "客户决策风格", "description": "客户的决策偏好/风格"}},
    {{"key": "emotion_tone", "label": "客户情绪基调", "description": "对话/朋友圈的情绪基调"}},

    {{"key": "overall_summary", "label": "综合总结", "description": "基于所有非空分析字段内容，生成一段流畅连贯的中文总结，使用标准MD格式，避免使用英文"}},
    {{"key": "action_1", "label": "动作一与建议时间", "description": "首要跟进行动与建议时间点"}},
    {{"key": "action_2", "label": "动作二与建议时间", "description": "次要跟进行动与建议时间点"}},
    {{"key": "alternatives", "label": "备选方案", "description": "可替代的策略或方案"}}
]

## 📝 **分析原则**

### 🔍 **客观事实提取规则**
- **必须基于客户明确表达的信息**
- 如果客户没有明确提及，不生成相应信息 (使用空字符串 "")

### 🧠 **主观推断规则**
- 只能基于客户明确表达的内容进行合理推断
- 如果某一字段推断依据不足，不输出该字段内容 (使用空字符串 "")
- 一旦感到某字段足以从对话中分析，则选择生成

### 🚨 **角色识别规则**
- **客户**：标记为【客户】的消息才是客户说的话
- **客服**：标记为【客服】的消息是客服说的话

### 📋 **字段填写要求**
- 系统计算的指标必须直接使用，不要修改
- 数值型字段必须是数字类型（年龄、分级、评分等）
- 所有字段都必须填写
- 客观事实无法获取时填写空字符串""
- 主观推断无法进行时填写空字符串""

### 🎯 **综合总结特别要求**
- **综合总结 (overall_summary)** 字段是最重要的输出，必须基于所有非空分析字段内容生成
- 使用中文以及标准MD格式，可以用一些无序列表、加粗、标点等格式语法
- 内容要涵盖客户画像、需求分析、行为特征、跟进建议等关键信息
- 语言要自然流畅，避免生硬的分点罗列
- 长度要充实，至少200字以上，全面反映客户特征

请直接返回纯净的 JSON 格式内容。
"""
            
            # 5. 调用 LLM
            step_start = time.time()
            llm_messages = [Message(role="system", content=system_prompt)]
            # 注意：这里不再次添加 short_term_messages，因为已经格式化到 system_prompt 中了

            llm_client = LLMClient()
            request = CompletionsRequest(
                id=str(uuid4()),
                provider="openrouter",
                model="qwen/qwen-plus-2025-07-28", # 或使用 gpt-4o 等
                messages=llm_messages,
                thread_id=thread_id,
                temperature=0.7
            )

            response = await llm_client.completions(request)
            _log_step_time("LLM调用", step_start, thread_id)
            
            # 6. 解析响应
            content = response.content
            
            # 尝试提取 JSON
            json_content = {}
            try:
                # 移除可能的 markdown 标记
                cleaned_content = re.sub(r'^```json\s*', '', content)
                cleaned_content = re.sub(r'\s*```$', '', cleaned_content)
                json_content = json.loads(cleaned_content)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON response: {content[:100]}...")
                # 降级处理：如果无法解析，将原始内容放入 result
                json_content = {"overall_summary": content}

            # 7. 构建返回结果
            # 提取 token 使用情况
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

            result = {
                "report_result": json_content.get("overall_summary", ""),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "error_message": None
            }

            total_elapsed_ms = (time.time() - total_start) * 1000
            logger.info(f"[{thread_id}] 报告生成完成, 总耗时: {total_elapsed_ms:.2f}ms, input_tokens: {input_tokens}, output_tokens: {output_tokens}")

            return result

        except Exception as e:
            logger.error(f"报告生成失败: {e}", exc_info=True)
            return {
                "report_result": "",
                "input_tokens": 0,
                "output_tokens": 0,
                "error_message": str(e)
            }
