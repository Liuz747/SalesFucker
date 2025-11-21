import aiohttp
import asyncio
from typing import Optional
from urllib.parse import urlparse

from dashscope.audio.asr import Transcription

from config import mas_config
from libs.types.content_params import (
    InputContent,
    InputContentParams,
    InputType
)
from schemas.exceptions import (
    ASRConfigurationException,
    ASRUrlValidationException,
    ASRTranscriptionException,
    ASRTimeoutException,
    ASRDownloadException
)
from utils import get_component_logger


logger = get_component_logger(__name__, "AudioService")


class AudioService:
    """
    Integrated Audio Service

    Provides:
    - STT: speech-to-text (audio URL → transcript)
    - input normalization for controller
    """

    @classmethod
    def _verify_api_key(cls):
        """验证API密钥"""
        api_key = mas_config.DASHSCOPE_API_KEY
        if not api_key:
            raise ASRConfigurationException()

    @classmethod
    async def transcribe_async(
        cls,
        audio_url: str,
        thread_id: str,
        language_hints: Optional[list[str]] = None
    ) -> str:
        """
        使用Paraformer进行语音转文字

        Args:
            audio_url: 音频文件的公网可访问URL
            thread_id: 线程ID，用于日志记录
            language_hints: 语言提示，默认支持'zh', 'en'

        Returns:
            转录后的文本内容
        """
        if language_hints is None:
            language_hints = ['zh', 'en']

        # 验证API密钥
        cls._verify_api_key()

        logger.info(f"[ASR] 开始转录")

        try:
            # 验证URL格式
            parsed_url = urlparse(audio_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ASRUrlValidationException(audio_url)

            # 提交ASR任务（异步调用）
            logger.debug(f"[ASR] 提交转录任务")
            task_response = Transcription.async_call(
                model='paraformer-v2',
                file_urls=[audio_url],
                language_hints=language_hints
            )

            task_id = task_response.output.task_id
            logger.debug(f"[ASR] 任务已提交 - task_id: {task_id}")

            # 轮询等待结果
            max_wait_time = 300
            poll_interval = 2
            elapsed_time = 0

            while elapsed_time < max_wait_time:
                await asyncio.sleep(poll_interval)
                elapsed_time += poll_interval

                # 查询任务状态
                result_response = Transcription.fetch(task=task_id)

                if result_response.status_code != 200:
                    logger.error(f"[ASR] 查询任务状态失败: {result_response.status_code}")
                    continue

                task_status = result_response.output.task_status
                logger.debug(f"[ASR] 任务状态: {task_status} - 已等待: {elapsed_time}秒")

                if task_status == 'SUCCEEDED':
                    # 任务完成，获取转录结果
                    transcription_url = result_response.output.results[0]['transcription_url']
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(transcription_url) as response:
                                if response.status != 200:
                                    raise ASRDownloadException(response.status)
                                json_content = await response.json()

                        transcripts = json_content.get('transcripts', [])
                        if not transcripts:
                            raise ASRTranscriptionException("无效的转录结果")

                        all_text = " ".join(
                            t.get("text", "").strip()
                            for t in transcripts
                            if t.get("text")
                        ).strip()

                        logger.info(f"[ASR] 转录完成 - thread={thread_id}, 耗时: {elapsed_time}秒")
                        return all_text
                    except Exception as e:
                        logger.error(f"[ASR] 获取转录结果失败: {e}", exc_info=True)
                        raise ASRTranscriptionException(f"下载或解析失败: {str(e)}")

                elif task_status == 'FAILED':
                    raise ASRTranscriptionException(f"任务ID: {task_id}")

            # 超时处理
            raise ASRTimeoutException(task_id, elapsed_time)
        except Exception as e:
            logger.error(f"[ASR] 转录过程中发生异常 - thread={thread_id}: {e}", exc_info=True)
            raise ASRTranscriptionException(f"未知异常: {str(e)}")

    @classmethod
    async def normalize_input(
        cls,
        raw_input: InputContentParams,
        thread_id: str
    ) -> InputContentParams:
        """
        标准化输入内容，为音频添加转录文本

        对于音频类型的输入，会调用ASR服务进行转录，然后将转录文本作为新的文本内容
        添加到输入列表中，同时保留原始音频内容以供后续处理使用。

        Args:
            raw_input: 原始输入内容参数（字符串或内容列表）
            thread_id: 线程标识符

        Returns:
            标准化后的输入内容，包含原始项目和音频转录文本
        """
        if isinstance(raw_input, str):
            return raw_input

        normalized = raw_input.copy()

        for item in raw_input:
            if item.type == InputType.AUDIO:
                transcript = await cls.transcribe_async(
                    audio_url=item.content,
                    thread_id=thread_id
                )
                normalized.append(
                    InputContent(type=InputType.TEXT, content=transcript)
                )

        return normalized

