"""
异常类单元测试

测试所有自定义异常类的:
- 错误码正确性
- HTTP状态码正确性
- 错误消息格式
- 异常详情内容
"""

import pytest
from uuid import uuid4

from libs.exceptions import (
    # 基础异常
    BaseHTTPException,
    # 租户相关
    TenantManagementException,
    TenantNotFoundException,
    TenantValidationException,
    TenantIdRequiredException,
    TenantDisabledException,
    TenantAlreadyExistsException,
    # 工作空间 - 助手相关
    WorkspaceException,
    AssistantException,
    AssistantNotFoundException,
    AssistantConflictException,
    AssistantInactiveException,
    AssistantCreationException,
    AssistantUpdateException,
    AssistantDeletionException,
    # 工作空间 - 线程相关
    ThreadException,
    ThreadNotFoundException,
    ThreadCreationException,
    ThreadAccessDeniedException,
    ThreadBusyException,
    ThreadUpdateException,
    # 工作空间 - 对话相关
    ConversationAnalysisException,
    # 工作空间 - 工作流相关
    WorkflowExecutionException,
    # 工作空间 - 营销相关
    MarketingPlanGenerationException,
    # 工作空间 - 记忆相关
    MemoryException,
    MemoryInsertFailureException,
    MemoryNotFoundException,
    MemoryDeletionException,
)
from libs.types import AccountStatus


class TestBaseExceptions:
    """测试基础异常类"""

    def test_base_http_exception_structure(self):
        """测试BaseHTTPException基础结构"""
        exc = BaseHTTPException(detail="测试错误")
        assert exc.detail == "测试错误"
        assert exc.code == 1000000
        assert exc.message == "INTERNAL_ERROR"
        assert exc.http_status_code == 500


class TestTenantExceptions:
    """测试租户相关异常"""

    def test_tenant_not_found_exception(self):
        """测试租户不存在异常"""
        tenant_id = "test_tenant_123"
        exc = TenantNotFoundException(tenant_id)

        assert exc.code == 1000001
        assert exc.message == "TENANT_NOT_FOUND"
        assert exc.http_status_code == 404
        assert tenant_id in exc.detail
        assert "不存在" in exc.detail

    def test_tenant_validation_exception(self):
        """测试租户验证失败异常"""
        tenant_id = "test_tenant_123"
        reason = "租户状态异常"
        exc = TenantValidationException(tenant_id, reason)

        assert exc.code == 1000002
        assert exc.message == "TENANT_VALIDATION_FAILED"
        assert exc.http_status_code == 403
        assert tenant_id in exc.detail
        assert reason in exc.detail

    def test_tenant_id_required_exception(self):
        """测试租户ID必需异常"""
        exc = TenantIdRequiredException()

        assert exc.code == 1000003
        assert exc.message == "TENANT_ID_REQUIRED"
        assert exc.http_status_code == 400
        assert "租户ID" in exc.detail

    def test_tenant_disabled_exception(self):
        """测试租户已禁用异常"""
        tenant_id = "test_tenant_123"
        exc = TenantDisabledException(tenant_id)

        assert exc.code == 1000004
        assert exc.message == "TENANT_DISABLED"
        assert exc.http_status_code == 403
        assert tenant_id in exc.detail
        assert "禁用" in exc.detail

    def test_tenant_already_exists_exception(self):
        """测试租户已存在异常"""
        tenant_id = "test_tenant_123"
        exc = TenantAlreadyExistsException(tenant_id)

        assert exc.code == 1000005
        assert exc.message == "TENANT_ALREADY_EXISTS"
        assert exc.http_status_code == 409
        assert tenant_id in exc.detail
        assert "已存在" in exc.detail


class TestAssistantExceptions:
    """测试助手相关异常"""

    def test_assistant_not_found_exception(self):
        """测试助手不存在异常"""
        assistant_id = uuid4()
        exc = AssistantNotFoundException(assistant_id)

        assert exc.code == 1100001
        assert exc.message == "ASSISTANT_NOT_FOUND"
        assert exc.http_status_code == 404
        assert str(assistant_id) in exc.detail
        assert "不存在" in exc.detail

    def test_assistant_conflict_exception(self):
        """测试助手冲突异常"""
        assistant_id = uuid4()
        exc = AssistantConflictException(assistant_id)

        assert exc.code == 1100003
        assert exc.message == "ASSISTANT_CONFLICT"
        assert exc.http_status_code == 409
        assert str(assistant_id) in exc.detail
        assert "已存在" in exc.detail

    def test_assistant_inactive_exception(self):
        """测试助手未激活异常"""
        assistant_id = uuid4()
        status = AccountStatus.INACTIVE
        exc = AssistantInactiveException(assistant_id, status)

        assert exc.code == 1100005
        assert exc.message == "ASSISTANT_INACTIVE"
        assert exc.http_status_code == 400
        assert str(assistant_id) in exc.detail
        assert status.value in exc.detail
        assert "未激活" in exc.detail

    def test_assistant_creation_exception_with_reason(self):
        """测试助手创建失败异常（带原因）"""
        reason = "数据库连接失败"
        exc = AssistantCreationException(reason)

        assert exc.code == 1100006
        assert exc.message == "ASSISTANT_CREATION_FAILED"
        assert exc.http_status_code == 500
        assert reason in exc.detail
        assert "创建失败" in exc.detail

    def test_assistant_creation_exception_without_reason(self):
        """测试助手创建失败异常（无原因）"""
        exc = AssistantCreationException()

        assert exc.code == 1100006
        assert exc.message == "ASSISTANT_CREATION_FAILED"
        assert exc.http_status_code == 500
        assert "创建失败" in exc.detail

    def test_assistant_update_exception(self):
        """测试助手更新失败异常"""
        assistant_id = uuid4()
        reason = "验证失败"
        exc = AssistantUpdateException(assistant_id, reason)

        assert exc.code == 1100007
        assert exc.message == "ASSISTANT_UPDATE_FAILED"
        assert exc.http_status_code == 500
        assert str(assistant_id) in exc.detail
        assert reason in exc.detail
        assert "更新失败" in exc.detail

    def test_assistant_deletion_exception(self):
        """测试助手删除失败异常"""
        assistant_id = uuid4()
        reason = "存在关联数据"
        exc = AssistantDeletionException(assistant_id, reason)

        assert exc.code == 1100008
        assert exc.message == "ASSISTANT_DELETION_FAILED"
        assert exc.http_status_code == 500
        assert str(assistant_id) in exc.detail
        assert reason in exc.detail
        assert "删除失败" in exc.detail


class TestThreadExceptions:
    """测试线程相关异常"""

    def test_thread_not_found_exception(self):
        """测试线程不存在异常"""
        thread_id = uuid4()
        exc = ThreadNotFoundException(thread_id)

        assert exc.code == 1300001
        assert exc.message == "THREAD_NOT_FOUND"
        assert exc.http_status_code == 404
        assert str(thread_id) in exc.detail
        assert "不存在" in exc.detail

    def test_thread_creation_exception_with_reason(self):
        """测试线程创建失败异常（带原因）"""
        reason = "租户配额已满"
        exc = ThreadCreationException(reason)

        assert exc.code == 1300002
        assert exc.message == "THREAD_CREATION_FAILED"
        assert exc.http_status_code == 500
        assert reason in exc.detail
        assert "创建失败" in exc.detail

    def test_thread_creation_exception_without_reason(self):
        """测试线程创建失败异常（无原因）"""
        exc = ThreadCreationException()

        assert exc.code == 1300002
        assert "创建失败" in exc.detail

    def test_thread_access_denied_exception(self):
        """测试线程访问拒绝异常"""
        tenant_id = "test_tenant_123"
        exc = ThreadAccessDeniedException(tenant_id)

        assert exc.code == 1300003
        assert exc.message == "THREAD_ACCESS_DENIED"
        assert exc.http_status_code == 403
        assert tenant_id in exc.detail
        assert "无权访问" in exc.detail

    def test_thread_busy_exception(self):
        """测试线程繁忙异常"""
        thread_id = uuid4()
        timeout = 30
        exc = ThreadBusyException(thread_id, timeout)

        assert exc.code == 1300004
        assert exc.message == "THREAD_BUSY"
        assert exc.http_status_code == 409
        assert str(thread_id) in exc.detail
        assert str(timeout) in exc.detail
        assert "正在处理" in exc.detail

    def test_thread_update_exception(self):
        """测试线程更新失败异常"""
        thread_id = uuid4()
        reason = "并发冲突"
        exc = ThreadUpdateException(thread_id, reason)

        assert exc.code == 1300006
        assert exc.message == "THREAD_UPDATE_FAILED"
        assert exc.http_status_code == 500
        assert str(thread_id) in exc.detail
        assert reason in exc.detail
        assert "更新失败" in exc.detail


class TestConversationExceptions:
    """测试对话相关异常"""

    def test_conversation_analysis_exception_with_reason(self):
        """测试对话分析失败异常（带原因）"""
        analysis_type = "报告"
        reason = "LLM调用超时"
        exc = ConversationAnalysisException(analysis_type, reason)

        assert exc.code == 1400004
        assert exc.message == "CONVERSATION_ANALYSIS_FAILED"
        assert exc.http_status_code == 500
        assert analysis_type in exc.detail
        assert reason in exc.detail
        assert "分析失败" in exc.detail

    def test_conversation_analysis_exception_without_reason(self):
        """测试对话分析失败异常（无原因）"""
        analysis_type = "标签"
        exc = ConversationAnalysisException(analysis_type)

        assert exc.code == 1400004
        assert analysis_type in exc.detail
        assert "分析失败" in exc.detail


class TestWorkflowExceptions:
    """测试工作流相关异常"""

    def test_workflow_execution_exception_with_reason(self):
        """测试工作流执行失败异常（带原因）"""
        workflow_type = "chat_sync"
        reason = "节点执行超时"
        exc = WorkflowExecutionException(workflow_type, reason)

        assert exc.code == 1400005
        assert exc.message == "WORKFLOW_EXECUTION_FAILED"
        assert exc.http_status_code == 500
        assert workflow_type in exc.detail
        assert reason in exc.detail
        assert "执行失败" in exc.detail

    def test_workflow_execution_exception_without_reason(self):
        """测试工作流执行失败异常（无原因）"""
        workflow_type = "suggestion"
        exc = WorkflowExecutionException(workflow_type)

        assert exc.code == 1400005
        assert workflow_type in exc.detail
        assert "执行失败" in exc.detail


class TestMarketingExceptions:
    """测试营销相关异常"""

    def test_marketing_plan_generation_exception_with_reason(self):
        """测试营销计划生成失败异常（带原因）"""
        reason = "产品数据不足"
        exc = MarketingPlanGenerationException(reason)

        assert exc.code == 1700002
        assert exc.message == "MARKETING_PLAN_GENERATION_FAILED"
        assert exc.http_status_code == 500
        assert reason in exc.detail
        assert "生成失败" in exc.detail

    def test_marketing_plan_generation_exception_without_reason(self):
        """测试营销计划生成失败异常（无原因）"""
        exc = MarketingPlanGenerationException()

        assert exc.code == 1700002
        assert "生成失败" in exc.detail


class TestMemoryExceptions:
    """测试记忆相关异常"""

    def test_memory_exception_with_reason(self):
        """测试记忆异常（带原因）"""
        reason = "向量数据库连接失败"
        exc = MemoryException(reason)

        assert exc.code == 1600001
        assert exc.message == "MEMORY_ERROR"
        assert exc.http_status_code == 500
        assert reason in exc.detail

    def test_memory_exception_without_reason(self):
        """测试记忆异常（无原因）"""
        exc = MemoryException()

        assert exc.code == 1600001
        assert "记忆操作失败" in exc.detail

    def test_memory_insert_failure_exception(self):
        """测试记忆插入失败异常"""
        failed_count = 3
        total_count = 5
        exc = MemoryInsertFailureException(failed_count, total_count)

        assert exc.code == 1600003
        assert exc.message == "MEMORY_INSERT_FAILURE"
        assert exc.http_status_code == 500
        assert str(failed_count) in exc.detail
        assert str(total_count) in exc.detail
        assert "插入失败" in exc.detail

    def test_memory_not_found_exception(self):
        """测试记忆不存在异常"""
        memory_id = "test_memory_123"
        exc = MemoryNotFoundException(memory_id)

        assert exc.code == 1600004
        assert exc.message == "MEMORY_NOT_FOUND"
        assert exc.http_status_code == 404
        assert memory_id in exc.detail
        assert "不存在" in exc.detail

    def test_memory_deletion_exception(self):
        """测试记忆删除失败异常"""
        memory_id = "test_memory_123"
        reason = "向量索引更新失败"
        exc = MemoryDeletionException(memory_id, reason)

        assert exc.code == 1600005
        assert exc.message == "MEMORY_DELETION_FAILED"
        assert exc.http_status_code == 500
        assert memory_id in exc.detail
        assert reason in exc.detail
        assert "删除失败" in exc.detail


class TestExceptionInheritance:
    """测试异常继承关系"""

    def test_tenant_exceptions_inherit_from_base(self):
        """测试租户异常继承自BaseHTTPException"""
        assert issubclass(TenantManagementException, BaseHTTPException)
        assert issubclass(TenantNotFoundException, TenantManagementException)
        assert issubclass(TenantValidationException, TenantManagementException)

    def test_workspace_exceptions_inherit_from_base(self):
        """测试工作空间异常继承自BaseHTTPException"""
        assert issubclass(WorkspaceException, BaseHTTPException)
        assert issubclass(AssistantException, WorkspaceException)
        assert issubclass(ThreadException, WorkspaceException)
        assert issubclass(MemoryException, WorkspaceException)

    def test_assistant_exceptions_inherit_from_assistant_exception(self):
        """测试助手异常继承关系"""
        assert issubclass(AssistantNotFoundException, AssistantException)
        assert issubclass(AssistantCreationException, AssistantException)
        assert issubclass(AssistantUpdateException, AssistantException)
        assert issubclass(AssistantDeletionException, AssistantException)

    def test_thread_exceptions_inherit_from_thread_exception(self):
        """测试线程异常继承关系"""
        assert issubclass(ThreadNotFoundException, ThreadException)
        assert issubclass(ThreadCreationException, ThreadException)
        assert issubclass(ThreadAccessDeniedException, ThreadException)
        assert issubclass(ThreadBusyException, ThreadException)
        assert issubclass(ThreadUpdateException, ThreadException)


class TestExceptionErrorCodes:
    """测试异常错误码唯一性"""

    def test_error_codes_are_unique(self):
        """测试所有错误码唯一"""
        exceptions = [
            # 租户相关 (100xxxx)
            TenantNotFoundException("test"),
            TenantValidationException("test", "reason"),
            TenantIdRequiredException(),
            TenantDisabledException("test"),
            TenantAlreadyExistsException("test"),
            # 助手相关 (110xxxx)
            AssistantNotFoundException(uuid4()),
            AssistantConflictException(uuid4()),
            AssistantInactiveException(uuid4(), AccountStatus.INACTIVE),
            AssistantCreationException(),
            AssistantUpdateException(uuid4()),
            AssistantDeletionException(uuid4()),
            # 线程相关 (130xxxx)
            ThreadNotFoundException(uuid4()),
            ThreadCreationException(),
            ThreadAccessDeniedException("test"),
            ThreadBusyException(uuid4()),
            ThreadUpdateException(uuid4()),
            # 对话相关 (140xxxx)
            ConversationAnalysisException("test"),
            WorkflowExecutionException("test"),
            # 营销相关 (170xxxx)
            MarketingPlanGenerationException(),
            # 记忆相关 (160xxxx)
            MemoryException(),
            MemoryInsertFailureException(1, 2),
            MemoryNotFoundException("test"),
            MemoryDeletionException("test"),
        ]

        error_codes = [exc.code for exc in exceptions]
        # 检查是否有重复的错误码
        assert len(error_codes) == len(set(error_codes)), f"发现重复的错误码: {error_codes}"