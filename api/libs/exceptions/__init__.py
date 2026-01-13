"""
异常模块

提供MAS系统中所有自定义异常的统一导入接口。

异常按照业务域组织：
- base: 基础异常类
- auth: 认证与授权异常
- tenant: 租户管理异常
- workspace: 工作空间异常（助手、线程、对话、工作流）
- audio: 音频服务异常
- infrastructure: 基础设施异常

错误代码范围：
- 40000-49999: 认证与授权
- 100000-199999: 基础设施与租户管理
- 200000-299999: 工作空间资源
- 1500000-1599999: 音频服务

使用示例：
    from libs.exceptions import TenantNotFoundException, AssistantDisabledException

    # 或按域导入
    from libs.exceptions.tenant import TenantNotFoundException
    from libs.exceptions.workspace import AssistantDisabledException
"""

# 基础异常
from .base import BaseHTTPException

# 认证与授权异常
from .auth import (
    AuthenticationException,
    AppKeyNotConfiguredException,
    InvalidAppKeyException,
    TokenGenerationException,
    AuthorizationException,
    InsufficientScopeException,
)

# 租户管理异常
from .tenant import (
    TenantManagementException,
    TenantNotFoundException,
    TenantSyncException,
    TenantValidationException,
    TenantIdRequiredException,
    TenantDisabledException,
    TenantAccessDeniedException,
    TenantAlreadyExistsException,
)

# 工作空间异常
from .workspace import (
    WorkspaceException,
    # 助手相关
    AssistantException,
    AssistantNotFoundException,
    AssistantUnavailableException,
    AssistantConflictException,
    AssistantDisabledException,
    AssistantInactiveException,
    # 记忆插入相关
    MemoryException,
    MemoryInsertionException,
    MemoryInsertFailureException,
    MemoryNotFoundException,
    MemoryDeletionException,
    # 线程相关
    ThreadException,
    ThreadNotFoundException,
    ThreadCreationException,
    ThreadAccessDeniedException,
    ThreadBusyException,
    # 对话相关
    ConversationException,
    ConversationProcessingException,
    MessageValidationException,
    # 工作流相关
    WorkflowException,
    WorkflowExecutionException,
)

# 音频服务异常
from .audio import (
    AudioServiceException,
    AudioConfigurationException,
    ASRUrlValidationException,
    ASRTaskSubmissionException,
    ASRTranscriptionException,
    ASRTimeoutException,
    ASRDownloadException,
)

# 基础设施异常
from .infrastructure import (
    DatabaseConnectionException,
)

__all__ = [
    # 基础
    "BaseHTTPException",

    # 认证与授权
    "AuthenticationException",
    "AppKeyNotConfiguredException",
    "InvalidAppKeyException",
    "TokenGenerationException",
    "AuthorizationException",
    "InsufficientScopeException",

    # 租户管理
    "TenantManagementException",
    "TenantNotFoundException",
    "TenantSyncException",
    "TenantValidationException",
    "TenantIdRequiredException",
    "TenantDisabledException",
    "TenantAccessDeniedException",
    "TenantAlreadyExistsException",

    # 工作空间
    "WorkspaceException",
    "AssistantException",
    "AssistantNotFoundException",
    "AssistantUnavailableException",
    "AssistantConflictException",
    "AssistantDisabledException",
    "AssistantInactiveException",
    "ThreadException",
    "ThreadNotFoundException",
    "ThreadCreationException",
    "ThreadAccessDeniedException",
    "ThreadBusyException",
    "ConversationException",
    "ConversationProcessingException",
    "MessageValidationException",
    "WorkflowException",
    "WorkflowExecutionException",

    # 音频服务
    "AudioServiceException",
    "AudioConfigurationException",
    "ASRUrlValidationException",
    "ASRTaskSubmissionException",
    "ASRTranscriptionException",
    "ASRTimeoutException",
    "ASRDownloadException",

    # 基础设施
    "DatabaseConnectionException",

    # 记忆插入
    "MemoryException",
    "MemoryInsertionException",
    "MemoryInsertFailureException",
    "MemoryNotFoundException",
    "MemoryDeletionException",
]