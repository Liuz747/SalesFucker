"""
租户数据访问存储库

提供纯粹的数据访问操作:
- 租户数据库CRUD操作（PostgreSQL） 
- 纯数据访问，无业务逻辑
- 依赖注入，支持外部会话管理
"""

from typing import Optional

import msgpack
from redis import Redis, RedisError
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from config import mas_config
from models import TenantOrm, TenantModel
from utils import get_component_logger
from utils.time_utils import SHANGHAI_TZ, get_current_datetime

logger = get_component_logger(__name__, "TenantRepository")


class TenantRepository:

    @staticmethod
    async def get_tenant_by_tenant_id(tenant_id: str, session: AsyncSession) -> Optional[TenantOrm]:
        """根据ID获取租户数据库模型"""
        try:
            stmt = select(TenantOrm).where(TenantOrm.tenant_id == tenant_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"获取租户数据库模型失败: {tenant_id}, 错误: {e}")
            raise

    @staticmethod
    async def insert_tenant(tenant: TenantOrm, session: AsyncSession) -> str:
        """创建租户数据库模型"""
        try:
            session.add(tenant)
            logger.debug(f"创建租户: {tenant.tenant_id}")
            return tenant.tenant_id
        except Exception as e:
            logger.error(f"创建租户数据库模型失败: {tenant.tenant_id}, 错误: {e}")
            raise

    @staticmethod
    async def update_tenant(tenant: TenantOrm, session: AsyncSession) -> Optional[TenantOrm]:
        """更新租户数据库模型"""
        try:
            tenant.updated_at = get_current_datetime()
            await session.merge(tenant)
            logger.debug(f"更新租户: {tenant.tenant_id}")
            # todo 需要判断修改行数
            return tenant
        except Exception as e:
            logger.error(f"更新租户数据库模型失败: {tenant.tenant_id}, 错误: {e}")
            raise

    @staticmethod
    async def update_tenant_field(tenant_id: str, value: dict, session: AsyncSession) -> bool:
        """更新租户数据库模型字段"""
        try:
            stmt = (
                update(TenantOrm)
                .where(TenantOrm.tenant_id == tenant_id)
                .values(**value)
            )
            result = await session.execute(stmt)
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"更新租户数据库模型字段失败: {tenant_id}, 错误: {e}")
            raise

    @staticmethod
    async def delete_tenant(tenant_id: str, session: AsyncSession) -> Optional[TenantOrm]:
        """删除租户数据库模型"""
        try:
            tenant = await session.get(TenantOrm, tenant_id)
            if not tenant:
                return None

            tenant.is_active = False
            tenant.updated_at = func.now()
            logger.debug(f"删除租户: {tenant_id}")

            return tenant

        except Exception as e:
            logger.error(f"删除租户数据库模型失败: {tenant_id}, 错误: {e}")
            raise

    @staticmethod
    async def get_tenant_cache(tenant_id: str, redis_client: Redis) -> Optional[TenantModel]:
        """获取租户缓存"""
        try:
            redis_key = f"tenant:{tenant_id}"
            tenant_data = await redis_client.get(redis_key)

            if tenant_data:
                tenant_data = msgpack.unpackb(tenant_data, raw=False)
                return TenantModel(**tenant_data)
            return None
        except RedisError as e:
            print(f"redis 命令执行失败: {e}")
            raise
        except Exception as e:
            logger.error(f"获取租户缓存失败: {tenant_id}, 错误: {e}")
            raise

    @staticmethod
    async def update_tenant_cache(tenant_model: TenantModel, redis_client: Redis):
        """更新租户缓存"""
        try:
            redis_key = f"tenant:{tenant_model.tenant_id}"
            tenant_data = tenant_model.model_dump(mode='json')

            await redis_client.setex(
                redis_key,
                mas_config.REDIS_TTL,
                msgpack.packb(tenant_data),
            )
            logger.debug(f"更新租户缓存: {tenant_model.tenant_id}")
        except RedisError as e:
            print(f"redis 命令执行失败: {e}")
            raise
        except Exception as e:
            logger.error(f"更新租户缓存失败: {tenant_model.tenant_id}, 错误: {e}")
            raise

    @staticmethod
    async def delete_tenant_cache(tenant_id: str, redis_client: Redis) -> bool:
        """删除租户缓存"""
        try:
            redis_key = f"tenant:{tenant_id}"
            deleted_count = await redis_client.delete(redis_key)

            if deleted_count > 0:
                logger.debug(f"删除租户缓存成功: {tenant_id}")
                return True
            else:
                logger.debug(f"租户缓存不存在，无需删除: {tenant_id}")
                return True
        except RedisError as e:
            print(f"redis 命令执行失败: {e}")
            raise
        except Exception as e:
            logger.error(f"删除租户缓存失败: {tenant_id}, 错误: {e}")
            raise
