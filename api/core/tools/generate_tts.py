"""
音频生成工具模块

提供TTS音频生成功能，使用MiniMax API将文本转换为语音。

主要功能:
- generate_audio: 根据文本和助理配置生成TTS音频
"""

from uuid import UUID

from config import mas_config
from core.entities import WorkflowExecutionModel
from libs.types import OutputContent, OutputType
from services import AssistantService, AudioService
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
        # 获取API密钥
        api_key = AudioService.verify_minimax_key()

        # 获取voice_id
        assistant_model = await AssistantService.get_assistant_by_id(assistant_id)
        voice_id = assistant_model.voice_id if assistant_model.voice_id else mas_config.MINIMAX_VOICE_ID

        logger.info(f"[TTS] 最终使用voice_id: {voice_id}")

        # 调用AudioService的activate_voice方法生成TTS
        audio_url, audio_length = await AudioService.generate_audio(
            api_key=api_key,
            voice_id=voice_id,
            activation_text=result.output
        )

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
