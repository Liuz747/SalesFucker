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
