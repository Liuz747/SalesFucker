"""
多模态数据处理工具类

统一处理多模态输入到字符串的转换逻辑，
整合了ChatAgent._input_to_text和MultimodalInputProcessor._extract_fallback_text的功能。

核心功能:
- 统一多模态输入到字符串转换
- 支持str和Sequence[InputContent]两种输入格式
- 提供内容类型提取功能
- 具备良好的容错性和降级处理
"""

from typing import Union, Sequence, List
from libs.types import InputContent, InputType


class MultimodalUtils:
    """多模态数据处理工具类"""

    @staticmethod
    def to_text(content: Union[str, Sequence[InputContent]]) -> str:
        """
        将多模态输入转换为字符串

        统一了ChatAgent._input_to_text和MultimodalInputProcessor._extract_fallback_text的逻辑

        参数:
            content: 输入内容，可以是字符串或InputContent序列

        返回:
            str: 转换后的字符串内容
        """
        # 处理字符串输入
        if isinstance(content, str):
            return content

        # 处理序列输入
        if isinstance(content, Sequence):
            if not content:
                return ""

            text_parts: List[str] = []

            for item in content:
                # 尝试提取文本内容
                extracted_text = MultimodalUtils._extract_text_from_item(item)
                if extracted_text:
                    text_parts.append(extracted_text)

            return "\n".join(text_parts) if text_parts else ""

        # 兜底处理：直接转换为字符串
        return str(content) if content is not None else ""

    @staticmethod
    def _extract_text_from_item(item) -> str:
        """
        从单个输入项中提取文本内容

        参数:
            item: 单个输入项，可能是dict或InputContent对象

        返回:
            str: 提取的文本内容
        """
        if isinstance(item, dict):
            # 处理字典格式的输入
            content_type = item.get("type", InputType.TEXT)
            content_value = item.get("content", "")

            if content_type == InputType.TEXT:
                return str(content_value) if content_value else ""
            else:
                # 非文本类型，生成描述性文本
                return f"[{content_type}内容: {content_value}]" if content_value else ""
        else:
            # 处理InputContent对象或其他类型
            try:
                # 使用getattr安全地获取属性
                content_type = getattr(item, "type", InputType.TEXT)
                content_value = getattr(item, "content", None)

                if content_type == InputType.TEXT:
                    return str(content_value) if content_value else ""
                elif content_value is not None:
                    return f"[{content_type}内容: {content_value}]"
                else:
                    # 如果没有content属性，直接转换为字符串
                    return str(item) if item is not None else ""
            except Exception:
                # 如果属性访问失败，直接转换为字符串
                return str(item) if item is not None else ""

    @staticmethod
    def extract_content_types(content: Union[str, Sequence[InputContent]]) -> List[str]:
        """
        提取输入内容的类型列表

        参数:
            content: 输入内容

        返回:
            List[str]: 内容类型列表
        """
        if isinstance(content, str):
            return [InputType.TEXT]

        if isinstance(content, Sequence):
            content_types = set()

            for item in content:
                if isinstance(item, dict):
                    content_type = item.get("type", InputType.TEXT)
                    content_types.add(content_type)
                else:
                    content_type = getattr(item, "type", InputType.TEXT)
                    content_types.add(content_type)

            return list(content_types)

        return [InputType.TEXT]  # 默认返回文本类型

    @staticmethod
    def has_multimodal_content(content: Union[str, Sequence[InputContent]]) -> bool:
        """
        检查输入是否包含多模态内容

        参数:
            content: 输入内容

        返回:
            bool: 是否包含多模态内容（非纯文本）
        """
        content_types = MultimodalUtils.extract_content_types(content)

        # 只有文本类型不算多模态
        if len(content_types) == 1 and InputType.TEXT in content_types:
            return False

        # 包含非文本类型或多种类型则为多模态
        return len(content_types) > 1 or InputType.TEXT not in content_types

    @staticmethod
    def get_content_summary(content: Union[str, Sequence[InputContent]]) -> dict:
        """
        获取内容摘要信息

        参数:
            content: 输入内容

        返回:
            dict: 包含类型、数量等信息的摘要
        """
        if isinstance(content, str):
            return {
                "input_type": "string",
                "content_types": [InputType.TEXT],
                "item_count": 1,
                "is_multimodal": False,
                "text_length": len(content)
            }

        if isinstance(content, Sequence):
            content_types = MultimodalUtils.extract_content_types(content)
            text_content = MultimodalUtils.to_text(content)

            return {
                "input_type": "sequence",
                "content_types": content_types,
                "item_count": len(content),
                "is_multimodal": MultimodalUtils.has_multimodal_content(content),
                "text_length": len(text_content)
            }

        return {
            "input_type": "other",
            "content_types": [InputType.TEXT],
            "item_count": 1,
            "is_multimodal": False,
            "text_length": len(str(content)) if content is not None else 0
        }