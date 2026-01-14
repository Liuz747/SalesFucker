"""
回复建议生成服务层
"""

import json
import re
from uuid import UUID

from core.memory import ConversationStore
from infra.runtimes import LLMClient
from libs.factory import infra_registry
from libs.types import Message, MessageParams
from repositories import AssistantRepository
from utils import get_component_logger, get_current_datetime, get_processing_time_ms

logger = get_component_logger(__name__, "SuggestionService")


# TODO: 目前不是工作重心，之后需要修改整体逻辑
async def generate_suggestions(
    input_content: MessageParams,
    thread_id: UUID,
    assistant_id: UUID,
    tenant_id: str = None
) -> tuple[list[str], int, int]:
    """
    生成回复建议

    参数:
        input_content: 标准化后的消息参数列表 (MessageParams)
        thread_id: 线程ID (用于日志和记忆检索)
        assistant_id: 助理ID (用于获取助理人设)
        tenant_id: 租户ID (保留，暂未强制使用)

    返回:
        tuple[list[str], int, int]: (建议回复列表, 输入tokens, 输出tokens)
    """
    try:
        # 初始化LLM客户端
        llm_client = LLMClient()

        # 明确指定使用 "openrouter" provider
        provider = llm_client.active_providers.get("openrouter")
        if not provider:
            raise ValueError("OpenRouter provider not available in active_providers")

        # 1. 获取助理人设信息
        assistant_model = None
        async with infra_registry.get_db_session() as session:
            assistant_orm = await AssistantRepository.get_assistant_by_id(
                assistant_id=assistant_id,
                session=session,
                include_inactive=False
            )
            if assistant_orm:
                assistant_model = assistant_orm.to_business_model()
                logger.info(f"获取到助理人设: {assistant_model.assistant_name}, 个性: {assistant_model.personality}")
            else:
                logger.warning(f"未找到助理ID: {assistant_id}，将使用默认人设")

        # 2. 获取最近的对话记忆
        store = ConversationStore()
        await store.append_messages(thread_id, input_content)
        recent_messages = await store.get_recent(thread_id, limit=10)
        
        # 构建消息列表
        messages = []
        
        # 3. 添加系统预设提示词
        if assistant_model:
            system_prompt = (
                f"你是{assistant_model.assistant_name}，一位{assistant_model.occupation}。\n"
                f"个性特征：{assistant_model.personality}\n"
                f"专业领域：{assistant_model.industry}\n"
                f"请根据你的专业背景和个性特征，结合对话上下文，生成3条合适的建议回复。\n"
                f"回复应该体现你的专业性和个性特点。\n"
                f"请务必以JSON数组格式返回，例如：[\"建议1\", \"建议2\", \"建议3\"]。"
            )
        else:
            system_prompt = (
                "你是一个专业的智能助手。请根据上下文回复用户，生成3条合适的建议回复。"
                "请务必以JSON数组格式返回，例如：[\"建议1\", \"建议2\", \"建议3\"]。"
            )
        messages.append(Message(role="system", content=system_prompt))
        
        # 4. 添加历史消息
        messages.extend(recent_messages + input_content)
        
        # 调用OpenAI生成3条回复
        start_time = get_current_datetime()
        
        # 准备消息格式 (provider specific)
        formatted_messages = []
        for m in messages:
            content = provider._format_message_content(m.content)
            formatted_messages.append({"role": m.role, "content": content})

        response = await provider.client.chat.completions.create(
            model="openai/gpt-oss-120b:exacto",
            messages=formatted_messages,
            n=1,  # 改回 n=1，使用 JSON 数组获取多条建议
            temperature=0.7
        )
        
        processing_time = get_processing_time_ms(start_time)
        
        # 构造输出
        suggestions_list = []

        response_content = response.choices[0].message.content.strip()

        await store.append_messages(thread_id, [Message(role="assistant", content=response_content)])

        # 尝试清理 markdown 标记
        if response_content.startswith("```json") and response_content.endswith("```"):
            response_content = response_content[7:-3].strip()

        try:
            # 尝试解析JSON数组
            suggestions = json.loads(response_content)
            if isinstance(suggestions, list):
                for suggestion in suggestions:
                    suggestions_list.append(str(suggestion))
            else:
                # 这是一个非列表的JSON对象或值
                suggestions_list.append(str(suggestions))
        except json.JSONDecodeError:
            # JSON解析失败，尝试按行分割作为兜底
            logger.warning(f"建议生成 JSON解析失败: {response_content}")
            lines = [line for line in response_content.split('\n') if line.strip()]
            for line in lines:
                # 简单清理序号如 "1. "
                cleaned_line = re.sub(r'^\d+[\.、]\s*', '', line.strip())
                if cleaned_line:
                    suggestions_list.append(cleaned_line)

        # Token使用统计
        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0

        logger.info(f"建议生成完成 - 输入tokens: {input_tokens}, 输出tokens: {output_tokens}, 处理时间: {processing_time}ms")

        return suggestions_list, input_tokens, output_tokens
        
    except Exception as e:
        logger.error(f"建议生成失败 - 线程: {thread_id}: {e}", exc_info=True)
        raise e
