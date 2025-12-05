"""
音频生成工具模块

提供TTS音频生成功能，使用MiniMax API将文本转换为语音。

主要功能:
- generate_audio: 根据文本和助理配置生成TTS音频
"""

from uuid import UUID

import aiohttp

from config import mas_config
from core.entities import WorkflowExecutionModel
from libs.types import OutputContent, OutputType
from services.assistant_service import AssistantService
from utils import get_component_logger

logger = get_component_logger(__name__)


async def generate_audio_output(result: WorkflowExecutionModel, assistant_id: UUID) -> None:
    """
    生成TTS音频输出

    使用MiniMax TTS API将文本转换为语音，并将生成的音频URL
    添加到result.multimodal_outputs中。

    参数:
        result: 工作流执行结果，包含需要转换的文本(result.output)
        assistant_id: 助理ID，用于获取个性化voice_id配置

    异常:
        ValueError: MiniMax API密钥未配置时抛出
        Exception: API调用失败时抛出
    """
    try:
        # 调用MiniMax TTS API
        api_key = mas_config.MINIMAX_API_KEY
        if not api_key:
            raise ValueError("MiniMax API密钥未配置")

        # 获取voice_id
        voice_id = mas_config.MINIMAX_VOICE_ID
        try:
            assistant_model = await AssistantService.get_assistant_by_id(assistant_id)
            if assistant_model.voice_id:
                voice_id = assistant_model.voice_id
                logger.info(f"[TTS] 使用助手配置的voice_id: {voice_id}")
        except Exception as e:
            logger.warning(f"[TTS] 获取助手voice_id失败，使用默认值: {e}")

        logger.info(f"[TTS] 最终使用voice_id: {voice_id}")

        url = "https://api.minimaxi.com/v1/t2a_v2"

        payload = {
            "model": "speech-2.6-hd",
            "text": result.output,
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

        if audio_length is not None and audio_length / 1000 >= 60:
            raise ValueError(f"MiniMax TTS audio exceeds 60 seconds: {audio_length}")

        if audio_url:
            # 处理URL编码问题：将\u0026转换为&
            audio_url = audio_url.replace("\\u0026", "&")

            result.multimodal_outputs.append(
                OutputContent(
                    type=OutputType.AUDIO,
                    url=audio_url,
                    metadata={
                        "format": "mp3",
                        "provider": "minimax",
                        "audio_length": audio_length,
                    }
                )
            )
            logger.info("[TTS] 添加音频输出成功")

    except Exception as e:
        logger.error(f"[TTS] 生成音频失败: {e}", exc_info=True)
