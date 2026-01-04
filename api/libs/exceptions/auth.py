"""
认证与授权相关异常

包含身份验证、令牌管理、权限控制等相关的异常定义。
"""

from .base import BaseHTTPException


class AuthenticationException(BaseHTTPException):
    """认证异常基类"""
    code = 40000
    message = "AUTHENTICATION_ERROR"
    http_status_code = 401


class AppKeyNotConfiguredException(AuthenticationException):
    """App Key未配置异常"""
    code = 40001
    message = "APP_AUTH_NOT_CONFIGURED"
    http_status_code = 500

    def __init__(self):
        super().__init__(detail="App-Key 未配置")


class InvalidAppKeyException(AuthenticationException):
    """无效App Key异常"""
    code = 40002
    message = "INVALID_APP_KEY"

    def __init__(self):
        super().__init__(detail="无效或缺失 App-Key")


class TokenGenerationException(AuthenticationException):
    """令牌生成失败异常"""
    code = 40003
    message = "TOKEN_GENERATION_FAILED"
    http_status_code = 500

    def __init__(self, reason: str):
        super().__init__(detail=f"JWT token 生成失败: {reason}")


class AuthorizationException(BaseHTTPException):
    """授权异常基类"""
    code = 40004
    message = "AUTHORIZATION_ERROR"
    http_status_code = 403


class InsufficientScopeException(AuthorizationException):
    """权限不足异常"""
    code = 40005
    message = "INSUFFICIENT_SCOPE"
    http_status_code = 403

    def __init__(self, required_scope: str):
        super().__init__(detail=f"权限不足，需要 {required_scope} 权限")