from enum import StrEnum
from typing import Any, Optional, Sequence, TypeAlias

from pydantic import BaseModel, Field, field_validator


class InputType(StrEnum):
    """输入类型枚举"""
    TEXT = "text"
    AUDIO = "input_audio"
    IMAGE = "input_image"
    VIDEO = "input_video"
    FILES = "input_files"


class OutputType(StrEnum):
    """输出类型枚举"""
    TEXT = "text"
    AUDIO = "output_audio"
    IMAGE = "output_image"
    VIDEO = "output_video"
    FILE = "output_file"


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


class OutputContent(BaseModel):
    """通用输出内容模型（支持多模态输出）"""

    type: OutputType = Field(description="输出内容类型")
    url: str = Field(description="生成内容的URL")
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="内容元数据（格式、时长、尺寸、语言等）"
    )

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """验证URL格式"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError(f"无效的URL格式: {v}")
        return v


InputContentParams: TypeAlias = str | Sequence[InputContent]
OutputContentParams: TypeAlias = Sequence[OutputContent]