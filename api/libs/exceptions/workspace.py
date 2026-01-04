"""
工作空间相关异常

包含助手、线程、对话、工作流等工作空间资源的异常定义。
"""

from uuid import UUID

from .base import BaseHTTPException


class WorkspaceException(BaseHTTPException):
    code = 200000
    message = "WORKSPACE_ERROR"
    http_status_code = 400


# ============================================
# 助手相关异常
# ============================================

class AssistantException(WorkspaceException):
    """助手异常基类"""
    code = 1100000
    message = "ASSISTANT_ERROR"


class AssistantNotFoundException(AssistantException):
    """助手不存在异常"""
    code = 1100001
    message = "ASSISTANT_NOT_FOUND"
    http_status_code = 404

    def __init__(self, assistant_id: str):
        super().__init__(detail=f"AI助手 {assistant_id} 不存在")


class AssistantUnavailableException(AssistantException):
    """助手不可用异常"""
    code = 1100002
    message = "ASSISTANT_UNAVAILABLE"
    http_status_code = 503

    def __init__(self, assistant_id: str):
        super().__init__(detail=f"AI助手 {assistant_id} 暂时不可用")


class AssistantConflictException(AssistantException):
    """助手冲突异常"""
    code = 1100003
    message = "ASSISTANT_CONFLICT"
    http_status_code = 503

    def __init__(self, assistant_id: str):
        super().__init__(detail=f"AI助手 {assistant_id} 已存在")


class AssistantDisabledException(AssistantException):
    """助手已禁用异常"""
    code = 1100004
    message = "ASSISTANT_DISABLED"
    http_status_code = 400

    def __init__(self, assistant_id: UUID | str):
        super().__init__(detail=f"AI助手 {assistant_id} 已被禁用，无法处理请求")


class AssistantInactiveException(AssistantException):
    """助手未激活异常"""
    code = 1100005
    message = "ASSISTANT_INACTIVE"
    http_status_code = 403

    def __init__(self, assistant_id: UUID, status: str):
        super().__init__(detail=f"AI数字员工 {assistant_id} 未激活（当前状态: {status}），无法使用")


# ============================================
# 线程相关异常
# ============================================

class ThreadException(WorkspaceException):
    """线程异常基类"""
    code = 1300001
    message = "THREAD_ERROR"


class ThreadNotFoundException(ThreadException):
    """线程不存在异常"""
    code = 1300002
    message = "THREAD_NOT_FOUND"
    http_status_code = 404

    def __init__(self, thread_id: UUID | str):
        super().__init__(detail=f"线程 {thread_id} 不存在")


class ThreadCreationException(ThreadException):
    """线程创建失败异常"""
    code = 1300003
    message = "THREAD_CREATION_FAILED"
    http_status_code = 500

    def __init__(self, reason: str = ""):
        detail = "线程创建失败"
        if reason:
            detail += f": {reason}"
        super().__init__(detail=detail)


class ThreadAccessDeniedException(ThreadException):
    """线程访问拒绝异常"""
    code = 1300004
    message = "THREAD_ACCESS_DENIED"
    http_status_code = 403

    def __init__(self, thread_id: UUID | str, tenant_id: str):
        super().__init__(detail=f"租户 {tenant_id} 无权访问线程 {thread_id}")


# ============================================
# 对话相关异常
# ============================================

class ConversationException(WorkspaceException):
    """对话异常基类"""
    code = 1400001
    message = "CONVERSATION_ERROR"


class ConversationProcessingException(ConversationException):
    """对话处理失败异常"""
    code = 1400002
    message = "CONVERSATION_PROCESSING_FAILED"
    http_status_code = 500

    def __init__(self, reason: str = ""):
        detail = "对话处理失败"
        if reason:
            detail += f": {reason}"
        super().__init__(detail=detail)


class MessageValidationException(ConversationException):
    """消息验证失败异常"""
    code = 1400003
    message = "MESSAGE_VALIDATION_ERROR"

    def __init__(self, message: str):
        super().__init__(detail=f"消息验证失败: {message}")


# ============================================
# 工作流相关异常
# ============================================

class WorkflowException(WorkspaceException):
    """工作流异常基类"""
    code = 1400004
    message = "WORKFLOW_ERROR"
    http_status_code = 500


class WorkflowExecutionException(WorkflowException):
    """工作流执行失败异常"""
    code = 1400005
    message = "WORKFLOW_EXECUTION_FAILED"

    def __init__(self, workflow_type: str, reason: str = ""):
        detail = f"{workflow_type} 工作流执行失败"
        if reason:
            detail += f": {reason}"
        super().__init__(detail=detail)