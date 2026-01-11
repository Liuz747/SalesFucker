import asyncio
from typing import Optional
from urllib.parse import urlparse

import aiohttp
from dashscope.audio.asr import Transcription

from config import mas_config
from libs.types import (
    InputContent,
    InputType,
    Message,
    MessageParams,
)
from libs.exceptions import (
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

    @staticmethod
    def verify_api_key():
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
        cls.verify_api_key()

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
            poll_interval = 1
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
                                    raise ASRDownloadException()
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
        raw_input: MessageParams,
        thread_id: str
    ) -> tuple[MessageParams, list[dict]]:
        """
        标准化输入消息列表，为音频添加转录文本

        对于消息列表中每个消息的音频类型内容，会调用ASR服务进行转录，
        然后将转录文本添加到该消息的内容列表中。

        Args:
            raw_input: 消息列表
            thread_id: 线程标识符

        Returns:
            tuple[MessageParams, list[dict]]: 标准化后的消息列表和ASR结果
        """
        normalized: list[Message] = []
        asr_result: list[dict] = []

        for index, message in enumerate(raw_input):
            # 如果内容是字符串，直接保留
            if isinstance(message.content, str):
                normalized.append(message)
                continue

            # 如果是 Sequence[InputContent]，处理音频
            normalized_content: list[InputContent] = []
            for item in message.content:
                if item.type != InputType.AUDIO:
                    normalized_content.append(item)
                    continue

                # Audio → STT
                transcript = await cls.transcribe_async(
                    audio_url=item.content,
                    thread_id=thread_id
                )

                asr_result.append({
                    "index": index,
                    "content": transcript
                })

                # 保留原始音频内容并添加转录文本
                normalized_content.extend([
                    item,
                    InputContent(type=InputType.TEXT, content=transcript)
                ])

            # 创建新的消息对象，保留原始角色
            message.content = normalized_content
            normalized.append(message)

        return normalized, asr_result

    @classmethod
    async def clone_and_activate_voice(
        cls,
        voice_file: str,
        voice_id: str,
        demo_text: Optional[str] = None
    ) -> dict:
        """
        克隆并激活声音

        从音频文件克隆声音，并立即激活以防止7天后过期。

        参数:
            voice_file_path: 源音频文件路径（mp3/m4a/wav，10秒-5分钟，最大20MB）
            voice_id: 自定义声音ID（8-256字符，必须以字母开头）
            demo_text: 可选的演示文本，用于预览克隆效果

        返回:
            dict: 包含voice_id和克隆结果的字典
        """
        try:
            # 验证API密钥
            api_key = mas_config.MINIMAX_API_KEY
            if not api_key:
                raise ValueError("MiniMax API密钥未配置")

            # 验证voice_id格式
            if not voice_id or len(voice_id) < 8 or len(voice_id) > 256:
                raise ValueError("voice_id长度必须在8-256字符之间")
            if not voice_id[0].isalpha():
                raise ValueError("voice_id必须以字母开头")
            if voice_id.endswith('-') or voice_id.endswith('_'):
                raise ValueError("voice_id不能以-或_结尾")

            logger.info(f"开始克隆声音: voice_id={voice_id}")

            # 步骤1: 上传源音频文件
            file_id = await cls._upload_audio_file(
                api_key=api_key,
                file_path=voice_file
            )
            logger.info(f"源音频上传成功: file_id={file_id}")

            # 步骤3: 调用克隆API
            clone_result = await cls._clone_voice(
                api_key=api_key,
                file_id=file_id,
                voice_id=voice_id,
                demo_text=demo_text
            )
            logger.info(f"声音克隆成功: voice_id={voice_id}")

            # 步骤4: 激活克隆的声音（防止7天后过期）
            activation_text = demo_text or "你好，我是你的AI助理。"
            await cls.activate_voice(
                api_key=api_key,
                voice_id=voice_id,
                activation_text=activation_text
            )
            logger.info(f"声音已激活，不会过期: voice_id={voice_id}")

            return {
                "voice_id": voice_id,
                "file_id": file_id,
                "clone_result": clone_result,
                "activated": True
            }

        except Exception as e:
            logger.error(f"克隆并激活声音失败: {e}", exc_info=True)
            raise

    @staticmethod
    async def _upload_audio_file(api_key: str, file_path: str) -> str:
        """
        上传音频文件到MiniMax

        参数:
            api_key: MiniMax API密钥
            file_path: 音频文件路径

        返回:
            str: 上传后的file_id
        """
        upload_url = "https://api.minimax.io/v1/files/upload"
        headers = {"Authorization": f"Bearer {api_key}"}

        async with aiohttp.ClientSession() as session:
            with open(file_path, "rb") as f:
                form_data = aiohttp.FormData()
                form_data.add_field("purpose", "voice_clone")
                form_data.add_field("file", f)

                async with session.post(
                    upload_url,
                    headers=headers,
                    data=form_data,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"上传音频失败: {response.status} - {error_text}")

                    response_data = await response.json()
                    file_id = response_data.get("file", {}).get("file_id")
                    if not file_id:
                        raise Exception("上传音频失败: 未返回file_id")

                    return file_id

    @staticmethod
    async def _clone_voice(
        api_key: str,
        file_id: str,
        voice_id: str,
        demo_text: Optional[str] = None
    ) -> dict:
        """
        调用MiniMax克隆API

        参数:
            api_key: MiniMax API密钥
            file_id: 源音频文件ID
            voice_id: 自定义声音ID
            demo_text: 演示文本

        返回:
            dict: 克隆结果

        异常:
            Exception: 克隆失败
        """
        clone_url = "https://api.minimax.io/v1/voice_clone"
        clone_payload = {
            "file_id": file_id,
            "voice_id": voice_id,
            "model": "speech-2.6-hd"
        }

        # 添加可选参数
        if demo_text:
            clone_payload["text"] = demo_text

        clone_headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                clone_url,
                headers=clone_headers,
                json=clone_payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"克隆声音失败: {response.status} - {error_text}")

                return await response.json()

    @staticmethod
    async def activate_voice(
        api_key: str,
        voice_id: str,
        activation_text: str
    ):
        """
        激活克隆的声音

        通过T2A API合成一次音频来激活克隆的声音，防止7天后过期。

        参数:
            api_key: MiniMax API密钥
            voice_id: 要激活的声音ID
            activation_text: 用于激活的文本内容

        异常:
            Exception: 激活失败
        """
        try:
            url = "https://api.minimaxi.com/v1/t2a_v2"

            payload = {
                "model": "speech-2.6-hd",
                "text": activation_text,
                "stream": False,
                "voice_setting": {
                    "voice_id": voice_id,
                    "speed": 1,
                    "vol": 1,
                    "pitch": 0
                },
                "audio_setting": {
                    "sample_rate": 32000,
                    "bitrate": 128000,
                    "format": "mp3",
                    "channel": 1
                },
                "language_boost": "auto",
                "output_format": "url"
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"MiniMax TTS API错误: {response.status} - {error_text}")

                    # MiniMax返回音频的链接
                    response_data = await response.json()
                    audio_url = response_data.get("data", {}).get("audio", "")
                    audio_length = response_data.get("extra_info", {}).get("audio_length", 0)

            if audio_url:
                audio_url = audio_url.replace("\\u0026", "&")

            # TODO: make this more smart instead of throwing an error. Add a retry mechanism
            if audio_length is not None and audio_length / 1000 >= 60:
                raise ValueError(f"MiniMax TTS audio exceeds 60 seconds: {audio_length}")

            return audio_url, audio_length

        except Exception as e:
            logger.error(f"激活声音失败: {e}", exc_info=True)
            raise
