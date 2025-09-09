"""
租户数据库操作层

该模块提供纯粹的租户数据库CRUD操作，不包含业务逻辑。
遵循Repository模式，专注于数据持久化和查询操作。

核心功能:
- 租户配置的数据库CRUD操作
- 租户访问记录更新
- 数据库健康检查
- 高效查询和索引优化
"""

import asyncio
from typing import Optional

from api.schemas.schema_tenant import TenantSyncRequest
from models.tenant import TenantModel, TenantOrm
from models.tenant import TenantOrm
from controllers.workspace.account.model import Tenant
from infra.db.connection import database_session
from infra.cache.redis_client import get_redis_client
from repositories.tenant_repo import TenantRepository
from infra.db.connection import database_session, test_db_connection
from services.tenant_dao import TenantDao
from utils import get_component_logger

logger = get_component_logger(__name__, "TenantService")


class TenantService:
    """
    租户数据库操作仓库
    
    提供纯粹的数据库操作
    所有方法都是静态的，不维护状态。
    """
    
    def __init__(self):
        self._redis_client = None

    async def dispatch(self):
        """初始化服务依赖（Redis客户端连接）"""
        try:
            self._redis_client = await get_redis_client()
            await self._redis_client.ping()
            logger.info("Redis连接初始化完成")
        except Exception as e:
            logger.error(f"Redis连接初始化失败: {e}")
            raise

        logger.info("租户服务初始化完成")

    async def create_tenant(self, tenant: TenantOrm) -> bool:
        """创建租户"""
        try:
            async with database_session() as session:
                tenant_id = await TenantRepository.insert_tenant(tenant, session)

                if tenant_id:
                    tenant_model = Tenant.to_model(tenant)
                    asyncio.create_task(TenantRepository.update_tenant_cache(
                        tenant_model,
                        self._redis_client
                    ))
                    return True

            logger.error(f"创建租户失败: {tenant_id}")
            return False
        except Exception as e:
            logger.error(f"创建租户失败: {tenant_id}, 错误: {e}")
            raise

    async def query_tenant(self, tenant_id: str) -> Optional[TenantOrm]:
        """
        根据ID获取租户ORM对象
        
        参数:
            tenant_id: 租户ID
            
        返回:
            Optional[TenantOrm]: 租户ORM对象，不存在则返回None
        """
        try:
            # Level 1: Redis缓存 (< 10ms)
            tenant_model = await TenantRepository.get_tenant_cache(tenant_id, self._redis_client)
            if tenant_model:
                return tenant_model.to_orm()

            # Level 2: 数据库查询
            async with database_session() as session:
                tenant_orm = await TenantRepository.get_tenant(tenant_id, session)
                if tenant_orm:
                    tenant_model = Tenant.to_model(tenant_orm)
                    asyncio.create_task(TenantRepository.update_tenant_cache(
                        tenant_model,
                        self._redis_client
                    ))
                    return tenant_orm

            logger.error(f"租户不存在: {tenant_id}")
            return None

        except Exception as e:
            logger.error(f"获取租户配置失败: {tenant_id}, 错误: {e}")
            raise
    
    async def update_tenant(self, tenant_orm: TenantOrm) -> TenantOrm:
        """更新租户"""
        try:
            async with database_session() as session:
                await TenantRepository.update_tenant(tenant_orm, session)

            tenant_model = Tenant.to_model(tenant_orm)
            asyncio.create_task(TenantRepository.update_tenant_cache(
                tenant_model,
                self._redis_client
            ))

            return tenant_orm

        except Exception as e:
            logger.error(f"更新租户失败: {tenant_orm.tenant_id}, 错误: {e}")
            raise

    async def delete_tenant(self, tenant_id: str) -> bool:
        """
        删除租户（软删除）
        
        参数:
            tenant_id: 租户ID

        返回:
            bool: 是否删除成功
        """
        try:
            async with database_session() as session:
                # 软删除：设置为非激活状态
                tenant_orm = await TenantRepository.delete_tenant(tenant_id, session)

            if tenant_orm:
                # 异步执行缓存实际删除 - 从Redis中彻底移除
                asyncio.create_task(TenantRepository.delete_tenant_cache(
                    tenant_id,
                    self._redis_client
                ))
                return True
            else:
                logger.error(f"租户不存在: {tenant_id}")
                return False

        except Exception as e:
            logger.error(f"删除租户失败: {tenant_id}, 错误: {e}")
            raise

    async def cleanup(self):
        """清理资源"""
        # 清理Redis客户端引用（共享连接池由应用层管理）
        self._redis_client = None