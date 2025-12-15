from enum import StrEnum


class AccountStatus(StrEnum):
    """租户状态枚举"""
    ACTIVE = "ACTIVE"          # 活跃
    BANNED = "BANNED"          # 禁用
    CLOSED = "CLOSED"          # 关闭