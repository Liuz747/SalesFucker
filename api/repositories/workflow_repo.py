"""
工作流执行数据访问存储库

该模块提供纯粹的工作流执行数据访问操作，不包含业务逻辑。
遵循Repository模式，专注于数据持久化和查询操作，支持数据库和缓存的独立访问。

核心功能:
- 工作流执行数据库CRUD操作（PostgreSQL）
- 工作流执行缓存操作（Redis）
- 纯数据访问，无业务逻辑
- 依赖注入，支持外部会话管理
"""

from utils import get_component_logger

logger = get_component_logger(__name__, "WorkflowRepository")


class WorkflowRepository:
    """
    提供工作流执行数据访问操作:
    1. 数据库操作 - PostgreSQL CRUD操作，依赖注入AsyncSession
    2. 缓存操作 - Redis读写操作，依赖注入Redis客户端
    3. 无业务逻辑 - 仅处理数据持久化和检索
    4. 静态方法 - 无状态设计，支持依赖注入
    """
