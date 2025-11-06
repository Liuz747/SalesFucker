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
    IDLE = "IDLE"
    ACTIVE = "ACTIVE"
    PROCESSING = "PROCESSING"
    FAILED = "FAILED"
    PAUSED = "PAUSED"
    DELETED = "DELETED"
