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
from typing import Optional, List
from sqlalchemy import select, update

from models import TenantModel
from models.assistant import AssistantModel, AssistantOrmModel
from infra.db.connection import database_session, test_db_connection
from utils import get_component_logger, get_current_datetime


logger = get_component_logger(__name__, "AssistantService")


class AssistantService:
    """
    租户数据库操作仓库
    
    提供纯粹的数据库操作
    所有方法都是静态的，不维护状态。
    """

    @staticmethod
    async def get_assistant_by_id(assistant_id: str) -> Optional[AssistantModel]:
        """
        根据ID获取租户配置

        参数:
            tenant_id: 租户ID

        返回:
            TenantConfig: 租户配置，不存在则返回None
        """
        try:
            async with database_session() as session:
                stmt = select(AssistantOrmModel).where(AssistantOrmModel.assistant_id == assistant_id)
                result = await session.execute(stmt)
                assistant_model = result.scalar_one_or_none()

                if assistant_model:
                    return assistant_model.to_business_model()

                return None

        except Exception as e:
            logger.error(f"获取助理配置失败: {assistant_id}, 错误: {e}")
            raise

    @staticmethod
    async def save(assistantData: AssistantModel) -> bool:
        """
        保存助理配置（创建或更新）
        
        参数:
            config: 助理配置
            
        返回:
            bool: 是否保存成功
        """

        try:
            async with (database_session() as session):
                # 查找现有助理
                assistantData.updated_at = get_current_datetime()
                stmt = select(AssistantOrmModel).where(AssistantOrmModel.assistant_id == assistantData.assistant_id)
                # print(stmt)  # 这将包括参数值，但如果使用了编译方言，则需要确保方言与数据库匹配。
                # print(assistantData.assistant_id)  # 这将包括参数值，但如果使用了编译方言，则需要确保方言与数据库匹配。

                result = await session.execute(stmt)
                existing_assistant = result.scalar_one_or_none()

                if existing_assistant:
                    # 更新现有助理
                    existing_assistant.update_from_business_mode_assistant(assistantData)
                    logger.debug(f"更新助理: {assistantData.assistant_id}")
                else:
                    # 创建新租户
                    new_assistant = AssistantOrmModel.from_business_model(assistantData)
                    session.add(new_assistant)
                    logger.debug(f"创建助理: {assistantData.assistant_id}")

                await session.commit()
                return True

        except Exception as e:
            logger.error(f"保存租户配置失败: {assistantData.assistant_id}, 错误: {e}")
            raise

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
                    .values(is_active=False, updated_at=get_current_datetime())
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
    async def get_all_tenants() -> List[str]:
        """
        获取所有激活状态的租户ID列表

        返回:
            List[str]: 激活的租户ID列表
        """
        try:
            async with database_session() as session:
                stmt = select(TenantModel.tenant_id).where(TenantModel.is_active == True)
                result = await session.execute(stmt)
                tenant_ids = [row[0] for row in result.fetchall()]

                logger.debug(f"查询到 {len(tenant_ids)} 个活跃租户")
                return tenant_ids

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
