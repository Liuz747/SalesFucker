"""
模型包

包含MAS系统中使用的所有数据模型，采用简化的单文件结构。
每个文件包含相关业务的所有模型（Pydantic业务模型 + SQLAlchemy数据库模型）。

模型文件:
- tenant.py: 租户管理相关的所有模型（业务模型 + 数据库模型）
- conversation.py: 对话相关的所有模型（业务模型）
"""

from .enums import (
    InputType,
    ThreadStatus,
    TenantRole,
    TenantStatus
)
from .tenant import (
    TenantOrm,
    TenantModel
)
from .conversation import (
    ThreadOrm,
    Thread
)
from .workflow import (
    WorkflowOrm,
    WorkflowRun,
    WorkflowExecutionModel
)

__all__ = [
    # Enums
    "TenantRole",
    "TenantStatus",
    "ThreadStatus",
    "InputType",

    # Tenant
    "TenantOrm",
    "TenantModel",

    # Conversation
    "ThreadOrm",
    "Thread",

    # Workflow
    "WorkflowOrm",
    "WorkflowRun",
    "WorkflowExecutionModel"
]