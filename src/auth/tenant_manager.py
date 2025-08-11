"""
租户管理模块

该模块提供租户配置管理、公钥存储、访问记录等核心功能，
支持动态配置更新和高性能缓存机制。

核心功能:
- 租户配置的CRUD操作
- JWT公钥管理和缓存
- 访问统计和审计日志
- 租户状态监控
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List, Any
from contextlib import asynccontextmanager

from .models import TenantConfig, SecurityAuditLog
from src.utils import get_component_logger

logger = get_component_logger(__name__, "TenantManager")


class TenantManager:
    """
    租户配置管理器
    
    提供租户配置的生命周期管理，包括配置缓存、公钥验证、
    访问统计和安全审计功能。
    """
    
    def __init__(self):
        self._config_cache: Dict[str, TenantConfig] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=30)  # 缓存30分钟
        self._access_stats: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        
        # 初始化默认租户配置（开发环境）
        self._initialize_default_config()
    
    def _initialize_default_config(self):
        """初始化默认租户配置（用于开发和测试）"""
        # 注意：这是示例公钥，生产环境应该使用真实的RSA密钥对
        default_public_key = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA1234567890abcdefghijk
lmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmn
opqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqr
stuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqrstuv
wxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqrstuvwxyz
ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqrstuvwxyzABCD
EFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqrstuvwxyzABCDEFGH
IJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKL
MNOPQRSTUVWXYZ1234567890abcdefghijklmnopqrstuvwxyzwibaqab
-----END PUBLIC KEY-----"""
        
        default_config = TenantConfig(
            tenant_id="default",
            tenant_name="默认租户",
            jwt_public_key=default_public_key,
            jwt_algorithm="RS256",
            jwt_issuer="mas-cosmetic-system",
            jwt_audience="mas-api",
            token_expiry_hours=24,
            max_token_age_minutes=5,
            allowed_origins=["*"],
            enable_audit_logging=True,
            enable_rate_limiting=True,
            enable_device_validation=False,  # 开发环境关闭设备验证
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        self._config_cache["default"] = default_config
        self._cache_expiry["default"] = datetime.now(timezone.utc) + timedelta(hours=24)
        
        logger.info("已初始化默认租户配置")
    
    async def get_tenant_config(self, tenant_id: str) -> Optional[TenantConfig]:
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
                if cache_expiry and datetime.now(timezone.utc) < cache_expiry:
                    return self._config_cache[tenant_id]
                else:
                    # 缓存过期，清理
                    self._config_cache.pop(tenant_id, None)
                    self._cache_expiry.pop(tenant_id, None)
            
            # 从存储加载配置
            config = await self._load_tenant_config(tenant_id)
            if config:
                # 更新缓存
                self._config_cache[tenant_id] = config
                self._cache_expiry[tenant_id] = (
                    datetime.now(timezone.utc) + self._cache_ttl
                )
            
            return config
    
    async def _load_tenant_config(self, tenant_id: str) -> Optional[TenantConfig]:
        """
        从持久化存储加载租户配置
        
        当前为模拟实现，生产环境应集成真实的数据库系统
        """
        # TODO: 集成数据库查询
        # 这里为演示目的使用内存存储
        
        if tenant_id == "default":
            return self._config_cache.get("default")
        
        # 模拟其他租户配置
        if tenant_id in ["tenant1", "tenant2", "cosmetic_brand_a"]:
            sample_config = TenantConfig(
                tenant_id=tenant_id,
                tenant_name=f"租户 {tenant_id}",
                jwt_public_key=self._config_cache["default"].jwt_public_key,  # 示例使用相同密钥
                jwt_algorithm="RS256",
                jwt_issuer="mas-cosmetic-system",
                jwt_audience="mas-api",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            return sample_config
        
        return None
    
    async def save_tenant_config(self, config: TenantConfig) -> bool:
        """
        保存租户配置
        
        参数:
            config: 租户配置
            
        返回:
            bool: 是否保存成功
        """
        try:
            async with self._lock:
                # 更新时间戳
                config.updated_at = datetime.now(timezone.utc)
                
                # 保存到持久化存储
                success = await self._save_tenant_config(config)
                
                if success:
                    # 更新缓存
                    self._config_cache[config.tenant_id] = config
                    self._cache_expiry[config.tenant_id] = (
                        datetime.now(timezone.utc) + self._cache_ttl
                    )
                    logger.info(f"租户配置已更新: {config.tenant_id}")
                
                return success
                
        except Exception as e:
            logger.error(f"保存租户配置失败: {config.tenant_id}, 错误: {e}")
            return False
    
    async def _save_tenant_config(self, config: TenantConfig) -> bool:
        """保存配置到持久化存储"""
        # TODO: 实现数据库保存逻辑
        return True
    
    async def record_access(self, tenant_id: str, access_time: datetime) -> None:
        """
        记录租户访问
        
        参数:
            tenant_id: 租户ID
            access_time: 访问时间
        """
        async with self._lock:
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
            date_key = access_time.date().isoformat()
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
                if datetime.fromisoformat(k).date() >= cutoff_date
            }
    
    async def get_access_stats(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """获取租户访问统计"""
        return self._access_stats.get(tenant_id)
    
    async def log_security_event(
        self,
        tenant_id: str,
        event_type: str,
        client_ip: str,
        details: Dict[str, Any],
        risk_level: str = "low"
    ) -> None:
        """
        记录安全事件
        
        参数:
            tenant_id: 租户ID
            event_type: 事件类型
            client_ip: 客户端IP
            details: 事件详情
            risk_level: 风险级别
        """
        try:
            audit_log = SecurityAuditLog(
                log_id=f"{tenant_id}_{int(datetime.now().timestamp())}_{event_type}",
                tenant_id=tenant_id,
                event_type=event_type,
                event_timestamp=datetime.now(timezone.utc),
                client_ip=client_ip,
                user_agent=details.get("user_agent"),
                request_id=details.get("request_id"),
                jwt_subject=details.get("jwt_subject"),
                jwt_issuer=details.get("jwt_issuer"),
                authentication_result=details.get("auth_result", "unknown"),
                details=details,
                risk_level=risk_level
            )
            
            # TODO: 保存到审计日志存储
            logger.info(
                f"安全事件记录 - 租户: {tenant_id}, 事件: {event_type}, "
                f"风险: {risk_level}, IP: {client_ip}"
            )
            
        except Exception as e:
            logger.error(f"记录安全事件失败: {e}")
    
    async def invalidate_cache(self, tenant_id: str) -> None:
        """使指定租户的缓存失效"""
        async with self._lock:
            self._config_cache.pop(tenant_id, None)
            self._cache_expiry.pop(tenant_id, None)
            logger.info(f"已清除租户缓存: {tenant_id}")
    
    async def get_all_tenants(self) -> List[str]:
        """获取所有租户ID列表"""
        # TODO: 从数据库查询所有租户
        return list(self._config_cache.keys())
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": "healthy",
            "cached_tenants": len(self._config_cache),
            "cache_hit_rate": self._calculate_cache_hit_rate(),
            "total_access_records": len(self._access_stats),
            "timestamp": datetime.now(timezone.utc).isoformat()
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