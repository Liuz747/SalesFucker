from uuid import UUID
from controllers.exceptions import BaseHTTPException


class WorkspaceException(BaseHTTPException):
    error_code = "WORKSPACE_ERROR"
    http_status_code = 400


class TenantValidationException(WorkspaceException):
    error_code = "TENANT_VALIDATION_ERROR"
    http_status_code = 403


class TenantIdRequiredException(TenantValidationException):
    error_code = "TENANT_ID_REQUIRED"
    http_status_code = 400
    
    def __init__(self):
        super().__init__(detail="请求必须包含租户ID，请在请求头中添加 X-Tenant-ID")


class TenantNotFoundException(TenantValidationException):
    error_code = "TENANT_NOT_FOUND"
    
    def __init__(self, tenant_id: str):
        super().__init__(detail=f"租户 {tenant_id} 不存在")


class TenantDisabledException(TenantValidationException):
    error_code = "TENANT_DISABLED"
    
    def __init__(self, tenant_id: str):
        super().__init__(detail=f"租户 {tenant_id} 已被禁用")


class TenantAccessDeniedException(TenantValidationException):
    error_code = "TENANT_ACCESS_DENIED"
    
    def __init__(self, tenant_id: str, resource: str):
        super().__init__(detail=f"租户 {tenant_id} 无权访问 {resource}")


class ThreadException(WorkspaceException):
    error_code = "THREAD_ERROR"


class ThreadNotFoundException(ThreadException):
    error_code = "THREAD_NOT_FOUND"
    http_status_code = 404
    
    def __init__(self, thread_id: UUID | str):
        super().__init__(detail=f"线程 {thread_id} 不存在")


class ThreadCreationException(ThreadException):
    error_code = "THREAD_CREATION_FAILED"
    http_status_code = 500
    
    def __init__(self, reason: str = ""):
        detail = "线程创建失败"
        if reason:
            detail += f": {reason}"
        super().__init__(detail=detail)


class ThreadAccessDeniedException(ThreadException):
    error_code = "THREAD_ACCESS_DENIED"
    http_status_code = 403
    
    def __init__(self, thread_id: UUID | str, tenant_id: str):
        super().__init__(detail=f"租户 {tenant_id} 无权访问线程 {thread_id}")


class ConversationException(WorkspaceException):
    error_code = "CONVERSATION_ERROR"


class ConversationProcessingException(ConversationException):
    error_code = "CONVERSATION_PROCESSING_FAILED"
    http_status_code = 500
    
    def __init__(self, reason: str = ""):
        detail = "对话处理失败"
        if reason:
            detail += f": {reason}"
        super().__init__(detail=detail)


class MessageValidationException(ConversationException):
    error_code = "MESSAGE_VALIDATION_ERROR"
    
    def __init__(self, message: str):
        super().__init__(detail=f"消息验证失败: {message}")


class WorkflowException(WorkspaceException):
    error_code = "WORKFLOW_ERROR"
    http_status_code = 500


class WorkflowExecutionException(WorkflowException):
    error_code = "WORKFLOW_EXECUTION_FAILED"
    
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