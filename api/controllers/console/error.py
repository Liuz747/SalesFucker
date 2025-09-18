from controllers.exceptions import BaseHTTPException


class AuthenticationException(BaseHTTPException):
    error_code = 40001
    error_message = "AUTHENTICATION_ERROR"
    http_status_code = 401


class AppKeyNotConfiguredException(AuthenticationException):
    error_code = 50001
    error_message = "APP_AUTH_NOT_CONFIGURED"
    http_status_code = 500
    
    def __init__(self):
        super().__init__(detail="App-Key 未配置")


class InvalidAppKeyException(AuthenticationException):
    error_code = 40101
    error_message = "INVALID_APP_KEY"
    
    def __init__(self):
        super().__init__(detail="无效或缺失 App-Key")


class TokenGenerationException(AuthenticationException):
    error_code = 50002
    error_message = "TOKEN_GENERATION_FAILED"
    http_status_code = 500
    
    def __init__(self, reason: str):
        super().__init__(detail=f"JWT token 生成失败: {reason}")


class AuthorizationException(BaseHTTPException):
    error_code = 40300
    error_message = "AUTHORIZATION_ERROR"
    http_status_code = 403


class InsufficientScopeException(AuthorizationException):
    error_code = 40301
    error_message = "INSUFFICIENT_SCOPE"
    
    def __init__(self, required_scope: str):
        super().__init__(detail=f"权限不足，需要 {required_scope} 权限")


class TenantManagementException(BaseHTTPException):
    error_code = 40001
    error_message = "TENANT_MANAGEMENT_ERROR"
    http_status_code = 400


class TenantIdMismatchException(TenantManagementException):
    error_code = 40002
    error_message = "TENANT_ID_MISMATCH"
    
    def __init__(self, url_tenant_id: str, body_tenant_id: str):
        super().__init__(detail=f"租户ID不匹配: URL中为 {url_tenant_id}, 请求体中为 {body_tenant_id}")


class TenantNotFoundException(TenantManagementException):
    error_code = 40401
    error_message = "TENANT_NOT_FOUND"
    http_status_code = 404
    
    def __init__(self, tenant_id: str):
        super().__init__(detail=f"租户 {tenant_id} 不存在")


class TenantSyncException(TenantManagementException):
    error_code = 40003
    error_message = "TENANT_SYNC_FAILED"
    http_status_code = 400
    
    def __init__(self, tenant_id: str, reason: str = ""):
        detail = f"租户 {tenant_id} 同步失败"
        if reason:
            detail += f": {reason}"
        super().__init__(detail=detail)


class TenantValidationException(TenantManagementException):
    error_code = 40003
    error_message = "TENANT_VALIDATION_ERROR"

    def __init__(self, tenant_id: str, reason: str):
        super().__init__(detail=f"租户 {tenant_id} 验证失败: {reason}")


class TenantAlreadyExistsException(TenantManagementException):
    error_code = 40009
    error_message = "TENANT_ALREADY_EXISTS"
    http_status_code = 409

    def __init__(self, tenant_id: str):
        super().__init__(detail=f"租户 {tenant_id} 已存在")


class DatabaseConnectionException(BaseHTTPException):
    error_code = 50301
    error_message = "DATABASE_CONNECTION_ERROR"
    http_status_code = 503
    
    def __init__(self, operation: str = ""):
        detail = "数据库连接不可用"
        if operation:
            detail += f" (操作: {operation})"
        super().__init__(detail=detail)