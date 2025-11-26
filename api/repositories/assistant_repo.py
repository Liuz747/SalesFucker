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

from typing import Optional
from uuid import UUID

import msgpack
from redis import Redis, RedisError
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import mas_config
from models.assistant import AssistantModel, AssistantOrmModel
from utils import get_component_logger

logger = get_component_logger(__name__, "AssistantService")


class AssistantRepository:
    """
    租户数据库操作仓库
    
    提供纯粹的数据库操作
    所有方法都是静态的，不维护状态。
    """

    @staticmethod
    async def get_assistant_by_id(
        assistant_id: UUID,
        session: AsyncSession,
        include_inactive: bool = False
    ) -> Optional[AssistantOrmModel]:
        """
        根据ID获取助理配置

        参数:
            assistant_id: 助理ID
            session: 数据库会话
            include_inactive: 是否包含已删除（is_active=False）的助理

        返回:
            AssistantOrmModel: 助理配置，不存在则返回None
        """
        try:
            stmt = select(AssistantOrmModel).where(AssistantOrmModel.assistant_id == assistant_id)
            if not include_inactive:
                stmt = stmt.where(AssistantOrmModel.is_active == True)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"获取助理配置失败: {assistant_id}, 错误: {e}")
            raise

    @staticmethod
    async def insert_assistant(assistant_data: AssistantModel, session: AsyncSession) -> Optional[AssistantOrmModel]:
        """
        创建新助理

        参数:
            assistant_data: 助理业务模型
            session: 数据库会话

        返回:
            AssistantOrmModel
        """
        try:
            new_assistant = AssistantOrmModel.to_orm_model(assistant_data)
            session.add(new_assistant)
            await session.flush()
            await session.refresh(new_assistant)
            logger.debug(f"创建助理: {new_assistant.assistant_id}")
            return new_assistant

        except Exception as e:
            logger.error(f"保存助理配置失败, 错误: {e}")
            raise

    @staticmethod
    async def update_assistant(assistant: AssistantOrmModel, session: AsyncSession) -> AssistantOrmModel:
        """更新租户数据库模型"""
        try:
            assistant.updated_at = func.now()
            merged_assistant = await session.merge(assistant)
            await session.flush()
            await session.refresh(merged_assistant)
            return merged_assistant
        except Exception as e:
            logger.error(f"更新数字员工失败: {assistant.assistant_name}, 错误: {e}")
            raise

    @staticmethod
    async def delete(assistant_id: UUID, session: AsyncSession) -> bool:
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
                .values(is_active=False, updated_at=func.now())
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
            redis_key = f"assistant:{str(assistant_model.assistant_id)}"
            assistant_data = assistant_model.model_dump(mode='json')

            await redis_client.setex(
                redis_key,
                mas_config.REDIS_TTL,
                msgpack.packb(assistant_data),
            )
            logger.debug(f"更新租户缓存: {assistant_model.assistant_id}")
        except RedisError as e:
            logger.error(f"redis 命令执行失败: {e}")
            raise
        except Exception as e:
            logger.error(f"更新租户缓存失败: {assistant_model.assistant_id}, 错误: {e}")
            raise

    @staticmethod
    async def get_assistant_cache(assistant_id: UUID, redis_client: Redis) -> Optional[AssistantModel]:
        """获取数字员工缓存"""
        try:
            redis_key = f"assistant:{str(assistant_id)}"
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

    @staticmethod
    async def delete_assistant_cache(assistant_id: UUID, redis_client: Redis) -> bool:
        """删除数字员工缓存"""
        try:
            redis_key = f"assistant:{str(assistant_id)}"
            result = await redis_client.delete(redis_key)
            logger.debug(f"删除助理缓存: {assistant_id}, 结果: {result}")
            return result > 0
        except RedisError as e:
            logger.error(f"redis 命令执行失败: {e}")
            raise
        except Exception as e:
            logger.error(f"删除数字员工缓存失败: {assistant_id}, 错误: {e}")
            raise
