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


class TenantManagementException(BaseHTTPException):
    error_code = 100000
    detail = "TENANT_MANAGEMENT_ERROR"
    http_status_code = 500


class TenantIdMismatchException(TenantManagementException):
    error_code = 1000001
    detail = "TENANT_ID_MISMATCH"
    def __init__(self, url_tenant_id: str, body_tenant_id: str):
        super().__init__(detail=f"租户ID不匹配: URL中为 {url_tenant_id}, 请求体中为 {body_tenant_id}")


class TenantNotFoundException(TenantManagementException):
    error_code = 1000002
    detail = "TENANT_NOT_FOUND"
    http_status_code = 404

    def __init__(self, tenant_id: str):
        super().__init__(detail=f"租户 {tenant_id} 不存在")


class TenantSyncException(TenantManagementException):
    error_code = 1000003
    detail = "TENANT_SYNC_FAILED"
    http_status_code = 500

    def __init__(self, tenant_id: str, reason: str = ""):
        detail = f"租户 {tenant_id} 同步失败"
        if reason:
            detail += f": {reason}"
        super().__init__(detail=detail)


class TenantValidationException(TenantManagementException):
    error_code = 1000004
    detail = "TENANT_VALIDATION_ERROR"
    def __init__(self, tenant_id: str, reason: str):
        super().__init__(detail=f"租户 {tenant_id} 验证失败: {reason}")


class DatabaseConnectionException(BaseHTTPException):
    error_code = 1000005
    detail = "DATABASE_CONNECTION_ERROR"
    http_status_code = 503

    def __init__(self, operation: str = ""):
        detail = "数据库连接不可用"
        if operation:
            detail += f" (操作: {operation})"
        super().__init__(detail=detail)
