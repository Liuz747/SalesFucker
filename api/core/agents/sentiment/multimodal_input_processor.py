"""
多模态输入处理器 - 简化版本

直接使用LLM的多模态能力处理不同类型的输入，
将复杂的预处理逻辑简化为直接的LLM调用。

核心功能:
- 支持 Sequence[InputContent] 多模态输入
- 直接利用LLM原生多模态能力
- 将多模态内容转换为纯文字
- 提供简洁的处理结果
"""

from typing import Dict, Any, Union, List, Tuple, Sequence
from libs.types import InputContentParams, InputContent, InputType
from utils import LoggerMixin


class MultimodalInputProcessor(LoggerMixin):
    """
    简化的多模态输入处理器

    直接使用LLM的多模态能力，避免复杂的预处理管道。
    """

    def __init__(self, tenant_id: str = None, config: Dict[str, Any] = None):
        super().__init__()
        self.tenant_id = tenant_id
        self.config = config or {}
        self.logger.info(f"简化多模态处理器初始化完成 - 租户: {tenant_id}")

    async def process_input(self, customer_input: InputContentParams) -> Tuple[str, Dict[str, Any]]:
        """
        处理多模态输入

        参数:
            customer_input: 客户输入 (str | Sequence[InputContent])

        返回:
            Tuple[str, Dict[str, Any]]: (处理后的纯文字, 多模态上下文)
        """
        # 简单字符串直接返回
        if isinstance(customer_input, str):
            return customer_input, {
                "type": "text",
                "modalities": ["text"],
                "item_count": 1
            }

        # 处理 Sequence[InputContent]
        if not customer_input:
            return "", {
                "type": "empty",
                "modalities": [],
                "item_count": 0
            }

        return await self._extract_text_from_multimodal(customer_input)

    async def _extract_text_from_multimodal(self, input_sequence: Sequence[InputContent]) -> Tuple[str, Dict[str, Any]]:
        """
        从多模态输入序列中提取文字

        使用LLM直接理解多模态内容并转换为文字描述
        """
        try:
            # 构建用于LLM处理的消息
            llm_messages = []
            modalities = set()

            for item in input_sequence:
                if isinstance(item, dict):
                    content_type = item.get("type", InputType.TEXT)
                    content = item.get("content", "")
                else:
                    # 如果是InputContent对象
                    content_type = getattr(item, "type", InputType.TEXT)
                    content = getattr(item, "content", "")

                modalities.add(content_type)

                if content_type == InputType.TEXT:
                    llm_messages.append({"type": "text", "text": content})
                elif content_type == InputType.IMAGE:
                    llm_messages.append({
                        "type": "image_url",
                        "image_url": {"url": content}
                    })
                elif content_type == InputType.AUDIO:
                    # 对于音频，我们先提供占位符，后续可以集成Whisper
                    llm_messages.append({
                        "type": "text",
                        "text": f"[音频内容: {content}]"
                    })
                else:
                    # 其他类型转为文本描述
                    llm_messages.append({
                        "type": "text",
                        "text": f"[{content_type}类型内容: {content}]"
                    })

            # 如果包含多模态内容，使用LLM提取文字
            if len(modalities) > 1 or InputType.IMAGE in modalities:
                extracted_text = await self._llm_extract_text(llm_messages)
            else:
                # 如果只是纯文本，直接拼接
                extracted_text = " ".join(
                    msg["text"] for msg in llm_messages
                    if msg["type"] == "text"
                )

            context = {
                "type": "multimodal",
                "modalities": list(modalities),
                "item_count": len(input_sequence),
                "processing_method": "llm_extraction"
            }

            return extracted_text or "无有效内容", context

        except Exception as e:
            self.logger.error(f"多模态处理失败: {e}")
            # 降级处理：尝试提取所有文本内容
            fallback_text = self._extract_fallback_text(input_sequence)
            return fallback_text, {
                "type": "fallback",
                "modalities": ["text"],
                "item_count": len(input_sequence),
                "error": str(e)
            }

    async def _llm_extract_text(self, messages: List[Dict[str, Any]]) -> str:
        """
        使用LLM提取多模态内容的文字描述

        这里应该调用LLM来理解多模态内容并生成文字
        暂时返回简化的结果，后续可以集成实际的LLM调用
        """
        # TODO: 这里应该调用实际的LLM接口
        # 例如：result = await self.invoke_llm(messages, "请将这些多模态内容转换为文字描述")

        # 暂时的简化处理
        text_parts = []
        for msg in messages:
            if msg["type"] == "text":
                text_parts.append(msg["text"])
            elif msg["type"] == "image_url":
                text_parts.append(f"[图片内容: {msg['image_url']['url']}]")

        return " ".join(text_parts) if text_parts else "多模态内容待处理"

    def _extract_fallback_text(self, input_sequence: Sequence[InputContent]) -> str:
        """降级文本提取"""
        text_parts = []
        for item in input_sequence:
            if isinstance(item, dict):
                if item.get("type") == InputType.TEXT:
                    text_parts.append(item.get("content", ""))
            else:
                # InputContent对象
                if getattr(item, "type", None) == InputType.TEXT:
                    text_parts.append(getattr(item, "content", ""))

        return " ".join(filter(None, text_parts)) or "无文本内容"

    def get_supported_modalities(self) -> List[str]:
        """获取支持的模态类型"""
        return ["text", "image", "audio", "video", "files"]

    def update_config(self, new_config: Dict[str, Any]):
        """更新配置"""
        self.config.update(new_config)