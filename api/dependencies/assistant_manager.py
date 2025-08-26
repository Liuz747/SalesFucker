"""
租户管理模块

该模块提供租户配置管理、业务设置和访问统计等核心功能，
支持动态配置更新、PostgreSQL持久化存储和高性能缓存机制。

核心功能:
- 租户配置的CRUD操作（PostgreSQL存储）
- 业务设置和功能开关管理
- 访问统计和审计日志
- 租户状态监控
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from contextlib import asynccontextmanager

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.assistant import AssistantConfig, AssistantModel
from infra.db.connection import database_session
from utils import get_component_logger, get_current_datetime, to_isoformat

logger = get_component_logger(__name__, "AssistantManager")


class AssistantManager:
    """
    租户配置管理器
    
    提供租户配置的生命周期管理，包括PostgreSQL持久化存储、
    配置缓存、业务设置、访问统计和安全审计功能。
    """
    
    def __init__(self):
        self._config_cache: Dict[str, AssistantConfig] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=30)  # 缓存30分钟
        self._access_stats: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        
        # 初始化默认租户配置（开发环境）
        self._initialize_default_config()
    
    def _initialize_default_config(self):
        """初始化默认助理配置（用于开发和测试）"""
        default_config = AssistantConfig(
            tenant_id="default",
            tenant_name="默认租户",
            assistant_id="default",
            assistant_name="默认助理",
            is_active=True,
            created_at=get_current_datetime(),
            updated_at=get_current_datetime()
        )
        
        self._config_cache["default"] = default_config
        self._cache_expiry["default"] = get_current_datetime() + timedelta(hours=24)
        
        logger.info("已初始化默认助理配置")
    
    async def get_tenant_config(self, tenant_id: str) -> Optional[AssistantConfig]:
        """
        获取租户配置
        
        参数:
            tenant_id: 租户ID
            
        返回:
            TenantConfig: 租户配置，不存在则返回None
        """
        async with self._lock:
            # 检查缓存
            if tenant_id in self._config_cache:
                cache_expiry = self._cache_expiry.get(tenant_id)
                if cache_expiry and get_current_datetime() < cache_expiry:
                    return self._config_cache[tenant_id]
                else:
                    # 缓存过期，清理
                    self._config_cache.pop(tenant_id, None)
                    self._cache_expiry.pop(tenant_id, None)
            
            # 从PostgreSQL加载配置
            config = await self._load_tenant_config(tenant_id)
            if config:
                # 更新缓存
                self._config_cache[tenant_id] = config
                self._cache_expiry[tenant_id] = (
                    get_current_datetime() + self._cache_ttl
                )
            
            return config
    
    async def _load_tenant_config(self, tenant_id: str) -> Optional[TenantConfig]:
        """
        从PostgreSQL加载租户配置
        
        参数:
            tenant_id: 租户ID
            
        返回:
            TenantConfig: 租户配置，不存在则返回None
        """
        try:
            async with database_session() as session:
                stmt = select(TenantModel).where(TenantModel.tenant_id == tenant_id)
                result = await session.execute(stmt)
                tenant_model = result.scalar_one_or_none()
                
                if tenant_model:
                    return tenant_model.to_business_model()
                
                # 如果是默认租户且数据库中不存在，创建它
                if tenant_id == "default":
                    await self._create_default_tenant_in_db(session)
                    return self._config_cache.get("default")
                
                return None
                
        except Exception as e:
            logger.error(f"从数据库加载租户配置失败: {tenant_id}, 错误: {e}")
            # 返回缓存中的配置（如果有）
            return self._config_cache.get(tenant_id)
    
    async def _create_default_tenant_in_db(self, session: AsyncSession) -> None:
        """在数据库中创建默认租户"""
        try:
            default_config = self._config_cache.get("default")
            if default_config:
                tenant_model = TenantModel.from_business_model(default_config)
                session.add(tenant_model)
                await session.commit()
                logger.info("默认租户已保存到数据库")
        except Exception as e:
            logger.error(f"创建默认租户失败: {e}")
            await session.rollback()
    
    async def save_assistant_config(self, config: AssistantConfig) -> bool:
        """
        保存租户配置到PostgreSQL
        
        参数:
            config: 租户配置
            
        返回:
            bool: 是否保存成功
        """
        try:
            async with self._lock:
                # 更新时间戳
                config.updated_at = get_current_datetime()
                
                # 保存到PostgreSQL
                success = await self._save_assistant_config(config)
                
                if success:
                    # 更新缓存
                    self._config_cache[config.tenant_id] = config
                    self._cache_expiry[config.tenant_id] = (
                        get_current_datetime() + self._cache_ttl
                    )
                    logger.info(f"助理配置已更新: {config.tenant_id}")
                
                return success
                
        except Exception as e:
            logger.error(f"保存助理配置失败: {config.tenant_id}, 错误: {e}")
            return False
    
    async def _save_assistant_config(self, config: AssistantConfig) -> bool:
        """保存配置到PostgreSQL"""
        try:
            async with database_session() as session:
                # 查找现有租户
                stmt = select(AssistantModel).where(AssistantModel.assistant_id == config.assistant_id)
                result = await session.execute(stmt)
                existing_tenant = result.scalar_one_or_none()
                
                if existing_tenant:
                    # 更新现有租户
                    existing_tenant.update_from_business_model(config)
                    await session.commit()
                else:
                    # 创建新租户
                    new_tenant = AssistantModel.from_business_model(config)
                    session.add(new_tenant)
                    await session.commit()
                
                return True
                
        except Exception as e:
            logger.error(f"保存租户到数据库失败: {e}")
            return False
    
    async def record_access(self, tenant_id: str, access_time: datetime) -> None:
        """
        记录租户访问
        
        参数:
            tenant_id: 租户ID
            access_time: 访问时间
        """
        async with self._lock:
            # 内存统计（用于实时监控）
            if tenant_id not in self._access_stats:
                self._access_stats[tenant_id] = {
                    "first_access": access_time,
                    "last_access": access_time,
                    "total_requests": 0,
                    "daily_requests": {},
                    "hourly_requests": {}
                }
            
            stats = self._access_stats[tenant_id]
            stats["last_access"] = access_time
            stats["total_requests"] += 1
            
            # 按日统计
            date_key = to_isoformat(access_time.date())
            stats["daily_requests"][date_key] = (
                stats["daily_requests"].get(date_key, 0) + 1
            )
            
            # 按小时统计
            hour_key = access_time.strftime("%Y-%m-%d %H:00")
            stats["hourly_requests"][hour_key] = (
                stats["hourly_requests"].get(hour_key, 0) + 1
            )
            
            # 清理超过30天的旧统计数据
            cutoff_date = (access_time - timedelta(days=30)).date()
            stats["daily_requests"] = {
                k: v for k, v in stats["daily_requests"].items()
                if to_isoformat(k).date() >= cutoff_date
            }
        
        # 异步更新数据库中的访问记录
        await self._update_tenant_access_in_db(tenant_id, access_time)
    
    async def _update_tenant_access_in_db(self, tenant_id: str, access_time: datetime) -> None:
        """更新数据库中的租户访问记录"""
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
            logger.error(f"更新租户访问记录失败: {e}")
    
    async def get_access_stats(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """获取租户访问统计"""
        return self._access_stats.get(tenant_id)
    
    async def invalidate_cache(self, tenant_id: str) -> None:
        """使指定租户的缓存失效"""
        async with self._lock:
            self._config_cache.pop(tenant_id, None)
            self._cache_expiry.pop(tenant_id, None)
            logger.info(f"已清除租户缓存: {tenant_id}")
    
    async def get_all_tenants(self) -> List[str]:
        """获取所有租户ID列表"""
        try:
            async with database_session() as session:
                stmt = select(TenantModel.tenant_id).where(TenantModel.is_active == True)
                result = await session.execute(stmt)
                tenant_ids = [row[0] for row in result.fetchall()]
                return tenant_ids
        except Exception as e:
            logger.error(f"获取租户列表失败: {e}")
            # 返回缓存中的租户ID
            return list(self._config_cache.keys())
    
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
                stmt = (
                    update(TenantModel)
                    .where(TenantModel.tenant_id == tenant_id)
                    .values(is_active=False, updated_at=get_current_datetime())
                )
                result = await session.execute(stmt)
                await session.commit()
                
                # 从缓存中移除
                await self.invalidate_cache(tenant_id)
                
                return result.rowcount > 0
                
        except Exception as e:
            logger.error(f"删除租户失败: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 测试数据库连接
            from infra.db.connection import test_database_connection
            db_healthy = await test_database_connection()
            
            # 获取租户数量
            tenant_count = len(await self.get_all_tenants())
            
            return {
                "status": "healthy" if db_healthy else "unhealthy",
                "database_connected": db_healthy,
                "cached_tenants": len(self._config_cache),
                "total_tenants": tenant_count,
                "cache_hit_rate": self._calculate_cache_hit_rate(),
                "total_access_records": len(self._access_stats),
                "timestamp": to_isoformat(get_current_datetime())
            }
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": to_isoformat(get_current_datetime())
            }
    
    def _calculate_cache_hit_rate(self) -> float:
        """计算缓存命中率"""
        # TODO: 实现真实的缓存命中率统计
        return 0.95  # 模拟95%命中率


# 全局租户管理器实例
_tenant_manager = None


async def get_tenant_manager() -> TenantManager:
    """获取租户管理器实例（FastAPI依赖）"""
    global _tenant_manager
    if _tenant_manager is None:
        _tenant_manager = TenantManager()
    return _tenant_manager


@asynccontextmanager
async def tenant_manager_context():
    """租户管理器上下文管理器"""
    manager = await get_tenant_manager()
    try:
        yield manager
    finally:
        # 清理资源
        pass