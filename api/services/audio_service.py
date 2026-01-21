from typing import Optional

import aiohttp

from config import mas_config
from infra.runtimes.client import LLMClient
from libs.exceptions import AudioConfigurationException
from libs.types import (
    InputContent,
    InputType,
    Message,
    MessageParams,
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
    def verify_minimax_key() -> str:
        """MiniMax API密钥"""
        minimax_api_key = mas_config.MINIMAX_API_KEY
        if not minimax_api_key:
            raise AudioConfigurationException(audio_service="MiniMax")
        return minimax_api_key

    @staticmethod
    async def normalize_input(raw_input: MessageParams, thread_id: str) -> tuple[MessageParams, list[dict]]:
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
        llm_client = LLMClient()

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
                logger.info(f"[ASR] 开始转录 - thread={thread_id}")
                transcript = await llm_client.transcribe_audio(
                    provider='bailian',
                    model='paraformer-v2',
                    audio_url=item.content
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
            api_key = cls.verify_minimax_key()

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
            await cls.generate_audio(
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
    async def generate_audio(
        api_key: str,
        voice_id: str,
        activation_text: str
    ) -> tuple[str, float]:
        """
        激活克隆的声音

        通过T2A API合成一次音频来激活克隆的声音，防止7天后过期。

        参数:
            api_key: MiniMax API密钥
            voice_id: 要激活的声音ID
            activation_text: 用于激活的文本内容

        返回:
            tuple[str, float]: 音频链接和音频长度
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
            logger.error(f"[TTS] 生成音频失败: {e}", exc_info=True)
            raise
