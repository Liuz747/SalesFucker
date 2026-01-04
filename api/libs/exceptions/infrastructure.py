"""
基础设施相关异常

包含数据库、缓存、消息队列等基础设施服务的异常定义。
"""

from .base import BaseHTTPException


class DatabaseConnectionException(BaseHTTPException):
    """数据库连接异常"""
    code = 100001
    message = "DATABASE_CONNECTION_ERROR"
    http_status_code = 503

    def __init__(self, operation: str = ""):
        detail = "数据库连接不可用"
        if operation:
            detail += f" (操作: {operation})"
        super().__init__(detail=detail)