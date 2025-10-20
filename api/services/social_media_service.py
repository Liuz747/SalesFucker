"""
社交媒体公域导流服务

封装 LLM 调用、提示词拼装和结果解析逻辑，为控制器提供复用能力。
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Type
from uuid import uuid4

from pydantic import BaseModel

from config import mas_config
from infra.cache import get_redis_client
from infra.runtimes import LLMClient, ResponseMessageRequest
from libs.types import MethodType
from schemas.social_media_schema import (
    CommentGenerationRequest,
    ReplyGenerationRequest,
    KeywordSummaryRequest,
    ChatGenerationRequest,
)
from utils import get_component_logger, load_yaml_file


logger = get_component_logger(__name__, "SocialMediaService")


class SocialMediaServiceError(Exception):
    """社交媒体导流服务异常"""


class SocialMediaPublicTrafficService:
    """社交媒体引流文案生成服务"""

    def __init__(self):
        project_root = Path(__file__).parent.parent
        config_path = project_root / "data" / "social_media_prompt.yaml"
        
        self.client = LLMClient()
        self.config_path = str(config_path)

    async def invoke_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        output_model: Type[BaseModel]
    ) -> Mapping:
        """调用统一LLM客户端"""
        run_id = uuid4()
        request = ResponseMessageRequest(
            id=run_id,
            model="openai/gpt-5-chat",
            provider="openrouter",
            temperature=0.5,
            max_tokens=4000,
            input=user_prompt,
            system_prompt=system_prompt,
            output_model=output_model
        )
        response = await self.client.responses(request)
        return response.content

    async def load_prompt(self, method: MethodType) -> str:
        redis_client = await get_redis_client()
        cache_key = f"social_media_prompt:{method}"

        try: 
            # Step 1: Check Redis cache
            # cached_prompt = await redis_client.get(cache_key)
            # if cached_prompt:
            #     if isinstance(cached_prompt, bytes):
            #         cached_prompt = cached_prompt.decode()
            #     return cached_prompt

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
            logger.exception(f"公域提示词获取失败：{e}")
            raise

    async def reload_prompt(self, method: MethodType):
        redis_client = await get_redis_client()
        cache_key = f"social_media_prompt:{method}"

        yaml_content = load_yaml_file(self.config_path)
        method_data = yaml_content.get(method)
        if not method_data:
            logger.error(f"未找到提示词配置: {method}")
            raise

        prompt = method_data.get("prompt")
        if not prompt:
            logger.error(f"配置中缺少 'prompt' 字段: {method}")
            raise

        await redis_client.set(cache_key, prompt, ex=mas_config.REDIS_TTL)

    def build_comment_prompt(self, request: CommentGenerationRequest) -> str:
        """构建评论生成提示词"""
        prompt_type_label = "固定文案" if request.comment_type else "风格"
        prompt_content = request.comment_prompt or "无"

        return (
            f"生成一个针对以下内容进行回复的评论。\n\n"
            f"平台: {request.platform}\n"
            f"产品或服务: {request.product_prompt}\n"
            f"类型: {request.comment_type}\n"
            f"{prompt_type_label}: {prompt_content}\n"
            f"目标作品内容: {request.task.product_content}"
        )

    def build_reply_prompt(self, request: ReplyGenerationRequest) -> str:
        """构建回复生成提示词"""
        task_descriptions = []
        for idx, task in enumerate(request.task_list, 1):
            task_descriptions.append(
                f"评论{idx} [ID: {task.id}]:\n  内容: {task.reply_content}"
            )

        prompt_type_label = "固定文案" if request.comment_type else "风格"
        prompt_content = request.comment_prompt or "无"

        return (
            f"请对以下{len(request.task_list)}条评论分别生成回复。\n\n"
            f"平台: {request.platform}\n"
            f"产品或服务: {request.product_prompt}\n"
            f"类型: {request.comment_type}\n"
            f"{prompt_type_label}: {prompt_content}\n\n"
            f"评论列表:\n"
            f"{chr(10).join(task_descriptions)}\n\n"
            f"重要：请务必返回{len(request.task_list)}个任务，每个任务对应上面的一条评论，保持ID一致。"
        )

    def build_keywords_prompt(self, request: KeywordSummaryRequest) -> str:
        """构建关键词摘要提示词"""
        existing_keywords = ', '.join(request.existing_keywords) if request.existing_keywords else '无'

        return (
            f"生成社交媒体关键词和主题摘要。\n\n"
            f"平台: {request.platform}\n"
            f"产品或服务: {request.product_prompt}\n"
            f"已存在关键词: {existing_keywords}\n"
            f"期望生成数量: {request.expecting_count}"
        )

    def build_chat_prompt(self, request: ChatGenerationRequest) -> str:
        """构建私聊回复提示词"""
        prompt_type_label = "固定文案" if request.comment_type else "风格"
        prompt_content = request.chat_prompt or "无"

        return (
            f"生成私聊回复。\n\n"
            f"平台: {request.platform}\n"
            f"产品或服务: {request.product_prompt}\n"
            f"类型: {request.comment_type}\n"
            f"{prompt_type_label}: {prompt_content}\n"
            f"用户消息: {request.content}"
        )

