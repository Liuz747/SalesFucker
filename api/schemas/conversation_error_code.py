from uuid import UUID
from controllers.exceptions import BaseHTTPException


class WorkspaceException(BaseHTTPException):
    error_code = "WORKSPACE_ERROR"
    status_code = 400


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


class TenantValidationException:
    error_code = 1000005
    detail = "TENANT_VALIDATION_ERROR"
    status_code = 403


class TenantIdRequiredException(TenantValidationException):
    error_code = 1000006
    detail = "TENANT_ID_REQUIRED"
    status_code = 400

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


class ThreadException(WorkspaceException):
    error_code = 1300001
    detail = "THREAD_ERROR"


class ThreadNotFoundException(ThreadException):
    error_code = 1300002
    detail = "THREAD_NOT_FOUND"
    status_code = 404

    def __init__(self, thread_id: UUID | str):
        super().__init__(detail=f"线程 {thread_id} 不存在")


class ThreadCreationException(ThreadException):
    error_code = 1300003
    detail = "THREAD_CREATION_FAILED"
    status_code = 500

    def __init__(self, reason: str = ""):
        detail = "线程创建失败"
        if reason:
            detail += f": {reason}"
        super().__init__(detail=detail)


class ThreadAccessDeniedException(ThreadException):
    error_code = 1300004
    detail = "THREAD_ACCESS_DENIED"
    status_code = 403

    def __init__(self, thread_id: UUID | str, tenant_id: str):
        super().__init__(detail=f"租户 {tenant_id} 无权访问线程 {thread_id}")


class ConversationException(WorkspaceException):
    error_code = 1400001
    detail = "CONVERSATION_ERROR"


class ConversationProcessingException(ConversationException):
    error_code = 1400002
    detail = "CONVERSATION_PROCESSING_FAILED"
    status_code = 500

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
    status_code = 500


class WorkflowExecutionException(WorkflowException):
    error_code = 1400005
    detail = "WORKFLOW_EXECUTION_FAILED"

    def __init__(self, workflow_type: str, reason: str = ""):
        detail = f"{workflow_type} 工作流执行失败"
        if reason:
            detail += f": {reason}"
        super().__init__(detail=detail)
