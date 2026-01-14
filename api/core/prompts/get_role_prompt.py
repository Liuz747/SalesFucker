"""
角色提示词生成器模块

根据助理ID查询助理信息并生成角色扮演系统提示词。
供智能体调用以获取个性化的角色设定。

主要功能:
- get_role_prompt: 根据assistant_id查询助理并生成角色提示词Message
- get_thread_context_prompt: 根据thread_id生成客户上下文提示词
- get_combined_system_prompt: 组合助理角色和客户上下文的完整系统提示词
"""

from typing import Optional
from uuid import UUID

from libs.exceptions import AssistantInactiveException, ThreadNotFoundException
from libs.types import AccountStatus, Message
from services import AssistantService, ThreadService
from .template_loader import get_prompt_template


async def get_role_prompt(
    assistant_id: UUID,
    custom_instructions: Optional[str] = None,
    use_cache: bool = True
) -> Message:
    """
    根据assistant_id查询助理模型并生成角色扮演系统提示词

    通过AssistantService获取助理信息（自动处理缓存和数据库查询），
    然后使用Jinja2模板组装角色设定提示词，返回标准Message实例。

    参数:
        assistant_id: 助理唯一标识符
        custom_instructions: 可选的自定义指令，会追加到提示词末尾
        use_cache: 是否使用Redis缓存，默认为True

    返回:
        Message: 包含role="system"的角色扮演系统提示词消息
    """
    # 通过服务层获取助理模型（自动处理缓存逻辑）
    assistant = await AssistantService.get_assistant_by_id(assistant_id, use_cache=use_cache)

    if assistant.status != AccountStatus.ACTIVE:
        raise AssistantInactiveException(assistant_id, assistant.status.value) 

    # 准备模板上下文
    name_display = assistant.nickname or assistant.assistant_name
    profile_lines = None

    if assistant.profile:
        profile_lines = [
            f"- {key.replace('_', ' ').title()}: {value}"
            for key, value in assistant.profile.items()
            if value is not None and value != ""
        ]

    # 使用统一的模板加载器渲染
    content = get_prompt_template(
        "role_prompt",
        name_display=name_display,
        occupation=assistant.occupation,
        personality=assistant.personality,
        industry=assistant.industry,
        sex=assistant.sex,
        address=assistant.address,
        profile_lines=profile_lines,
        custom_instructions=custom_instructions
    )

    return Message(role="system", content=content)


async def get_thread_context_prompt(
    thread_id: UUID,
    custom_context: Optional[str] = None
) -> Message:
    """
    根据thread_id查询客户线程信息并生成上下文提示词

    通过ThreadService获取线程信息（自动处理缓存和数据库查询），
    然后使用Jinja2模板生成客户背景上下文提示词。

    参数:
        thread_id: 线程唯一标识符
        custom_context: 可选的自定义上下文信息

    返回:
        Message: 包含role="user"的客户上下文提示词消息

    异常:
        ThreadNotFoundException: 线程不存在时抛出
    """
    # 通过服务层获取线程信息
    thread = await ThreadService.get_thread(thread_id)

    if not thread:
        raise ThreadNotFoundException(thread_id)

    # 使用统一的模板加载器渲染
    content = get_prompt_template(
        "thread_context_prompt",
        name=thread.name,
        nickname=thread.nickname,
        real_name=thread.real_name,
        sex=thread.sex.value if thread.sex else None,
        age=thread.age,
        occupation=thread.occupation,
        phone=thread.phone,
        services=thread.services,
        is_converted=thread.is_converted,
        custom_context=custom_context
    )

    return Message(role="user", content=content)


async def get_combined_system_prompt(
    assistant_id: UUID,
    thread_id: UUID,
    custom_instructions: Optional[str] = None,
    custom_context: Optional[str] = None
) -> Message:
    """
    获取组合的系统提示词（助理角色 + 客户上下文）

    同时获取助理角色设定和客户背景信息，生成完整的系统提示词。
    这个提示词包含了助理应该如何行动以及客户的具体情况。

    参数:
        assistant_id: 助理ID
        thread_id: 线程ID
        custom_instructions: 自定义人设指令
        custom_context: 自定义客户上下文

    返回:
        Message: 完整的系统提示词
    """

    # 生成两部分提示词
    role_msg = await get_role_prompt(assistant_id, custom_instructions)
    thread_msg = await get_thread_context_prompt(thread_id, custom_context)

    # 使用组合模板
    content = get_prompt_template(
        "combined_system_prompt",
        role_section=role_msg.content,
        thread_section=thread_msg.content
    )

    return Message(role="system", content=content)