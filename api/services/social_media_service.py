"""
社交媒体公域导流服务

封装 LLM 调用、提示词拼装和结果解析逻辑，为控制器提供复用能力。
"""

from pathlib import Path
from typing import Type
from time import time
from uuid import uuid4

from pydantic import BaseModel

from config import mas_config
from infra.cache import get_redis_client
from infra.runtimes import LLMClient, CompletionsRequest, LLMResponse
from libs.types import MethodType, Message, TextBeautifyActionType
from schemas.social_media_schema import (
    CommentGenerationRequest,
    ReplyGenerationRequest,
    KeywordSummaryRequest,
    ChatGenerationRequest,
    TextBeautifyRequest,
    TextBeautifyResponse,
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
    ) -> LLMResponse:
        """调用统一LLM客户端"""
        run_id = uuid4()
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]
        request = CompletionsRequest(
            id=run_id,
            model="openai/gpt-oss-120b:exacto",
            provider="openrouter",
            temperature=0.5,
            max_tokens=4000,
            messages=messages,
            output_model=output_model
        )
        response = await self.client.completions(request)
        return response

    async def load_prompt(self, method: MethodType) -> str:
        redis_client = await get_redis_client()
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

    def build_text_beautify_prompt(self, request: TextBeautifyRequest) -> str:
        """构建文本美化提示词"""
        action_desc = "缩写" if request.action_type == TextBeautifyActionType.COMPRESS else "扩写"
        style_desc = request.style or "专业、简洁、易读"

        return (
            f"请对以下文本进行{action_desc}美化处理。\n\n"
            f"原始文本: {request.source_text}\n"
            f"期望数量: {request.result_count}\n"
            f"风格要求: {style_desc}\n\n"
            f"请提供{request.result_count}个不同版本的{action_desc}结果，"
            f"每个版本都要保持原意的同时提升表达效果。"
        )

    async def text_beautify(self, request: TextBeautifyRequest) -> TextBeautifyResponse:
        """执行文本美化处理"""
        start_time = time()
        run_id = str(uuid4())

        # 构建提示词
        user_prompt = self.build_text_beautify_prompt(request)

        # 根据操作类型选择系统提示词
        if request.action_type == TextBeautifyActionType.COMPRESS:
            system_prompt = await self.load_prompt(method=MethodType.COMPRESS)
        else:
            system_prompt = await self.load_prompt(method=MethodType.EXPAND)

        try:
            # 直接调用LLM客户端，不通过invoke_llm
            run_id_llm = uuid4()
            messages = [
                Message(role="system", content=system_prompt),
                Message(role="user", content=user_prompt)
            ]
            llm_request = CompletionsRequest(
                id=run_id_llm,
                model="openai/gpt-oss-120b:exacto",
                provider="openrouter",
                temperature=0.5,
                max_tokens=4000,
                messages=messages,
                output_model=None
            )
            response = await self.client.completions(request=llm_request)

            # 获取原始响应文本
            llm_result = response.content if hasattr(response, 'content') else str(response)

            # 解析响应文本为多个美化结果
            beautified_texts = self._parse_beautify_response(llm_result, request.result_count)

            processing_time = (time() - start_time) * 1000  # 转换为毫秒

            return TextBeautifyResponse(
                run_id=run_id,
                status="completed",
                response=beautified_texts,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                processing_time=processing_time,
                action_type=request.action_type
            )

        except Exception as e:
            logger.error(f"文本美化处理失败: {e}")
            return TextBeautifyResponse(
                run_id=run_id,
                status="failed",
                response=[],
                input_tokens=0,
                output_tokens=0,
                processing_time=(time() - start_time) * 1000,
                action_type=request.action_type
            )

    def _parse_beautify_response(self, response: str, expected_count: int) -> list[str]:
        """解析LLM响应为多个美化文本"""
        # 尝试按数字编号分割
        import re

        # 按数字序号分割，如 "1. 文本一 2. 文本二"
        numbered_pattern = r'\d+[\.、]\s*'
        parts = re.split(numbered_pattern, response.strip())

        # 过滤空字符串
        texts = [part.strip() for part in parts if part.strip()]

        # 如果没有找到编号分割，尝试按换行分割
        if len(texts) <= 1:
            texts = [line.strip() for line in response.strip().split('\n') if line.strip()]

        # 确保返回期望数量的结果
        if len(texts) < expected_count:
            # 如果结果不够，复制现有结果或使用空字符串填充
            while len(texts) < expected_count:
                if texts:
                    texts.append(texts[-1] + f" (变体{len(texts)+1})")
                else:
                    texts.append("")
        elif len(texts) > expected_count:
            texts = texts[:expected_count]

        return texts
