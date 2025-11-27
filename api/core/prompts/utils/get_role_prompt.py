"""
角色提示词生成器模块

根据助理ID查询助理信息并生成角色扮演系统提示词。
供智能体调用以获取个性化的角色设定。

主要功能:
- get_role_prompt: 根据assistant_id查询助理并生成角色提示词Message
"""

from typing import Optional
from uuid import UUID

from libs.types import Message
from services.assistant_service import AssistantService


async def get_role_prompt(
    assistant_id: UUID,
    custom_instructions: Optional[str] = None,
    use_cache: bool = True
) -> Message:
    """
    根据assistant_id查询助理模型并生成角色扮演系统提示词

    通过AssistantService获取助理信息（自动处理缓存和数据库查询），
    然后根据助理属性组装角色设定提示词，返回标准Message实例。

    参数:
        assistant_id: 助理唯一标识符
        custom_instructions: 可选的自定义指令，会追加到提示词末尾
        use_cache: 是否使用Redis缓存，默认为True

    返回:
        Message: 包含role="system"的角色扮演系统提示词消息

    异常:
        AssistantNotFoundException: 助理不存在时抛出

    使用示例:
        >>> from uuid import UUID
        >>> assistant_id = UUID("12345678-1234-5678-1234-567812345678")
        >>> system_message = await get_role_prompt(assistant_id)
        >>> # system_message.role == "system"
        >>> # system_message.content == "你是小美，一位专业的..."
    """
    # 通过服务层获取助理模型（自动处理缓存逻辑）
    assistant = await AssistantService.get_assistant_by_id(assistant_id, use_cache=use_cache)

    # 构建提示词
    prompt_parts = []

    # 角色身份声明
    name_display = assistant.nickname or assistant.assistant_name
    prompt_parts.append(f"你是{name_display}，一位专业的{assistant.occupation}。")

    # 性格特征
    if assistant.personality:
        prompt_parts.append(f"\n【性格特点】\n{assistant.personality}")

    # 专业领域
    if assistant.industry:
        prompt_parts.append(f"\n【专业领域】\n{assistant.industry}")

    # 性别信息
    if assistant.sex:
        prompt_parts.append(f"\n【性别】\n{assistant.sex}")

    # 地址信息
    if assistant.address:
        prompt_parts.append(f"\n【所在地】\n{assistant.address}")

    # 个人资料详情
    if assistant.profile:
        profile_lines = [
            f"- {key.replace('_', ' ').title()}: {value}"
            for key, value in assistant.profile.items()
            if value is not None and value != ""
        ]
        if profile_lines:
            prompt_parts.append(f"\n【个人资料】\n" + "\n".join(profile_lines))

    # 行为准则
    prompt_parts.append(
        "\n【行为准则】\n"
        "- 始终保持角色设定，以第一人称进行对话\n"
        "- 根据性格特点调整语气和表达方式\n"
        "- 在专业领域内提供准确、有价值的建议\n"
        "- 保持友好、专业的服务态度"
    )

    # 自定义指令
    if custom_instructions:
        prompt_parts.append(f"\n【特殊指令】\n{custom_instructions}")

    return Message(role="system", content="\n".join(prompt_parts))


__all__ = ["get_role_prompt"]