"""
音频生成工具模块

提供TTS音频生成功能，使用MiniMax API将文本转换为语音。

主要功能:
- generate_audio: 根据文本和助理配置生成TTS音频
"""

from config import mas_config
from libs.types import OutputContent, OutputType
from models import WorkflowExecutionModel
from services import AssistantService, AudioService
from utils import get_component_logger

logger = get_component_logger(__name__)


async def generate_audio_output(result: WorkflowExecutionModel):
    """
    生成TTS音频输出

    使用MiniMax TTS API将文本转换为语音，并将生成的音频URL
    添加到result.multimodal_outputs中。

    参数:
        result: 工作流执行结果，包含需要转换的文本(result.output)
    """
    try:
        # 获取API密钥
        api_key = AudioService.verify_minimax_key()

        # 获取voice_id
        voice_id = mas_config.MINIMAX_VOICE_ID
        try:
            assistant_model = await AssistantService.get_assistant_by_id(result.assistant_id)
            if assistant_model.voice_id:
                voice_id = assistant_model.voice_id
                logger.info(f"[TTS] 使用助手配置的voice_id: {voice_id}")
        except Exception as e:
            logger.warning(f"[TTS] 获取助手voice_id失败，使用默认值: {e}")

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
