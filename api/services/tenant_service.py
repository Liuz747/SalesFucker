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

from sqlalchemy.exc import IntegrityError

from libs.exceptions import TenantNotFoundException, TenantAlreadyExistsException
from libs.factory import infra_registry
from repositories.tenant_repo import TenantRepository, TenantModel, AccountStatus
from utils import get_component_logger

logger = get_component_logger(__name__, "TenantService")


class TenantService:
    """
    租户数据库操作仓库
    
    提供纯粹的数据库操作
    所有方法都是静态的，不维护状态。
    """

    @staticmethod
    async def create_tenant(tenant: TenantModel) -> Optional[TenantModel]:
        """创建租户"""
        try:
            tenant_orm = tenant.to_orm()

            async with infra_registry.get_db_session() as session:
                flag = await TenantRepository.insert_tenant(tenant_orm, session)

            if flag:
                # 获取Redis客户端
                redis_client = infra_registry.get_cached_clients().redis
                tenant_model = TenantModel.to_model(tenant_orm)
                asyncio.create_task(TenantRepository.update_tenant_cache(
                    tenant_model,
                    redis_client
                ))
                return tenant_model

            logger.error(f"创建租户失败: {tenant.tenant_id}")
            return None

        except IntegrityError as e:
            logger.error(f"创建租户失败，租户ID已存在: {tenant.tenant_id}")
            raise TenantAlreadyExistsException(tenant.tenant_id)
        except Exception as e:
            logger.error(f"创建租户失败: {tenant.tenant_id}, 错误: {e}")
            raise

    @staticmethod
    async def query_tenant(tenant_id: str, use_cache=False) -> Optional[TenantModel]:
        """
        根据ID获取租户业务模型
        
        参数:
            tenant_id: 租户ID
            
        返回:
            Optional[Tenant]: 租户业务模型，不存在则返回None
        """
        try:
            redis_client = infra_registry.get_cached_clients().redis

            if use_cache:

                # Level 1: Redis缓存 (< 10ms)
                tenant_model = await TenantRepository.get_tenant_cache(tenant_id, redis_client)
                if tenant_model:
                    return tenant_model

            # Level 2: 数据库查询
            async with infra_registry.get_db_session() as session:
                tenant_orm = await TenantRepository.get_tenant_by_id(tenant_id, session)

            if tenant_orm:
                tenant_model = TenantModel.to_model(tenant_orm)
                asyncio.create_task(TenantRepository.update_tenant_cache(
                    tenant_model,
                    redis_client
                ))
                return tenant_model

            logger.debug(f"租户不存在: {tenant_id}")
            return None

        except Exception as e:
            logger.error(f"获取租户配置失败: {tenant_id}, 错误: {e}")
            raise

    @staticmethod
    async def update_tenant(
        tenant_id: str,
        tenant_status: Optional[AccountStatus] = None
    ) -> TenantModel:
        """更新租户"""
        try:
            async with infra_registry.get_db_session() as session:
                tenant_orm = await TenantRepository.get_tenant_by_id(tenant_id, session)
                if not tenant_orm:
                    raise TenantNotFoundException(tenant_id)

                tenant_orm.status = tenant_status or tenant_orm.status
                updated_tenant_orm = await TenantRepository.update_tenant(tenant_orm, session)

            # 修改数据成功后，刷新缓存
            redis_client = infra_registry.get_cached_clients().redis
            tenant_model = TenantModel.to_model(updated_tenant_orm)
            asyncio.create_task(TenantRepository.update_tenant_cache(
                tenant_model,
                redis_client
            ))

            return tenant_model
        except Exception as e:
            logger.error(f"更新租户失败: {tenant_id}, 错误: {e}")
            raise

    @staticmethod
    async def delete_tenant(tenant_id: str) -> bool:
        """
        删除租户（软删除）
        
        参数: tenant_id: 租户ID
        
        返回: bool: 是否删除成功
        """
        try:
            async with infra_registry.get_db_session() as session:
                # 软删除：设置为非激活状态
                tenant_orm = await TenantRepository.delete_tenant(tenant_id, session)

            if tenant_orm:
                # 直接获取Redis客户端，使用连接池
                redis_client = infra_registry.get_cached_clients().redis
                # 异步执行缓存实际删除 - 从Redis中彻底移除
                asyncio.create_task(TenantRepository.delete_tenant_cache(
                    tenant_id,
                    redis_client
                ))
                return True
            else:
                logger.error(f"租户不存在: {tenant_id}")
                return False

        except Exception as e:
            logger.error(f"删除租户失败: {tenant_id}, 错误: {e}")
            raise
