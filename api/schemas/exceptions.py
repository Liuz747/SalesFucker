from collections.abc import Mapping
from uuid import UUID

from starlette.exceptions import HTTPException


class BaseHTTPException(HTTPException):
    """
    HTTP异常基类

    继承Starlette的HTTPException，提供标准化的HTTP错误响应格式。
    所有需要返回HTTP错误响应的异常都应该继承此类。

    属性:
        error_code: 业务错误代码，子类应该重写此属性
        error_message: 错误描述，子类应该重写此属性
        data: 结构化的错误响应数据

    用法示例:
        class AgentNotFound(BaseHTTPException):
            error_code = 10011
            error_message = "AGENT_NOT_FOUND"
            status_code = 404

            def __init__(self, agent_id: str):
                super().__init__(detail=f"智能体 {agent_id} 不存在")
    """

    # 20000 代表 internal server error
    error_code: int = 200
    error_message: str = "SUCCESS"
    http_status_code: int = 500
    data: dict | None = None

    def __init__(self, detail: str | None = None, headers: Mapping[str, str] | None = None):
        super().__init__(self.http_status_code, detail, headers)

        self.data = {
            "code": self.error_code,
            "error": self.error_message,
            "message": self.detail
        }


class WorkspaceException(BaseHTTPException):
    error_code = "WORKSPACE_ERROR"
    http_status_code = 400


class TenantManagementException(BaseHTTPException):
    error_code = 100000
    error_message = "TENANT_MANAGEMENT_ERROR"
    http_status_code = 500


class TenantNotFoundException(TenantManagementException):
    error_code = 1000002
    error_message = "TENANT_NOT_FOUND"
    http_status_code = 404

    def __init__(self, tenant_id: str):
        super().__init__(detail=f"租户 {tenant_id} 不存在")


class TenantSyncException(TenantManagementException):
    error_code = 1000003
    error_message = "TENANT_SYNC_FAILED"
    http_status_code = 400

    def __init__(self, tenant_id: str, reason: str = ""):
        detail = f"租户 {tenant_id} 同步失败"
        if reason:
            detail += f": {reason}"
        super().__init__(detail=detail)


class TenantValidationException(BaseHTTPException):
    error_code = 1000005
    error_message = "TENANT_VALIDATION_ERROR"
    http_status_code = 403

    def __init__(self, tenant_id: str, reason: str):
        super().__init__(detail=f"租户 {tenant_id} 验证失败: {reason}")


class TenantIdRequiredException(TenantValidationException):
    error_code = 1000006
    detail = "TENANT_ID_REQUIRED"
    http_status_code = 400

    def __init__(self):
        super().__init__(detail="请求必须包含租户ID，请在请求头中添加 X-Tenant-ID")


class TenantNotFoundException(TenantValidationException):
    error_code = 1000007
    detail = "TENANT_NOT_FOUND"

    def __init__(self, tenant_id: str):
        super().__init__(detail=f"租户 {tenant_id} 不存在")


class TenantDisabledException(TenantValidationException):
    error_code = 1000008
    detail = "TENANT_DISABLED"

    def __init__(self, tenant_id: str):
        super().__init__(detail=f"租户 {tenant_id} 已被禁用")


class TenantAccessDeniedException(TenantValidationException):
    error_code = 1000009
    detail = "TENANT_ACCESS_DENIED"

    def __init__(self, tenant_id: str, resource: str):
        super().__init__(detail=f"租户 {tenant_id} 无权访问 {resource}")


class TenantAlreadyExistsException(TenantManagementException):
    error_code = 1000001
    error_message = "TENANT_ALREADY_EXISTS"
    http_status_code = 409

    def __init__(self, tenant_id: str):
        super().__init__(detail=f"租户 {tenant_id} 已存在")


class AssistantException(WorkspaceException):
    error_code = 1100000
    detail = "ASSISTANT_ERROR"


class AssistantNotFoundException(AssistantException):
    error_code = 1100001
    detail = "ASSISTANT_NOT_FOUND"
    status_code = 404

    def __init__(self, assistant_id: str):
        super().__init__(detail=f"AI助手 {assistant_id} 不存在")


class AssistantUnavailableException(AssistantException):
    error_code = 1100002
    detail = "ASSISTANT_UNAVAILABLE"
    status_code = 503

    def __init__(self, assistant_id: str):
        super().__init__(detail=f"AI助手 {assistant_id} 暂时不可用")


class AssistantConflictException(AssistantException):
    error_code = 1100003
    detail = "Assistant_Conflict"
    status_code = 503

    def __init__(self, assistant_id: str):
        super().__init__(detail=f"AI助手 {assistant_id} 已存在")


class ThreadException(WorkspaceException):
    error_code = 1300001
    detail = "THREAD_ERROR"


class ThreadNotFoundException(ThreadException):
    error_code = 1300002
    detail = "THREAD_NOT_FOUND"
    http_status_code = 404

    def __init__(self, thread_id: UUID | str):
        super().__init__(detail=f"线程 {thread_id} 不存在")


class ThreadCreationException(ThreadException):
    error_code = 1300003
    detail = "THREAD_CREATION_FAILED"
    http_status_code = 500

    def __init__(self, reason: str = ""):
        detail = "线程创建失败"
        if reason:
            detail += f": {reason}"
        super().__init__(detail=detail)


class ThreadAccessDeniedException(ThreadException):
    error_code = 1300004
    detail = "THREAD_ACCESS_DENIED"
    http_status_code = 403

    def __init__(self, thread_id: UUID | str, tenant_id: str):
        super().__init__(detail=f"租户 {tenant_id} 无权访问线程 {thread_id}")


class ConversationException(WorkspaceException):
    error_code = 1400001
    detail = "CONVERSATION_ERROR"


class ConversationProcessingException(ConversationException):
    error_code = 1400002
    detail = "CONVERSATION_PROCESSING_FAILED"
    http_status_code = 500

    def __init__(self, reason: str = ""):
        detail = "对话处理失败"
        if reason:
            detail += f": {reason}"
        super().__init__(detail=detail)


class MessageValidationException(ConversationException):
    error_code = 1400003
    detail = "MESSAGE_VALIDATION_ERROR"

    def __init__(self, message: str):
        super().__init__(detail=f"消息验证失败: {message}")


class WorkflowException(WorkspaceException):
    error_code = 1400004
    detail = "WORKFLOW_ERROR"
    http_status_code = 500


class WorkflowExecutionException(WorkflowException):
    error_code = 1400005
    detail = "WORKFLOW_EXECUTION_FAILED"

    def __init__(self, workflow_type: str, reason: str = ""):
        detail = f"{workflow_type} 工作流执行失败"
        if reason:
            detail += f": {reason}"
        super().__init__(detail=detail)


class AssistantException(WorkspaceException):
    error_code = "ASSISTANT_ERROR"


class AssistantNotFoundException(AssistantException):
    error_code = "ASSISTANT_NOT_FOUND"
    http_status_code = 404

    def __init__(self, assistant_id: str):
        super().__init__(detail=f"AI助手 {assistant_id} 不存在")


class AssistantUnavailableException(AssistantException):
    error_code = "ASSISTANT_UNAVAILABLE"
    http_status_code = 503

    def __init__(self, assistant_id: str):
        super().__init__(detail=f"AI助手 {assistant_id} 暂时不可用")


class AuthenticationException(BaseHTTPException):
    error_code = 40000
    error_message = "AUTHENTICATION_ERROR"
    http_status_code = 401


class AppKeyNotConfiguredException(AuthenticationException):
    error_code = 40001
    error_message = "APP_AUTH_NOT_CONFIGURED"
    http_status_code = 500

    def __init__(self):
        super().__init__(detail="App-Key 未配置")


class InvalidAppKeyException(AuthenticationException):
    error_code = 40002
    error_message = "INVALID_APP_KEY"

    def __init__(self):
        super().__init__(detail="无效或缺失 App-Key")


class TokenGenerationException(AuthenticationException):
    error_code = 40003
    error_message = "TOKEN_GENERATION_FAILED"
    http_status_code = 500

    def __init__(self, reason: str):
        super().__init__(detail=f"JWT token 生成失败: {reason}")


class AuthorizationException(BaseHTTPException):
    error_code = 40004
    error_message = "AUTHORIZATION_ERROR"
    http_status_code = 403


class InsufficientScopeException(AuthorizationException):
    error_code = 40005
    error_message = "INSUFFICIENT_SCOPE"
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
