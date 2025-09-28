from controllers.exceptions import BaseHTTPException


class AuthenticationException(BaseHTTPException):
    error_code = 40000
    detail = "AUTHENTICATION_ERROR"
    http_status_code = 401


class AppKeyNotConfiguredException(AuthenticationException):
    error_code = 40001
    detail = "APP_AUTH_NOT_CONFIGURED"
    http_status_code = 500

    def __init__(self):
        super().__init__(detail="App-Key 未配置")


class InvalidAppKeyException(AuthenticationException):
    error_code = 40002
    detail = "INVALID_APP_KEY"

    def __init__(self):
        super().__init__(detail="无效或缺失 App-Key")


class TokenGenerationException(AuthenticationException):
    error_code = 40003
    detail = "TOKEN_GENERATION_FAILED"
    http_status_code = 500

    def __init__(self, reason: str):
        super().__init__(detail=f"JWT token 生成失败: {reason}")


class AuthorizationException(BaseHTTPException):
    error_code = 40004
    detail = "AUTHORIZATION_ERROR"
    http_status_code = 403


class InsufficientScopeException(AuthorizationException):
    error_code = 40005
    detail = "INSUFFICIENT_SCOPE"
    http_status_code = 403

    def __init__(self, required_scope: str):
        super().__init__(detail=f"权限不足，需要 {required_scope} 权限")


class DatabaseConnectionException(BaseHTTPException):
    error_code = 100001
    detail = "DATABASE_CONNECTION_ERROR"
    http_status_code = 503

    def __init__(self, operation: str = ""):
        detail = "数据库连接不可用"
        if operation:
            detail += f" (操作: {operation})"
        super().__init__(detail=detail)
