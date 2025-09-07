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
from uuid import UUID
from typing import Optional, List

from sqlalchemy import select, update, and_, desc

from models.prompts import PromptsOrmModel
from models.tenant import TenantModel, TenantOrm
from infra.db.connection import database_session, get_session, test_db_connection
from utils import get_component_logger
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)

logger = get_component_logger(__name__, "TenantDao")


class TenantDao:

    @staticmethod
    async def get_tenant(tenant_id: str, session: AsyncSession = None) -> Optional[TenantOrm]:
        try:
            if session is None:
                session = await get_session()
                stmt = select(TenantOrm).where(
                    TenantOrm.tenant_id == tenant_id
                )
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"获取租户列表失败: {e}")
            raise


    @staticmethod
    async def insert_tenant(orm: TenantOrm, session: AsyncSession = None) -> UUID:
        try:
            if session is None:
                session = await get_session()
                # 创建新租户
                session.add(orm)
                logger.debug(f"创建租户: {orm.tenant_id}")
                await session.commit()
                return orm.id

        except Exception as e:
            logger.error(f"创建提示词: {orm.tenant_id} 错误：{e}")
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
