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
from sqlalchemy.sql import func

from models.tenant import TenantOrm
from controllers.workspace.account.model import Tenant
from infra.db.connection import database_session, test_db_connection
from utils import get_component_logger

logger = get_component_logger(__name__, "TenantService")


class TenantService:
    """
    租户数据库操作仓库
    
    提供纯粹的数据库操作
    所有方法都是静态的，不维护状态。
    """
    
    @staticmethod
    async def _get_tenant_by_id(session, tenant_id: str) -> Optional[TenantOrm]:
        """
        获取租户数据库模型
        
        参数:
            session: 数据库会话
            tenant_id: 租户ID
            
        返回:
            TenantOrm: 租户数据库模型，不存在则返回None
        """
        stmt = select(TenantOrm).where(TenantOrm.tenant_id == tenant_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def query(tenant_id: str) -> Optional[Tenant]:
        """
        根据ID获取租户配置
        
        参数:
            tenant_id: 租户ID
            
        返回:
            Tenant: 租户配置，不存在则返回None
        """
        try:
            async with database_session() as session:
                orm_obj = await TenantService._get_tenant_by_id(session, tenant_id)
                
                if orm_obj:
                    return Tenant(
                        tenant_id=orm_obj.tenant_id,
                        tenant_name=orm_obj.tenant_name,
                        status=orm_obj.status,
                        industry=orm_obj.industry,
                        company_size=orm_obj.company_size,
                    )
                
                return None

        except Exception as e:
            logger.error(f"获取租户配置失败: {tenant_id}, 错误: {e}")
            raise
    
    @staticmethod
    async def save(config: Tenant) -> bool:
        """
        保存租户配置（创建或更新）
        
        参数:
            config: 租户配置
            
        返回:
            bool: 是否保存成功
        """
        try:
            async with database_session() as session:
                # 查找现有租户
                existing_tenant = await TenantService._get_tenant_by_id(session, config.tenant_id)
                
                if existing_tenant:
                    # 更新现有租户
                    existing_tenant.tenant_name = config.tenant_name
                    existing_tenant.status = config.status
                    existing_tenant.industry = config.industry
                    existing_tenant.company_size = config.company_size
                    existing_tenant.area_id = config.area_id
                    existing_tenant.user_count = config.user_count
                    existing_tenant.expires_at = config.expires_at
                    existing_tenant.feature_flags = config.feature_flags
                    existing_tenant.updated_at = func.now()
                    logger.debug(f"更新租户: {config.tenant_id}")
                else:
                    # 创建新租户
                    new_tenant = TenantOrm(
                        tenant_id=config.tenant_id,
                        tenant_name=config.tenant_name,
                        status=config.status,
                        industry=config.industry,
                        company_size=config.company_size,
                    )
                    session.add(new_tenant)
                    logger.debug(f"创建租户: {config.tenant_id}")
                
                await session.commit()
                return True
                
        except Exception as e:
            logger.error(f"保存租户配置失败: {config.tenant_id}, 错误: {e}")
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
                    update(TenantOrm)
                    .where(TenantOrm.tenant_id == tenant_id)
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
    async def get_all_tenants() -> List[str]:
        """
        获取所有激活状态的租户ID列表
        
        返回:
            List[str]: 激活的租户ID列表
        """
        try:
            async with database_session() as session:
                stmt = select(TenantOrm.tenant_id).where(TenantOrm.status == 1)
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
                    update(TenantOrm)
                    .where(TenantOrm.tenant_id == tenant_id)
                    .values(
                        last_access=access_time,
                        total_requests=TenantOrm.total_requests + 1
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
                stmt = select(TenantOrm.tenant_id)
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
