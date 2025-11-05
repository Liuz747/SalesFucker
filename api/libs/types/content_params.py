from enum import StrEnum
from typing import Sequence, TypeAlias

from pydantic import BaseModel, Field, field_validator


class InputType(StrEnum):
    """输入类型枚举"""
    TEXT = "text"
    AUDIO = "input_audio"
    IMAGE = "input_image"
    VIDEO = "input_video"
    FILES = "input_files"


class InputContent(BaseModel):
    """通用输入内容模型（支持文本和多模态URL）"""

    type: InputType = Field(description="内容类型")
    content: str = Field(description="文本内容或URL（根据type字段）")

    @field_validator('content')
    @classmethod
    def validate_url_if_not_text(cls, v: str, info) -> str:
        """验证非文本类型必须是有效URL"""
        content_type = info.data.get('type')
        if content_type and content_type != InputType.TEXT:
            if not v.startswith(('http://', 'https://')):
                raise ValueError(f"无效的URL格式: {v}")
        return v


InputContentParams: TypeAlias = str | Sequence[InputContent]