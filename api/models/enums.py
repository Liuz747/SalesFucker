from enum import StrEnum


class TenantRole(StrEnum):
    """租户角色枚举"""
    ADMIN = "admin"          # 管理员
    OPERATOR = "operator"    # 操作员
    VIEWER = "viewer"        # 查看者
    EDITOR = "editor"        # 编辑者


class TenantStatus(StrEnum):
    """租户状态枚举"""
    ACTIVE = "ACTIVE"          # 活跃
    BANNED = "BANNED"          # 禁用
    CLOSED = "CLOSED"          # 关闭


class ThreadStatus(StrEnum):
    """对话状态枚举"""
    ACTIVE = "ACTIVE"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PAUSED = "PAUSED"
    DELETED = "DELETED"


class InputType(StrEnum):
    """输入类型枚举"""
    TEXT = "text"
    AUDIO = "input_audio"
    IMAGE = "input_image"
    VIDEO = "input_video"
    FILES = "input_files"
