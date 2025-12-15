from collections.abc import Mapping
from uuid import UUID

from starlette.exceptions import HTTPException


class BaseHTTPException(HTTPException):
    """
    HTTP异常基类

    继承Starlette的HTTPException，提供标准化的HTTP错误响应格式。
    所有需要返回HTTP错误响应的异常都应该继承此类。

    属性:
        code: 业务错误代码，子类应该重写此属性
        message: 错误描述，子类应该重写此属性
        data: 结构化的错误响应数据

    用法示例:
        class AgentNotFound(BaseHTTPException):
            code = 10011
            message = "AGENT_NOT_FOUND"
            status_code = 404

            def __init__(self, agent_id: str):
                super().__init__(detail=f"智能体 {agent_id} 不存在")
    """

    code: int = 200
    message: str = "SUCCESS"
    http_status_code: int = 500
    data: dict | None = None

    def __init__(self, detail: str | None = None, headers: Mapping[str, str] | None = None):
        super().__init__(self.http_status_code, detail, headers)

        self.data = {
            "code": self.code,
            "message": self.message,
            "detail": self.detail
        }


class WorkspaceException(BaseHTTPException):
    code = 200000
    message = "WORKSPACE_ERROR"
    http_status_code = 400


class TenantManagementException(BaseHTTPException):
    code = 100000
    message = "TENANT_MANAGEMENT_ERROR"
    http_status_code = 500


class TenantNotFoundException(TenantManagementException):
    code = 1000002
    message = "TENANT_NOT_FOUND"
    http_status_code = 404

    def __init__(self, tenant_id: str):
        super().__init__(detail=f"租户 {tenant_id} 不存在")


class TenantSyncException(TenantManagementException):
    code = 1000003
    message = "TENANT_SYNC_FAILED"
    http_status_code = 400

    def __init__(self, tenant_id: str, reason: str = ""):
        detail = f"租户 {tenant_id} 同步失败"
        if reason:
            detail += f": {reason}"
        super().__init__(detail=detail)


class TenantValidationException(BaseHTTPException):
    code = 1000005
    message = "TENANT_VALIDATION_ERROR"
    http_status_code = 403

    def __init__(self, tenant_id: str, reason: str):
        super().__init__(detail=f"租户 {tenant_id} 验证失败: {reason}")


class TenantIdRequiredException(BaseHTTPException):
    code = 1000006
    message = "TENANT_ID_REQUIRED"
    http_status_code = 400

    def __init__(self):
        super().__init__(detail="请求必须包含租户ID，请在请求头中添加 X-Tenant-ID")


class TenantDisabledException(TenantValidationException):
    code = 1000008
    message = "TENANT_DISABLED"

    def __init__(self, tenant_id: str):
        super().__init__(tenant_id=tenant_id, reason="租户已被禁用")


class TenantAccessDeniedException(TenantValidationException):
    code = 1000009
    message = "TENANT_ACCESS_DENIED"

    def __init__(self, tenant_id: str, resource: str):
        super().__init__(tenant_id=tenant_id, reason=f"无权访问 {resource}")


class TenantAlreadyExistsException(TenantManagementException):
    code = 1000001
    message = "TENANT_ALREADY_EXISTS"
    http_status_code = 409

    def __init__(self, tenant_id: str):
        super().__init__(detail=f"租户 {tenant_id} 已存在")


class AssistantException(WorkspaceException):
    code = 1100000
    message = "ASSISTANT_ERROR"


class AssistantNotFoundException(AssistantException):
    code = 1100001
    message = "ASSISTANT_NOT_FOUND"
    http_status_code = 404

    def __init__(self, assistant_id: str):
        super().__init__(detail=f"AI助手 {assistant_id} 不存在")


class AssistantUnavailableException(AssistantException):
    code = 1100002
    message = "ASSISTANT_UNAVAILABLE"
    http_status_code = 503

    def __init__(self, assistant_id: str):
        super().__init__(detail=f"AI助手 {assistant_id} 暂时不可用")


class AssistantConflictException(AssistantException):
    code = 1100003
    message = "ASSISTANT_CONFLICT"
    http_status_code = 503

    def __init__(self, assistant_id: str):
        super().__init__(detail=f"AI助手 {assistant_id} 已存在")


class AssistantDisabledException(AssistantException):
    code = 1100004
    message = "ASSISTANT_DISABLED"
    http_status_code = 400

    def __init__(self, assistant_id: UUID | str):
        super().__init__(detail=f"AI助手 {assistant_id} 已被禁用，无法处理请求")


class ThreadException(WorkspaceException):
    code = 1300001
    message = "THREAD_ERROR"


class ThreadNotFoundException(ThreadException):
    code = 1300002
    message = "THREAD_NOT_FOUND"
    http_status_code = 404

    def __init__(self, thread_id: UUID | str):
        super().__init__(detail=f"线程 {thread_id} 不存在")


class ThreadCreationException(ThreadException):
    code = 1300003
    message = "THREAD_CREATION_FAILED"
    http_status_code = 500

    def __init__(self, reason: str = ""):
        detail = "线程创建失败"
        if reason:
            detail += f": {reason}"
        super().__init__(detail=detail)


class ThreadAccessDeniedException(ThreadException):
    code = 1300004
    message = "THREAD_ACCESS_DENIED"
    http_status_code = 403

    def __init__(self, thread_id: UUID | str, tenant_id: str):
        super().__init__(detail=f"租户 {tenant_id} 无权访问线程 {thread_id}")


class ConversationException(WorkspaceException):
    code = 1400001
    message = "CONVERSATION_ERROR"


class ConversationProcessingException(ConversationException):
    code = 1400002
    message = "CONVERSATION_PROCESSING_FAILED"
    http_status_code = 500

    def __init__(self, reason: str = ""):
        detail = "对话处理失败"
        if reason:
            detail += f": {reason}"
        super().__init__(detail=detail)


class MessageValidationException(ConversationException):
    code = 1400003
    message = "MESSAGE_VALIDATION_ERROR"

    def __init__(self, message: str):
        super().__init__(detail=f"消息验证失败: {message}")


class WorkflowException(WorkspaceException):
    code = 1400004
    message = "WORKFLOW_ERROR"
    http_status_code = 500


class WorkflowExecutionException(WorkflowException):
    code = 1400005
    message = "WORKFLOW_EXECUTION_FAILED"

    def __init__(self, workflow_type: str, reason: str = ""):
        detail = f"{workflow_type} 工作流执行失败"
        if reason:
            detail += f": {reason}"
        super().__init__(detail=detail)


class AuthenticationException(BaseHTTPException):
    code = 40000
    message = "AUTHENTICATION_ERROR"
    http_status_code = 401


class AppKeyNotConfiguredException(AuthenticationException):
    code = 40001
    message = "APP_AUTH_NOT_CONFIGURED"
    http_status_code = 500

    def __init__(self):
        super().__init__(detail="App-Key 未配置")


class InvalidAppKeyException(AuthenticationException):
    code = 40002
    message = "INVALID_APP_KEY"

    def __init__(self):
        super().__init__(detail="无效或缺失 App-Key")


class TokenGenerationException(AuthenticationException):
    code = 40003
    message = "TOKEN_GENERATION_FAILED"
    http_status_code = 500

    def __init__(self, reason: str):
        super().__init__(detail=f"JWT token 生成失败: {reason}")


class AuthorizationException(BaseHTTPException):
    code = 40004
    message = "AUTHORIZATION_ERROR"
    http_status_code = 403


class InsufficientScopeException(AuthorizationException):
    code = 40005
    message = "INSUFFICIENT_SCOPE"
    http_status_code = 403

    def __init__(self, required_scope: str):
        super().__init__(detail=f"权限不足，需要 {required_scope} 权限")


class DatabaseConnectionException(BaseHTTPException):
    code = 100001
    message = "DATABASE_CONNECTION_ERROR"
    http_status_code = 503

    def __init__(self, operation: str = ""):
        detail = "数据库连接不可用"
        if operation:
            detail += f" (操作: {operation})"
        super().__init__(detail=detail)


class AudioServiceException(BaseHTTPException):
    code = 1500000
    message = "AUDIO_SERVICE_ERROR"
    http_status_code = 500


class ASRConfigurationException(AudioServiceException):
    code = 1500001
    message = "ASR_CONFIGURATION_ERROR"
    http_status_code = 500

    def __init__(self):
        super().__init__(detail="DASHSCOPE_API_KEY未配置，无法进行ASR转录")


class ASRUrlValidationException(AudioServiceException):
    code = 1500002
    message = "ASR_URL_VALIDATION_ERROR"
    http_status_code = 400

    def __init__(self, audio_url: str):
        super().__init__(detail=f"无效的音频URL格式: {audio_url}")


class ASRTaskSubmissionException(AudioServiceException):
    code = 1500003
    message = "ASR_TASK_SUBMISSION_FAILED"
    http_status_code = 500

    def __init__(self):
        super().__init__(detail="ASR任务提交失败")


class ASRTranscriptionException(AudioServiceException):
    code = 1500004
    message = "ASR_TRANSCRIPTION_FAILED"
    http_status_code = 500

    def __init__(self, reason: str = ""):
        detail = "ASR转录任务失败"
        if reason:
            detail += f": {reason}"
        super().__init__(detail=detail)


class ASRTimeoutException(AudioServiceException):
    code = 1500005
    message = "ASR_TIMEOUT"
    http_status_code = 408

    def __init__(self, task_id: str, elapsed_time: int):
        super().__init__(detail=f"ASR转录任务超时 - task_id: {task_id}, 已等待: {elapsed_time}秒")


class ASRDownloadException(AudioServiceException):
    code = 1500006
    message = "ASR_DOWNLOAD_FAILED"
    http_status_code = 500

    def __init__(self):
        super().__init__(detail="下载转录结果失败")
