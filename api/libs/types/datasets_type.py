from enum import StrEnum


class DocumentStatus(StrEnum):
    """文档状态枚举"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    INDEXED = "INDEXED"
    FAILED = "FAILED"


class DocumentType(StrEnum):
    """文档类型枚举"""
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    FILE = "FILE"
    OTHER = "OTHER"
