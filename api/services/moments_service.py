"""
朋友圈智能分析服务

专门处理朋友圈内容的多模态分析，独立于社交媒体服务，
支持文本和图像的智能分析，提供互动建议。
"""

import asyncio
from pathlib import Path
from typing import Type
from uuid import uuid4

from pydantic import BaseModel

from config import mas_config
from core.memory import StorageManager
from infra.runtimes import LLMClient, CompletionsRequest, LLMResponse
from libs.factory import infra_registry
from libs.types import MethodType, Message, InputContent, InputType, MemoryType
from schemas.social_media_schema import (
    MomentsAnalysisRequest,
    MomentsAnalysisResponse,
    SocialMediaActionType,
)
from utils import get_component_logger, load_yaml_file


logger = get_component_logger(__name__, "MomentsService")


class MomentsServiceError(Exception):
    """朋友圈服务异常"""


class MomentsAnalysisService:
    """朋友圈智能分析服务"""

    def __init__(self):
        project_root = Path(__file__).parent.parent
        config_path = project_root / "data" / "social_media_prompt.yaml"

        self.client = LLMClient()
        self.config_path = str(config_path)
        self.storage_manager = StorageManager()

    async def invoke_llm_multimodal(
        self,
        system_prompt: str,
        text_content: str,
        image_urls: list[str],
        output_model: Type[BaseModel]
    ) -> LLMResponse:
        """调用多模态LLM客户端，支持图片和文本混合分析"""
        run_id = uuid4()

        # 构建多模态内容
        content = [InputContent(type=InputType.TEXT, content=text_content)]
        for url in image_urls:
            content.append(InputContent(type=InputType.IMAGE, content=url))

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=content)
        ]

        request = CompletionsRequest(
            id=run_id,
            model="openai/gpt-4o",  # 使用支持视觉的模型
            provider="openrouter",
            temperature=0.3,  # 较低温度确保稳定输出
            max_tokens=4000,
            messages=messages,
            output_model=output_model
        )
        response = await self.client.completions(request)
        return response

    async def invoke_llm_text(
        self,
        system_prompt: str,
        user_prompt: str,
        output_model: Type[BaseModel]
    ) -> LLMResponse:
        """调用文本LLM客户端，处理纯文本分析"""
        run_id = uuid4()
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]
        request = CompletionsRequest(
            id=run_id,
            model="openai/gpt-5",  # 文本分析使用更经济的模型
            provider="openrouter",
            temperature=1,
            max_tokens=1000,  # 朋友圈分析通常不需要很长的回复
            messages=messages,
            output_model=output_model
        )
        response = await self.client.completions(request)
        return response

    async def load_prompt(self, method: MethodType) -> str:
        """加载提示词配置，支持Redis缓存"""
        redis_client = infra_registry.get_cached_clients().redis
        cache_key = f"social_media_prompt:{method}"

        try:
            # Step 1: Check Redis cache
            cached_prompt = await redis_client.get(cache_key)
            if cached_prompt:
                if isinstance(cached_prompt, bytes):
                    cached_prompt = cached_prompt.decode()
                return cached_prompt

            # Step 2: Load from YAML
            yaml_content = load_yaml_file(self.config_path)
            method_data = yaml_content.get(method)
            if not method_data:
                logger.error(f"未找到提示词配置: {method}")
                raise

            prompt = method_data.get("prompt")
            if not prompt:
                logger.error(f"配置中缺少 'prompt' 字段: {method}")
                raise

            # Step 3: Cache to Redis
            await redis_client.set(cache_key, prompt, ex=mas_config.REDIS_TTL)

            return prompt

        except Exception as e:
            logger.exception(f"朋友圈提示词获取失败：{e}")
            raise

    @staticmethod
    def build_moments_prompt(request: MomentsAnalysisRequest) -> str:
        """构建朋友圈分析提示词"""
        moment_descriptions = []
        for idx, moment in enumerate(request.task_list, 1):
            desc = f"朋友圈{idx} [ID: {moment.id}]:"

            # 处理文案内容
            if moment.moment_content:
                desc += f"\n  文案: {moment.moment_content}"

            # 处理图片列表
            if moment.url_list:
                desc += f"\n  图片: {len(moment.url_list)}张图片"
                if len(moment.url_list) <= 3:
                    desc += f" - {', '.join(moment.url_list)}"
                else:
                    desc += f" - {', '.join(moment.url_list[:2])}等{len(moment.url_list)}张"

            # 处理空白朋友圈
            if not moment.moment_content and not moment.url_list:
                desc += "\n  内容: 空白朋友圈（仅可见好友可看到）"

            moment_descriptions.append(desc)

        return (
            f"请分析以下{len(request.task_list)}条朋友圈内容，并根据内容特点决定是否进行互动。\n\n"
            f"朋友圈内容列表:\n"
            f"{chr(10).join(moment_descriptions)}\n\n"
            f"注意事项:\n"
            f"- 必须返回{len(request.task_list)}个任务结果，每个任务对应上面的一条朋友圈\n"
            f"- 严格保持ID一致性，不要遗漏或重复\n"
            f"- 严格按照系统提示词中的安全原则和互动策略执行\n"
            f"- 对于图片内容，请结合视觉信息进行综合判断"
        )

    async def analyze_moments(self, request: MomentsAnalysisRequest, tenant_id: str) -> MomentsAnalysisResponse:
        """分析朋友圈内容并生成互动建议"""
        try:
            # 加载系统提示词
            system_prompt = await self.load_prompt(MethodType.MOMENTS)

            # 构建用户提示词
            user_prompt = self.build_moments_prompt(request)

            logger.info(f"开始分析 {len(request.task_list)} 条朋友圈内容")

            # 收集所有图片URL
            all_image_urls = []
            for moment in request.task_list:
                if moment.url_list:
                    all_image_urls.extend(moment.url_list)

            # 选择调用方式：有图片使用多模态，无图片使用文本模型
            if all_image_urls:
                logger.info(f"检测到 {len(all_image_urls)} 张图片，使用多模态LLM进行视觉分析")
                llm_response = await self.invoke_llm_multimodal(
                    system_prompt=system_prompt,
                    text_content=user_prompt,
                    image_urls=all_image_urls,
                    output_model=MomentsAnalysisResponse
                )
            else:
                logger.info("纯文本内容，使用标准文本LLM分析")
                llm_response = await self.invoke_llm_text(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    output_model=MomentsAnalysisResponse
                )

            # 从 LLMResponse 中提取结果和token信息
            result = llm_response.content

            # 创建包含token信息的响应
            final_response = MomentsAnalysisResponse(
                tasks=result.tasks,
                input_tokens=llm_response.usage.input_tokens,
                output_tokens=llm_response.usage.output_tokens
            )

            tasks_count = len(result.tasks)
            logger.info(f"朋友圈分析完成，生成 {tasks_count} 个互动建议，使用Token: 输入{llm_response.usage.input_tokens}, 输出{llm_response.usage.output_tokens}")

            # 验证返回结果的完整性
            if tasks_count != len(request.task_list):
                logger.warning(f"返回任务数量({tasks_count})与输入数量({len(request.task_list)})不匹配")

            # 存储互动记录到记忆
            asyncio.create_task(self._store_moments_memories(
                request,
                final_response,
                tenant_id
            ))

            # 返回包含token信息的结果
            return final_response

        except Exception as e:
            logger.exception(f"朋友圈分析失败: {e}")
            raise MomentsServiceError(f"朋友圈内容分析失败: {str(e)}")

    async def _store_moments_memories(
        self,
        request: MomentsAnalysisRequest,
        result: MomentsAnalysisResponse,
        tenant_id: str
    ):
        """存储朋友圈互动记录到记忆"""
        try:
            # 建立 id 到 moment 的映射
            moment_map = {m.id: m for m in request.task_list}

            for task_result in result.tasks:
                moment = moment_map.get(task_result.id)
                if not moment or not moment.thread_id:
                    continue

                # 仅当有互动行为（点赞或评论）时存储
                if not task_result.actions:
                    continue

                # 构建记忆内容
                content_parts = []
                if moment.moment_content:
                    content_parts.append(f"用户发布朋友圈: {moment.moment_content}")
                
                if moment.url_list:
                    content_parts.append(f"[包含{len(moment.url_list)}张图片]")
                
                interaction_parts = []
                if SocialMediaActionType.LIKE in task_result.actions: # 假设 1 是点赞
                    interaction_parts.append("我点赞了")
                if SocialMediaActionType.COMMENT in task_result.actions and task_result.message: # 假设 2 是评论
                    interaction_parts.append(f"我评论: {task_result.message}")
                
                if interaction_parts:
                    content_parts.append(f"交互记录: {', '.join(interaction_parts)}")

                memory_content = " | ".join(content_parts)

                # 存储到记忆
                await self.storage_manager.add_episodic_memory(
                    tenant_id=tenant_id,
                    thread_id=moment.thread_id,
                    content=memory_content,
                    memory_type=MemoryType.MOMENTS_INTERACTION,
                    tags=["moments", "interaction"]
                )
                logger.debug(f"朋友圈互动记忆已存储: {moment.id} -> {moment.thread_id}")

        except Exception as e:
            logger.error(f"存储朋友圈记忆失败: {e}", exc_info=True)
            # 不抛出异常，以免影响主流程
