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
from typing import Optional, List, Dict

from sqlalchemy import select, update
from sqlalchemy.sql import func

from models.tenant import TenantOrm
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
    async def query(tenant_id: str) -> Optional[TenantOrm]:
        """
        根据ID获取租户ORM对象
        
        参数:
            tenant_id: 租户ID
            
        返回:
            Optional[TenantOrm]: 租户ORM对象，不存在则返回None
        """
        try:
            async with database_session() as session:
                return await TenantService._get_tenant_by_id(session, tenant_id)

        except Exception as e:
            logger.error(f"获取租户配置失败: {tenant_id}, 错误: {e}")
            raise
    
    @staticmethod
    async def upsert(
        tenant_id: str,
        tenant_name: str,
        status: int,
        industry: int,
        area_id: int,
        creator: int,
        company_size: int,
        feature_flags: Dict[str, bool] = None
    ) -> bool:
        """
        创建或更新租户配置
        
        参数:
            tenant_id: 租户ID
            tenant_name: 租户名称
            status: 状态
            industry: 行业类型
            area_id: 地区ID  
            creator: 创建者ID
            company_size: 公司规模
            feature_flags: 功能开关
            
        返回:
            bool: 是否保存成功
        """
        try:
            async with database_session() as session:
                # 查找现有租户
                existing_tenant = await TenantService._get_tenant_by_id(session, tenant_id)
                
                if existing_tenant:
                    # 更新现有租户
                    existing_tenant.tenant_name = tenant_name
                    existing_tenant.status = status
                    existing_tenant.industry = industry
                    existing_tenant.company_size = company_size
                    existing_tenant.area_id = area_id
                    existing_tenant.feature_flags = feature_flags or {}
                    existing_tenant.updated_at = func.now()
                    logger.debug(f"更新租户: {tenant_id}")
                else:
                    # 创建新租户
                    new_tenant = TenantOrm(
                        tenant_id=tenant_id,
                        tenant_name=tenant_name,
                        status=status,
                        industry=industry,
                        area_id=area_id,
                        creator=creator,
                        company_size=company_size,
                        feature_flags=feature_flags or {},
                    )
                    session.add(new_tenant)
                    logger.debug(f"创建租户: {tenant_id}")
                
                await session.commit()
                return True
                
        except Exception as e:
            logger.error(f"保存租户配置失败: {tenant_id}, 错误: {e}")
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
    async def get_all_tenants(
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[TenantOrm]:
        """
        获取所有租户ORM对象列表
        
        参数:
            status_filter: 状态过滤器 ("active"/"inactive")
            limit: 限制数量
            offset: 偏移量
            
        返回:
            List[TenantOrm]: 租户ORM对象列表
        """
        try:
            async with database_session() as session:
                stmt = select(TenantOrm)
                
                # 应用状态过滤器
                if status_filter == "active":
                    stmt = stmt.where(TenantOrm.status == 1)
                elif status_filter == "inactive":
                    stmt = stmt.where(TenantOrm.status == 0)
                    
                # 应用分页
                stmt = stmt.offset(offset).limit(limit)
                
                result = await session.execute(stmt)
                tenants = result.scalars().all()
                
                logger.debug(f"查询到 {len(tenants)} 个租户")
                return list(tenants)

        except Exception as e:
            logger.error(f"获取租户列表失败: {e}")
            raise
    
    @staticmethod
    async def update_tenant(
        tenant_id: str,
        status: Optional[int] = None,
        feature_flags: Optional[Dict[str, bool]] = None
    ) -> bool:
        """
        更新租户信息
        
        参数:
            tenant_id: 租户ID
            status: 状态 (可选)
            feature_flags: 功能开关 (可选)
            
        返回:
            bool: 是否更新成功
        """
        try:
            async with database_session() as session:
                # 获取现有租户
                existing_tenant = await TenantService._get_tenant_by_id(session, tenant_id)
                if not existing_tenant:
                    return False
                
                # 直接修改ORM对象属性
                if status is not None:
                    existing_tenant.status = status
                if feature_flags is not None:
                    existing_tenant.feature_flags = feature_flags
                
                existing_tenant.updated_at = func.now()
                logger.debug(f"更新租户: {tenant_id}")
                
                await session.commit()
                return True

        except Exception as e:
            logger.error(f"更新租户失败: {tenant_id}, 错误: {e}")
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
