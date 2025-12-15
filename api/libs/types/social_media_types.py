from enum import IntEnum, StrEnum


class SocialPlatform(StrEnum):
    """支持的社交媒体平台枚举"""

    REDNOTE = "rednote"
    DOUYING = "douyin"


class SocialMediaActionType(IntEnum):
    """动作类型枚举"""

    FOLLOW = 1
    LIKE = 2
    COMMENT = 3
    SHARE = 4
    FAVORITE = 5
    PROFILE = 6


class MethodType(StrEnum):
    COMMENT = "comment"
    REPLIES = "replies"
    KEYWORDS = "keywords"
    PRIVATE_MESSAGE = "private_message"
    MOMENTS = "moments"
    COMPRESS = "compress"
    EXPAND = "expand"


class TextBeautifyActionType(IntEnum):
    """文本美化动作类型"""
    COMPRESS = 1  # 缩写
    EXPAND = 2    # 扩写
