"""
默认提示词配置模块

该模块提供不同输入类型的默认提示词配置。
当用户仅提供附件而没有文本内容时，系统将使用这些默认提示词。

核心功能:
- 不同输入类型的默认提示词
- 特定场景的提示词模板
- 智能提示词选择逻辑
- 可配置的提示词管理
"""

from typing import Optional

from models.enums import InputType


class DefaultPrompts:
    """
    默认提示词配置类

    为不同的输入类型提供默认的处理提示词。
    支持自定义提示词和场景特定提示词。
    """

    # 不同输入类型的默认提示词
    PROMPTS: dict[str, str] = {
        InputType.IMAGE: """请分析这张图片，包括：
1. 描述图片中的主要内容和对象
2. 识别图片的类型和用途
3. 提供相关的建议和信息""",

        InputType.VOICE: "请处理这段音频内容，转录语音并理解用户的意图。",

        InputType.MULTIMODAL: """
                            请综合分析提供的多模态内容（图片和音频）：
                            1. 分析图片中的视觉信息
                            2. 处理音频中的语音内容
                            3. 综合两者提供完整的分析和建议
                            """,
    }

    # 特定场景的提示词（用于业务定制）
    GENERAL_IMAGE_ANALYSIS = """请对这张图片进行通用分析：
1. 描述图片的主要内容
2. 识别关键对象和元素
3. 分析图片的风格和特点
4. 提供相关的见解和建议"""

    VOICE_TRANSCRIPTION_PROMPT = "请转录这段音频的内容，并理解用户的意图和需求。"

    VOICE_EMOTION_ANALYSIS = """请分析这段音频：
1. 转录语音内容
2. 识别说话者的情绪状态
3. 理解用户的意图和需求
4. 提供合适的回应建议"""

    @classmethod
    def get_prompt(
        cls,
        input_type: str,
        custom_prompt: Optional[str] = None,
        scenario: Optional[str] = None
    ) -> str:
        """
        获取提示词

        优先级：自定义提示 > 场景提示 > 默认提示

        Args:
            input_type: 输入类型（text/image/voice/multimodal）
            custom_prompt: 用户自定义提示词
            scenario: 特定场景标识（skin_analysis/product_recognition等）

        Returns:
            str: 最终使用的提示词
        """
        # 1. 优先使用自定义提示
        if custom_prompt:
            return custom_prompt

        # 2. 使用场景特定提示
        if scenario:
            scenario_prompt = cls._get_scenario_prompt(scenario)
            if scenario_prompt:
                return scenario_prompt

        # 3. 使用默认提示
        return cls.PROMPTS.get(input_type, "")

    @classmethod
    def _get_scenario_prompt(cls, scenario: str) -> Optional[str]:
        """
        获取场景特定提示词

        Args:
            scenario: 场景标识

        Returns:
            Optional[str]: 场景提示词，如果不存在则返回None
        """
        scenario_map = {
            'skin_analysis': cls.SKIN_ANALYSIS_PROMPT,
            'product_recognition': cls.PRODUCT_RECOGNITION_PROMPT,
            'general_image': cls.GENERAL_IMAGE_ANALYSIS,
            'voice_transcription': cls.VOICE_TRANSCRIPTION_PROMPT,
            'emotion_analysis': cls.VOICE_EMOTION_ANALYSIS
        }

        return scenario_map.get(scenario)

    @classmethod
    def list_available_scenarios(cls) -> dict[str, str]:
        """
        列出所有可用的场景及其描述

        Returns:
            Dict[str, str]: 场景标识到描述的映射
        """
        return {
            'skin_analysis': '皮肤分析 - 识别肤质、检测问题、提供护肤建议',
            'product_recognition': '产品识别 - 识别化妆品品牌、类型和用途',
            'general_image': '通用图像分析 - 描述图片内容和特点',
            'voice_transcription': '语音转录 - 转录音频内容',
            'emotion_analysis': '情绪分析 - 分析语音情绪和意图'
        }

    @classmethod
    def get_prompt_for_attachment_type(
        cls,
        attachment_type: str,
        custom_prompt: Optional[str] = None
    ) -> str:
        """
        根据附件类型获取合适的提示词

        Args:
            attachment_type: 附件类型（image/audio/file）
            custom_prompt: 自定义提示词

        Returns:
            str: 提示词
        """
        if custom_prompt:
            return custom_prompt

        type_to_input_type = {
            'image': InputType.IMAGE,
            'audio': InputType.VOICE,
            'file': InputType.TEXT
        }

        input_type = type_to_input_type.get(attachment_type, InputType.TEXT)
        return cls.PROMPTS.get(input_type, "")
