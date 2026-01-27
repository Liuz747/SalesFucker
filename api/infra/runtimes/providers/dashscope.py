"""
DashScope供应商实现

提供阿里云通义千问系列模型的调用功能。
"""

from typing import Any, Optional

import aiohttp
import dashscope
from dashscope import (
    AioGeneration,
    AioMultiModalConversation,
    Transcription
)
from dashscope.api_entities.dashscope_response import (
    GenerationResponse,
    Message,
    MultiModalConversationResponse
)

from libs.exceptions import (
    ASRTranscriptionException,
    ASRDownloadException,
    BaseHTTPException
)
from libs.types import MessageParams
from utils import get_component_logger
from .base import BaseProvider
from ..entities import (
    CompletionsRequest,
    LLMResponse,
    Provider,
    TokenUsage
)

logger = get_component_logger(__name__, "DashScopeProvider")


class DashScopeProvider(BaseProvider):
    """DashScope供应商实现类"""

    def __init__(self, provider: Provider):
        """
        初始化DashScope供应商

        Args:
            provider: DashScope配置
        """
        super().__init__(provider)
        dashscope.api_key = provider.api_key
        if provider.base_url:
            dashscope.base_http_api_url = provider.base_url

    def _format_message_content(self, content) -> str | list[dict[str, Any]]:
        """
        将通用content格式转换为DashScope特定格式

        Args:
            content: InputContentParams

        Returns:
            str 或 list[dict]: DashScope API所需的content格式
        """
        if isinstance(content, str):
            return content

        # 将InputContent序列转换为DashScope要求的字段
        formatted: list[dict[str, Any]] = []
        for item in content:
            if item.type == "text":
                formatted.append({"text": item.content})
            elif item.type == "input_image":
                formatted.append({"image": item.content})
        return formatted

    def _format_messages(self, messages: MessageParams) -> list[Message]:
        """
        将通用消息列表转换为DashScope特定格式

        Args:
            messages: MessageParams（消息列表）

        Returns:
            list[Message]: DashScope API所需的消息格式
        """
        formatted_messages: list[Message] = []
        for m in messages:
            formatted_content = self._format_message_content(m.content) if m.content else ""
            message = Message(
                role=m.role,
                content=formatted_content
            )
            formatted_messages.append(message)

        return formatted_messages

    @staticmethod
    def _has_multimodal_input(messages: MessageParams) -> bool:
        """
        检测请求是否包含多模态内容

        Args:
            messages: 输入内容

        Returns:
            bool: 如果包含多模态内容返回True，否则返回False
        """
        for message in messages:
            if message.content and not isinstance(message.content, str):
                # content是Sequence[InputContent]类型，检查是否有非文本类型
                for item in message.content:
                    if item.type != "text":
                        return True
        return False

    async def completions(self, request: CompletionsRequest) -> LLMResponse:
        """
        发送聊天请求到DashScope

        根据请求内容自动识别是否包含多模态输入，
        并路由到相应的API调用方法，然后统一处理响应。

        Args:
            request: LLM请求

        Returns:
            LLMResponse: DashScope响应
        """
        try:
            formatted_messages = self._format_messages(request.messages)

            # 根据请求类型选择合适的API调用方法
            if self._has_multimodal_input(request.messages):
                logger.info("检测到多模态内容，使用多模态API")
                response = await self._call_multimodal_api(request, formatted_messages)
            else:
                logger.info("纯文本请求，使用通用文本API")
                response = await self._call_text_api(request, formatted_messages)

            # 统一处理响应
            if response.status_code != 200:
                error_msg = f"DashScope API错误: {response.code} - {response.message}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # 提取消息内容
            message = response.output.choices[0].message
            content = message.content

            # 处理多模态响应中的列表格式内容
            if isinstance(content, list):
                # 提取第一个文本内容
                for item in content:
                    if "text" in item:
                        content = item["text"]
                        break

            # 提取token使用情况
            token_usage = TokenUsage(
                input_tokens=response.usage.input_tokens if response.usage else 0,
                output_tokens=response.usage.output_tokens if response.usage else 0
            )

            return LLMResponse(
                id=request.id,
                content=content,
                provider=request.provider,
                model=request.model,
                usage=token_usage,
                finish_reason=response.output.choices[0].finish_reason
            )

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"DashScope completions调用失败: {str(e)}")
            raise

    @staticmethod
    async def _call_text_api(
        request: CompletionsRequest,
        messages: list[Message]
    ) -> GenerationResponse:
        """
        调用DashScope纯文本API

        Returns:
            GenerationResponse: DashScope响应对象
        """
        try:
            return await AioGeneration.call(
                model=request.model,
                messages=messages,
                result_format='message',
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=request.stream
            )

        except Exception as e:
            logger.error(f"DashScope文本API调用失败: {str(e)}", exc_info=True)
            raise

    @staticmethod
    async def _call_multimodal_api(
        request: CompletionsRequest,
        messages: list[Message]
    ) -> MultiModalConversationResponse:
        """
        调用DashScope多模态API

        Returns:
            MultiModalConversationResponse: DashScope响应对象
        """
        try:
            return await AioMultiModalConversation.call(
                model=request.model,
                messages=messages,
                result_format='message',
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=request.stream
            )

        except Exception as e:
            logger.error(f"DashScope多模态API调用失败: {str(e)}", exc_info=True)
            raise

    @staticmethod
    async def transcribe_audio(
        audio_url: str,
        language_hints: Optional[list[str]] = None
    ) -> str:
        """
        使用Paraformer进行语音转文字

        Args:
            audio_url: 音频文件的公网可访问URL
            language_hints: 语言提示，默认支持'zh', 'en'

        Returns:
            转录后的文本内容

        Raises:
            ASRTranscriptionException: 转录失败
            ASRDownloadException: 下载转录结果失败
        """
        if not language_hints:
            language_hints = ['zh', 'en']

        logger.info(f"[ASR] 开始转录音频: {audio_url}")

        try:
            # 提交ASR任务（异步调用）
            logger.debug(f"[ASR] 提交转录任务")
            task_response = Transcription.async_call(
                model='paraformer-v2',
                file_urls=[audio_url],
                language_hints=language_hints
            )

            task_id = task_response.output.task_id
            logger.debug(f"[ASR] 任务已提交 - task_id: {task_id}")

            # 在异步上下文中运行同步的wait方法
            result_response = Transcription.wait(task=task_id)

            # 检查任务状态
            if result_response.status_code != 200:
                error_msg = f"ASR任务失败: \n ID: {task_id}\n 错误信息: {result_response.code} - {result_response.message}"
                logger.error(f"[ASR] {error_msg}")
                raise ASRTranscriptionException(error_msg)

            # 获取转录结果URL
            transcription_url = result_response.output.results[0]['transcription_url']

            # 下载并解析转录结果
            async with aiohttp.ClientSession() as session:
                async with session.get(transcription_url) as response:
                    if response.status != 200:
                        raise ASRDownloadException()
                    json_content = await response.json()

            transcripts = json_content.get('transcripts', [])
            if not transcripts:
                raise ASRTranscriptionException("无效的转录结果")

            # 拼接所有转录文本
            transcription_output = []
            for t in transcripts:
                sentence = t.get("text", "").strip()
                if sentence:
                    transcription_output.append(sentence)

            all_text = " ".join(transcription_output)

            logger.info(f"[ASR] 转录完成")
            return all_text

        except BaseHTTPException:
            raise
        except Exception as e:
            logger.error(f"[ASR] 转录过程中发生异常: {e}", exc_info=True)
            raise ASRTranscriptionException(f"未知异常: {str(e)}")
