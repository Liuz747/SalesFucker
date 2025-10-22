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

from datetime import datetime
from typing import Optional
from uuid import UUID

import msgpack
from redis import RedisError
from sqlalchemy import select, update, and_, func

from config import mas_config
from models.prompts import PromptsOrmModel, PromptsModel
from models import TenantModel
from infra.db.connection import database_session, test_db_connection
from utils import get_component_logger
from sqlalchemy.ext.asyncio import AsyncSession
from redis import Redis, RedisError
from infra.cache import get_redis_client

logger = get_component_logger(__name__, "PromptsDao")


class PromptsRepository:
    """
    租户数据库操作仓库
    
    提供纯粹的数据库操作
    所有方法都是静态的，不维护状态。
    """

    @staticmethod
    async def get_latest_prompts_by_assistant_id(assistant_id: str, session: AsyncSession) -> Optional[PromptsOrmModel]:
        """根据ID获取提示词数据库模型"""
        try:
            stmt = (select(PromptsOrmModel).where(PromptsOrmModel.assistant_id == assistant_id)
                    .order_by(PromptsOrmModel.version).limit(1))
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"获取租户数据库模型失败: {assistant_id}, 错误: {e}")
            raise

    @staticmethod
    async def insert_prompts(orm: PromptsOrmModel, session: AsyncSession) -> UUID:
        """
        保存租户配置（创建或更新）
        
        参数:
            config: 租户配置
            
        返回:
            bool: 是否保存成功
        """
        try:
            # 创建新租户
            session.add(orm)
            logger.debug(f"创建提示词: {orm.tenant_id} {orm.assistant_id} {orm.personality_prompt}")
            await session.flush()
            return orm.id
        except Exception as e:
            logger.error(f"创建提示词: {orm.tenant_id} {orm.assistant_id} {orm.personality_prompt} 错误：{e}")
            raise

    @staticmethod
    async def update_prompts_field(assistant_id: str, value: dict, session: AsyncSession) -> bool:
        """更新数字员工数据库模型字段"""
        try:
            value['updated_at'] = func.now()
            stmt = (
                update(PromptsOrmModel)
                .where(PromptsOrmModel.assistant_id == assistant_id)
                .values(**value)
            )
            result = await session.execute(stmt)
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"更新租户数据库模型字段失败: {assistant_id}, 错误: {e}")
            raise

    @staticmethod
    async def update_prompts_cache(prompts_model: PromptsModel, redis_client: Redis = None):
        """更新提示词缓存"""
        try:
            if not redis_client:
                redis_client = await get_redis_client()
            redis_key = PromptsRepository.get_prompts_key(prompts_model.assistant_id, prompts_model.version)
            tenant_data = prompts_model.model_dump(mode='json')

            await redis_client.setex(
                redis_key,
                mas_config.REDIS_TTL,
                msgpack.packb(tenant_data),
            )
            logger.debug(f"更新租户缓存: {prompts_model.id}")
        except RedisError as e:
            logger.error(f"redis 命令执行失败: {e}")
            raise
        except Exception as e:
            logger.error(f"更新租户缓存失败: {prompts_model.id}, 错误: {e}")
            raise

    @staticmethod
    async def get_prompts_cache(assistant_id: str, version: int, redis_client: Redis = None) -> PromptsModel:
        """更新提示词缓存"""
        try:
            if not redis_client:
                redis_client = await get_redis_client()
            redis_key = PromptsRepository.get_prompts_key(assistant_id, version)
            prompt_version_model = await redis_client.get(redis_key)

            if prompt_version_model:
                prompt_model = msgpack.unpackb(prompt_version_model, raw=False)
                return PromptsModel(**prompt_model)
            return None
        except RedisError as e:
            logger.error(f"redis 命令执行失败: {e}")
            raise
        except Exception as e:
            logger.error(f"获取租户指定 version 提示词: assistant_id={assistant_id},version={version} 错误: {e}")
            raise

    @staticmethod
    async def update_prompts_latest_version_cache(assistant_id: str, version: int, redis_client: Redis = None):
        """更新提示词缓存"""
        try:
            if not redis_client:
                redis_client = await get_redis_client()
            redis_key = PromptsRepository.get_version_key(assistant_id)

            await redis_client.setex(
                redis_key,
                mas_config.REDIS_TTL,
                version,
            )
            logger.debug(f"更新租户缓存: assistant_id={assistant_id} version={version}")
        except RedisError as e:
            logger.error(f"redis 命令执行失败: {e}")
            raise
        except Exception as e:
            logger.error(f"更新租户缓存失败: assistant_id={assistant_id} version={version}, 错误: {e}")
            raise

    @staticmethod
    async def get_prompts_latest_version_cache(assistant_id: str, redis_client: Redis = None) -> int:
        """更新提示词缓存"""
        try:
            if not redis_client:
                redis_client = await get_redis_client()
            redis_key = PromptsRepository.get_version_key(assistant_id)
            prompts_version = await redis_client.get(redis_key)

            if prompts_version:
                return int(prompts_version)
            return None
        except RedisError as e:
            logger.error(f"redis 命令执行失败: {e}")
            raise
        except Exception as e:
            logger.error(f"获取租户指定 version 提示词: assistant_id={assistant_id} 错误: {e}")
            raise

    @staticmethod
    def get_prompts_key(assistant_id: str, version: int) -> str:
        return f"prompts:{assistant_id}:{version}"

    @staticmethod
    def get_version_key(assistant_id: str) -> str:
        return f"prompts:latest_version:{assistant_id}"

    @staticmethod
    async def delete(tenant_id: str) -> bool:
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
                stmt = (
                    update(TenantModel)
                    .where(TenantModel.tenant_id == tenant_id)
                    .values(status=0)
                )
                result = await session.execute(stmt)
                await session.commit()

                flag = result.rowcount > 0
                if flag:
                    logger.info(f"软删除租户: {tenant_id}")
                else:
                    logger.warning(f"租户不存在，无法删除: {tenant_id}")

                return flag

        except Exception as e:
            logger.error(f"删除租户失败: {tenant_id}, 错误: {e}")
            raise

    @staticmethod
    async def get_prompts_by_version(assistant_id: str, version: int) -> PromptsOrmModel:
        """
        获取所有激活状态的租户ID列表
        
        返回:
            List[str]: 激活的租户ID列表
        """
        try:
            async with database_session() as session:
                stmt = select(PromptsOrmModel).where(
                    and_(
                        PromptsOrmModel.assistant_id == assistant_id,
                        PromptsOrmModel.version == version
                    )
                )
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"获取租户列表失败: {e}")
            raise

    @staticmethod
    async def get_prompts_list_order(tenant_id: str, assistant_id: str, limitNum: int) -> list[PromptsOrmModel]:
        """
        获取所有激活状态的租户ID列表

        返回:
            List[str]: 激活的租户ID列表
        """
        try:
            async with (database_session() as session):

                stmt = select(PromptsOrmModel).where(
                    and_(PromptsOrmModel.tenant_id == tenant_id,
                         PromptsOrmModel.tenant_id == assistant_id
                         )
                ).order_by(PromptsOrmModel.updated_at.desc()).limit(limitNum)

                result = await session.execute(stmt)
                r = result.scalars().all()
                return r

        except Exception as e:
            logger.error(f"获取租户列表失败: {e}")
            raise

    @staticmethod
    async def update_access_stats(tenant_id: str, access_time: datetime) -> bool:
        """
        更新租户访问统计
        
        参数:
            tenant_id: 租户ID
            access_time: 访问时间
            
        返回:
            bool: 是否更新成功
        """
        try:
            async with database_session() as session:
                stmt = (
                    update(TenantModel)
                    .where(TenantModel.tenant_id == tenant_id)
                    .values(
                        last_access=access_time,
                        total_requests=TenantModel.total_requests + 1
                    )
                )
                await session.execute(stmt)
                await session.commit()

        except Exception as e:
            logger.error(f"更新租户访问统计失败: {tenant_id}, 错误: {e}")
            raise

    @staticmethod
    async def count_total() -> int:
        """
        获取租户总数
        
        返回:
            int: 租户总数（包括激活和非激活）
        """
        try:
            async with database_session() as session:
                stmt = select(TenantModel.tenant_id)
                result = await session.execute(stmt)
                total = len(result.fetchall())

                logger.debug(f"租户总数: {total}")
                return total

        except Exception as e:
            logger.error(f"获取租户总数失败: {e}")
            raise

    @staticmethod
    async def health_check() -> dict:
        """
        数据库健康检查
        
        返回:
            dict: 健康状态信息
        """
        try:
            # 测试数据库连接
            db_healthy = await test_db_connection()

            if db_healthy:
                # 获取租户统计
                total_tenants = await TenantService.count_total()
                active_tenants = len(await TenantService.get_all_tenants())

                return {
                    "database_connected": True,
                    "total_tenants": total_tenants,
                    "active_tenants": active_tenants,
                }
            else:
                return {
                    "database_connected": False,
                    "total_tenants": 0,
                    "active_tenants": 0,
                }

        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")
            return {
                "database_connected": False,
                "error": str(e),
                "total_tenants": 0,
                "active_tenants": 0,
            }
