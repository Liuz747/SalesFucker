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

import msgpack
from redis import Redis, RedisError
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import mas_config
from infra.cache import get_redis_client
from models.assistant import AssistantModel, AssistantOrmModel
from utils import get_component_logger, get_current_datetime

logger = get_component_logger(__name__, "AssistantService")


class AssistantRepository:
    """
    租户数据库操作仓库
    
    提供纯粹的数据库操作
    所有方法都是静态的，不维护状态。
    """

    @staticmethod
    async def get_assistant_by_id(assistant_id: str, session: AsyncSession) -> Optional[AssistantOrmModel]:
        """
        根据ID获取租户配置

        参数:
            tenant_id: 租户ID

        返回:
            TenantConfig: 租户配置，不存在则返回None
        """
        try:
            stmt = select(AssistantOrmModel).where(AssistantOrmModel.assistant_id == assistant_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"获取助理配置失败: {assistant_id}, 错误: {e}")
            raise

    @staticmethod
    async def insert_assistant(assistantData: AssistantModel, session: AsyncSession) -> bool:
        """
        保存助理配置（创建或更新）
        
        参数:
            config: 助理配置
            
        返回:
            bool: 是否保存成功
        """

        try:
            # 查找现有助理
            # assistantData.updated_at = get_current_datetime()
            # stmt = select(AssistantOrmModel).where(AssistantOrmModel.assistant_id == assistantData.assistant_id)
            #
            # result = await session.execute(stmt)
            # existing_assistant = result.scalar_one_or_none()
            #
            # if existing_assistant:
            #     # 更新现有助理
            #     existing_assistant.update_from_business_mode_assistant(assistantData)
            #     logger.debug(f"更新助理: {assistantData.assistant_id}")
            # else:
            #     # 创建新租户
            new_assistant = AssistantOrmModel.from_business_model(assistantData)
            session.add(new_assistant)
            logger.debug(f"创建助理: {assistantData.assistant_id}")

            return True

        except Exception as e:
            logger.error(f"保存租户配置失败: {assistantData.assistant_id}, 错误: {e}")
            raise

    @staticmethod
    async def update_assistant(assistant: AssistantOrmModel, session: AsyncSession) -> Optional[AssistantOrmModel]:
        """更新租户数据库模型"""
        try:
            assistant.updated_at = get_current_datetime()
            await session.merge(assistant)
            return assistant
        except Exception as e:
            logger.error(f"更新数字员工失败: {assistant.assistant_name}, 错误: {e}")
            raise

    @staticmethod
    async def delete(assistant_id: str, session: AsyncSession) -> bool:
        """
        删除租户（软删除）

        参数:
            tenant_id: 租户ID

        返回:
            bool: 是否删除成功
        """
        try:
            # 软删除：设置为非激活状态
            stmt = (
                update(AssistantOrmModel)
                .where(AssistantOrmModel.assistant_id == assistant_id)
                .values(is_active=False, updated_at=get_current_datetime())
            )
            result = await session.execute(stmt)
            await session.commit()

            flag = result.rowcount > 0
            if flag:
                logger.info(f"软删除租户: assistant_id={assistant_id}")
            else:
                logger.warning(f"租户不存在，无法删除: assistant_id={assistant_id}")

            return flag
        except Exception as e:
            logger.error(f"删除租户失败: assistant_id={assistant_id}, 错误: {e}")
            raise

    @staticmethod
    async def update_assistant_cache(assistant_model: AssistantModel, redis_client: Redis):
        """更新数字员工缓存"""
        try:
            redis_key = f"assistant:{assistant_model.assistant_id}"
            tenant_data = assistant_model.model_dump(mode='json')

            await redis_client.setex(
                redis_key,
                mas_config.REDIS_TTL,
                msgpack.packb(tenant_data),
            )
            logger.debug(f"更新租户缓存: {assistant_model.assistant_id}")
        except RedisError as e:
            logger.error(f"redis 命令执行失败: {e}")
            raise
        except Exception as e:
            logger.error(f"更新租户缓存失败: {assistant_model.assistant_id}, 错误: {e}")
            raise

    @staticmethod
    async def update_assistant_cache_4_task(assistant_model: AssistantModel, redis_client: Redis = None):
        """获取数字员工缓存"""
        try:
            if not redis_client:
                redis_client = await get_redis_client()
            asyncio.create_task(AssistantRepository.update_assistant_cache(
                assistant_model,
                redis_client
            ))
        except Exception as e:
            raise

    @staticmethod
    async def get_assistant_cache(assistant_id: str, redis_client: Redis) -> Optional[AssistantModel]:
        """获取数字员工缓存"""
        try:
            redis_key = f"assistant:{assistant_id}"
            assistant_data = await redis_client.get(redis_key)

            if assistant_data:
                assistant_data = msgpack.unpackb(assistant_data, raw=False)
                return AssistantModel(**assistant_data)
            return None
        except RedisError as e:
            logger.error(f"redis 命令执行失败: {e}")
            raise
        except Exception as e:
            logger.error(f"获取数字员工缓存失败: {assistant_id}, 错误: {e}")
            raise
