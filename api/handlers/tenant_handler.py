"""
租户管理服务

该模块提供租户配置管理、业务设置和访问统计等核心功能。

核心功能:
- 租户配置的CRUD操作
- 业务设置和功能开关管理
- 访问统计和审计日志
- 租户状态监控
- API请求处理和响应转换
"""

from datetime import datetime
from typing import Dict, Any, Optional, List

from models.tenant import (
    TenantModel,
    TenantSyncRequest,
    TenantUpdateRequest,
    TenantStatusResponse,
    TenantListResponse,
)
from services.tenant_service import TenantService
from utils import get_component_logger, get_current_datetime, to_isoformat

logger = get_component_logger(__name__, "TenantHandler")


class TenantHandler:
    
    def __init__(self):
        self._access_stats: Dict[str, Dict[str, Any]] = {}

    async def sync_tenant(self, request: TenantSyncRequest) -> None:
        """同步租户配置"""
        try:
            exist = await self.get_tenant_config(request.tenant_id)
            if not exist:
                cfg = TenantModel(
                    tenant_id=request.tenant_id,
                    tenant_name=request.tenant_name,
                    status=request.status,
                    industry=request.industry,
                    area_id=request.area_id,
                    creator=request.creator,
                    company_size=request.company_size,
                )
            else:
                cfg = exist
                cfg.status = request.status
                cfg.tenant_name = request.tenant_name
                cfg.industry = request.industry
                cfg.area_id = request.area_id
                cfg.company_size = request.company_size

            # Update features if provided
            if request.features:
                cfg.feature_flags = {feature: True for feature in request.features}

            status = await self.save_tenant_config(cfg)
            if not status:
                raise ValueError(f"Failed to save tenant configuration for {cfg.tenant_id}")
        except Exception as e:
            logger.error(f"租户同步失败: {request.tenant_id}, 错误: {e}")
            raise

    async def get_tenant_status(self, tenant_id: str) -> Optional[TenantStatusResponse]:
        """获取租户状态"""
        cfg = await self.get_tenant_config(tenant_id)
        if not cfg:
            return None
        return TenantStatusResponse(
            tenant_id=cfg.tenant_id,
            tenant_name=cfg.tenant_name,
            status=cfg.status,
            updated_at=cfg.updated_at,
            last_access=cfg.last_access,
        )

    async def update_tenant(self, tenant_id: str, request: TenantUpdateRequest) -> Dict[str, Any]:
        """更新租户配置"""
        cfg = await self.get_tenant_config(tenant_id)
        if not cfg:
            raise ValueError("Tenant not found")
        
        if request.status is not None:
            cfg.status = request.status
        
        if request.features:
            cfg.feature_flags = {feature: True for feature in request.features}
            
        status = await self.save_tenant_config(cfg)
        return {
            "status": "updated" if status else "failed",
            "features": request.features or [],
        }

    async def delete_tenant(self, tenant_id: str, force: bool = False) -> Dict[str, Any]:
        """删除租户"""
        try:
            flag = await TenantService.delete(tenant_id)
            return {"status": "deleted" if flag else "failed", "data_purged": force}
        except Exception as e:
            logger.error(f"删除租户失败: {tenant_id}, 错误: {e}")
            return {"status": "failed", "error": str(e)}

    async def list_tenants(
        self, status_filter: Optional[str], limit: int, offset: int
    ) -> TenantListResponse:
        
        """获取租户列表"""
        try:
            ids = await TenantService.get_all_tenants()
            items: List[Dict[str, Any]] = []
            for tid in ids:
                cfg = await self.get_tenant_config(tid)
                if not cfg:
                    continue
                if status_filter == "active" and not cfg.status:
                    continue
                if status_filter == "inactive" and cfg.status:
                    continue
                items.append(
                    {
                        "tenant_id": cfg.tenant_id,
                        "tenant_name": cfg.tenant_name,
                        "status": cfg.status,
                        "updated_at": cfg.updated_at,
                        "features_enabled": list(cfg.feature_flags.keys()) if cfg.feature_flags else [],
                    }
                )
            total = len(items)
            return TenantListResponse(total=total, tenants=items[offset : offset + limit])
        except Exception as e:
            logger.error(f"获取租户列表失败: {e}")
            return TenantListResponse(total=0, tenants=[])


    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 使用仓库层进行健康检查
            db_stats = await TenantService.health_check()
            
            return {
                "status": "healthy" if db_stats["database_connected"] else "unhealthy",
                "database_connected": db_stats["database_connected"],
                "total_tenants": db_stats["total_tenants"],
                "active_tenants": db_stats["active_tenants"],
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
    
    async def get_tenant_config(self, tenant_id: str) -> Optional[TenantModel]:
        """
        获取租户配置
        
        参数:
            tenant_id: 租户ID
            
        返回:
            TenantModel: 租户配置，不存在则返回None
            
        异常:
            数据库连接异常将被传播，业务异常返回None
        """
        try:
            return await TenantService.query(tenant_id)
        except Exception as e:
            logger.error(f"获取租户配置失败: {tenant_id}, 错误: {e}")
            raise
    
    async def save_tenant_config(self, config: TenantModel) -> bool:
        """
        保存租户配置到PostgreSQL
        
        参数:
            config: 租户配置
            
        返回:
            bool: 是否保存成功
        """
        # 保存到数据库 - 让异常向上传播
        flag = await TenantService.save(config)
        
        if flag:
            logger.info(f"租户配置已更新: {config.tenant_id}")
        else:
            logger.error(f"保存租户配置失败: {config.tenant_id}")
        
        return flag
    
    async def record_access(self, tenant_id: str, access_time: datetime) -> None:
        """
        记录租户访问
        
        参数:
            tenant_id: 租户ID
            access_time: 访问时间
        """
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
        from datetime import timedelta
        cutoff_date = (access_time - timedelta(days=30)).date()
        stats["daily_requests"] = {
            k: v for k, v in stats["daily_requests"].items()
            if to_isoformat(k).date() >= cutoff_date
        }
        
        # 异步更新数据库中的访问记录
        try:
            await TenantService.update_access_stats(tenant_id, access_time)
        except Exception as e:
            logger.error(f"更新租户访问记录失败: {tenant_id}, 错误: {e}")
    
    async def get_access_stats(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """获取租户访问统计"""
        return self._access_stats.get(tenant_id)