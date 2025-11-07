"""
多模态输入处理器

专门负责处理各种类型的输入数据，将其转换为统一的文本格式
并提供多模态分析结果。集成现有的VoiceAnalyzer、图像分析等系统。

核心功能:
- 多模态输入格式标准化
- 语音转文字处理
- 图像分析集成
- 文本内容聚合
- 多模态元数据管理
"""

from typing import Dict, Any, Union, List, Tuple
from abc import ABC, abstractmethod

from libs.types import InputContentParams, InputContent, InputType
from utils import LoggerMixin


class ModalityProcessor(ABC):
    """模态处理器基类"""

    @abstractmethod
    async def process(self, content: str) -> Dict[str, Any]:
        """处理特定模态的内容"""
        pass

    @abstractmethod
    def can_process(self, input_type: InputType) -> bool:
        """检查是否能处理该类型"""
        pass


class TextProcessor(ModalityProcessor):
    """文本处理器"""

    def can_process(self, input_type: InputType) -> bool:
        return input_type == InputType.TEXT

    async def process(self, content: str) -> Dict[str, Any]:
        return {
            "text": content,
            "confidence": 1.0,
            "metadata": {"type": "text"}
        }


class VoiceProcessor(ModalityProcessor):
    """语音处理器 - 集成现有的VoiceAnalyzer"""

    def __init__(self, tenant_id: str = None, openai_api_key: str = None):
        self.tenant_id = tenant_id
        self.openai_api_key = openai_api_key
        self._voice_analyzer = None

    def can_process(self, input_type: InputType) -> bool:
        return input_type == InputType.AUDIO

    async def process(self, content: str) -> Dict[str, Any]:
        try:
            # TODO: 集成现有的VoiceAnalyzer
            # if not self._voice_analyzer and self.openai_api_key:
            #     from core.multimodal.voice.voice_analyzer import VoiceAnalyzer
            #     self._voice_analyzer = VoiceAnalyzer(self.tenant_id, self.openai_api_key)

            # result = await self._voice_analyzer.analyze_voice(content)
            # return {
            #     "text": result.get("transcription", ""),
            #     "confidence": result.get("confidence", 0.0),
            #     "metadata": {
            #         "type": "voice",
            #         "language": result.get("language"),
            #         "duration": result.get("duration")
            #     }
            # }

            # 暂时返回占位符
            return {
                "text": "[语音内容：待集成VoiceAnalyzer]",
                "confidence": 0.8,
                "metadata": {
                    "type": "voice",
                    "source_url": content,
                    "integration_status": "pending"
                }
            }
        except Exception as e:
            return {
                "text": "",
                "confidence": 0.0,
                "metadata": {
                    "type": "voice",
                    "error": str(e),
                    "integration_status": "error"
                }
            }


class ImageProcessor(ModalityProcessor):
    """图像处理器 - 集成现有的GPT-4V"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self._image_analyzer = None

    def can_process(self, input_type: InputType) -> bool:
        return input_type == InputType.IMAGE

    async def process(self, content: str) -> Dict[str, Any]:
        try:
            # TODO: 集成现有的图像分析系统（GPT-4V）
            # if not self._image_analyzer and self.api_key:
            #     from core.multimodal.image.image_analyzer import ImageAnalyzer
            #     self._image_analyzer = ImageAnalyzer(self.api_key)

            # result = await self._image_analyzer.analyze_image(content)
            # return {
            #     "text": result.get("description", ""),
            #     "confidence": result.get("confidence", 0.0),
            #     "metadata": {
            #         "type": "image",
            #         "analysis": result.get("analysis"),
            #         "objects": result.get("objects"),
            #         "skin_analysis": result.get("skin_analysis")
            #     }
            # }

            # 暂时返回占位符
            return {
                "text": "[图像内容：待集成GPT-4V]",
                "confidence": 0.7,
                "metadata": {
                    "type": "image",
                    "source_url": content,
                    "integration_status": "pending",
                    "analysis_summary": "图像分析功能待集成"
                }
            }
        except Exception as e:
            return {
                "text": "",
                "confidence": 0.0,
                "metadata": {
                    "type": "image",
                    "error": str(e),
                    "integration_status": "error"
                }
            }


class MultimodalInputProcessor(LoggerMixin):
    """
    多模态输入处理器

    负责处理各种输入类型，将其转换为统一的文本格式，
    并保留多模态分析结果。
    """

    def __init__(self, tenant_id: str = None, config: Dict[str, Any] = None):
        super().__init__()
        self.tenant_id = tenant_id
        self.config = config or {}

        # 初始化各种模态处理器
        self.processors: List[ModalityProcessor] = [
            TextProcessor(),
            VoiceProcessor(tenant_id, self.config.get("openai_api_key")),
            ImageProcessor(self.config.get("openai_api_key"))
        ]

        self.logger.info(f"多模态输入处理器初始化完成 - 租户: {tenant_id}")

    async def process_input(self, customer_input: Union[str, List[InputContent]]) -> Tuple[str, Dict[str, Any]]:
        """
        处理多模态输入

        参数:
            customer_input: 客户输入（字符串或InputContent列表）

        返回:
            Tuple[str, Dict[str, Any]]: (处理后的纯文本, 多模态分析结果)
        """
        if isinstance(customer_input, str):
            return customer_input, {
                "type": "text",
                "modalities": ["text"],
                "analysis": {},
                "processing_stats": {
                    "total_items": 1,
                    "successful": 1,
                    "failed": 0
                }
            }

        if not isinstance(customer_input, list) or not customer_input:
            empty_text = str(customer_input) if customer_input else ""
            return empty_text, {"type": "unknown", "modalities": [], "analysis": {}}

        return await self._process_multimodal_list(customer_input)

    async def _process_multimodal_list(self, input_list: List[InputContent]) -> Tuple[str, Dict[str, Any]]:
        """处理多模态内容列表"""
        text_parts = []
        analysis_results = {}
        modalities = set()
        stats = {"total_items": len(input_list), "successful": 0, "failed": 0}

        for i, item in enumerate(input_list):
            try:
                processed_text, analysis = await self._process_single_item(item)

                if processed_text:
                    text_parts.append(processed_text)

                if analysis:
                    analysis_results[f"item_{i}"] = analysis
                    modalities.add(analysis["metadata"]["type"])

                stats["successful"] += 1

            except Exception as e:
                self.logger.error(f"处理第{i}项失败: {e}")
                stats["failed"] += 1

        final_text = " ".join(filter(None, text_parts))

        return final_text or "无有效文本内容", {
            "type": "multimodal",
            "modalities": list(modalities),
            "analysis": analysis_results,
            "processing_stats": stats
        }

    async def _process_single_item(self, item: Union[str, InputContent]) -> Tuple[str, Dict[str, Any]]:
        """处理单个输入项"""
        if isinstance(item, str):
            # 纯文本
            processor = self.processors[0]  # TextProcessor
            result = await processor.process(item)
            return result["text"], result

        if isinstance(item, dict):
            input_type = item.get("type", InputType.TEXT)
            content = item.get("content", "")

            # 找到合适的处理器
            processor = self._get_processor_for_type(input_type)
            if not processor:
                # 默认作为文本处理
                processor = self.processors[0]
                content = str(item)

            result = await processor.process(content)
            return result["text"], result

        # 默认转换为字符串处理
        processor = self.processors[0]
        result = await processor.process(str(item))
        return result["text"], result

    def _get_processor_for_type(self, input_type: InputType) -> Union[ModalityProcessor, None]:
        """根据输入类型获取处理器"""
        for processor in self.processors:
            if processor.can_process(input_type):
                return processor
        return None

    def get_supported_modalities(self) -> List[str]:
        """获取支持的模态类型列表"""
        return [type(processor).__name__ for processor in self.processors]

    def update_config(self, new_config: Dict[str, Any]):
        """更新配置"""
        self.config.update(new_config)

        # 重新初始化需要配置的处理器
        for i, processor in enumerate(self.processors):
            if isinstance(processor, VoiceProcessor):
                self.processors[i] = VoiceProcessor(
                    self.tenant_id,
                    self.config.get("openai_api_key")
                )
            elif isinstance(processor, ImageProcessor):
                self.processors[i] = ImageProcessor(
                    self.config.get("openai_api_key")
                )