"""
多租户隔离中间件

该中间件确保多租户环境下的数据隔离和访问控制。
防止租户之间的数据泄露和越权访问。

核心功能:
- 租户身份验证
- 资源访问隔离
- 租户配额管理
- 访问日志记录
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Any, Optional, Set

from datetime import datetime, timedelta

from utils import get_component_logger

logger = get_component_logger(__name__, "TenantIsolation")


class TenantIsolation(BaseHTTPMiddleware):
    """
    多租户隔离中间件
    
    确保每个租户只能访问自己的资源，防止数据泄露。
    """
    
    def __init__(self, app):
        super().__init__(app)
        
        # 租户配额限制（可从配置文件加载）
        self.tenant_quotas = {
            "default": {
                "requests_per_hour": 1000,
                "max_agents": 10,
                "max_conversations": 100
            }
        }
        
        # 租户请求计数（生产环境应使用Redis）
        self.tenant_request_counts = {}
        
        # 需要租户隔离的路径模式
        self.tenant_required_paths = {
            "/api/v1/agents",
            "/api/v1/conversations", 
            "/api/v1/multimodal"
        }
        
        # 管理员路径（不需要租户隔离）
        self.admin_paths = {
            "/api/v1/llm-management/admin",
            "/api/v1/health"
        }
    
    async def dispatch(self, request: Request, call_next):
        """
        中间件处理逻辑
        
        参数:
            request: HTTP请求
            call_next: 下一个中间件或处理器
            
        返回:
            Response: HTTP响应
        """
        # 检查是否需要租户隔离
        if not self._requires_tenant_isolation(request.url.path):
            return await call_next(request)
        
        # 获取租户ID
        tenant_id = self._extract_tenant_id(request)
        if not tenant_id:
            return await self._create_tenant_required_response()
        
        # 验证租户权限
        if not await self._validate_tenant_access(tenant_id, request):
            return await self._create_tenant_access_denied_response(tenant_id)
        
        # 检查租户配额
        quota_result = await self._check_tenant_quota(tenant_id, request)
        if not quota_result["allowed"]:
            return await self._create_quota_exceeded_response(tenant_id, quota_result)
        
        # 记录租户请求
        await self._record_tenant_request(tenant_id, request)
        
        # 添加租户上下文到请求
        request.state.tenant_id = tenant_id
        request.state.tenant_context = await self._get_tenant_context(tenant_id)
        
        # 处理请求
        response = await call_next(request)
        
        # 添加租户相关响应头
        response.headers["X-Tenant-ID"] = tenant_id
        response.headers["X-Tenant-Quota-Remaining"] = str(
            quota_result.get("remaining", 0)
        )
        
        return response
    
    def _requires_tenant_isolation(self, path: str) -> bool:
        """
        检查路径是否需要租户隔离
        
        参数:
            path: 请求路径
            
        返回:
            bool: 是否需要租户隔离
        """
        # 管理员路径不需要租户隔离
        for admin_path in self.admin_paths:
            if path.startswith(admin_path):
                return False
        
        # 检查是否为需要租户隔离的路径
        for tenant_path in self.tenant_required_paths:
            if path.startswith(tenant_path):
                return True
        
        return False
    
    def _extract_tenant_id(self, request: Request) -> Optional[str]:
        """
        从请求中提取租户ID
        
        支持多种提取方式：
        1. Header: X-Tenant-ID
        2. Query参数: tenant_id
        3. 路径参数: /tenant/{tenant_id}/...
        
        参数:
            request: HTTP请求
            
        返回:
            Optional[str]: 租户ID
        """
        # 方式1: 从Header获取
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return tenant_id
        
        # 方式2: 从Query参数获取
        tenant_id = request.query_params.get("tenant_id")
        if tenant_id:
            return tenant_id
        
        # 方式3: 从路径参数获取
        path_parts = request.url.path.split("/")
        if "tenant" in path_parts:
            try:
                tenant_index = path_parts.index("tenant")
                if tenant_index + 1 < len(path_parts):
                    return path_parts[tenant_index + 1]
            except (ValueError, IndexError):
                pass
        
        return None
    
    async def _validate_tenant_access(self, tenant_id: str, request: Request) -> bool:
        """
        验证租户访问权限
        
        参数:
            tenant_id: 租户ID
            request: HTTP请求
            
        返回:
            bool: 是否有访问权限
        """
        # 基础验证：租户ID格式
        if not tenant_id or len(tenant_id) < 3:
            return False
        
        # TODO: 添加更多验证逻辑
        # - 租户是否存在
        # - 租户是否激活
        # - 租户权限检查
        
        return True
    
    async def _check_tenant_quota(self, tenant_id: str, request: Request) -> Dict[str, Any]:
        """
        检查租户配额
        
        参数:
            tenant_id: 租户ID
            request: HTTP请求
            
        返回:
            Dict[str, Any]: 配额检查结果
        """
        # 获取租户配额配置
        quota_config = self.tenant_quotas.get(tenant_id, self.tenant_quotas["default"])
        
        # 获取当前小时的请求计数
        current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
        tenant_key = f"{tenant_id}:{current_hour.isoformat()}"
        
        current_count = self.tenant_request_counts.get(tenant_key, 0)
        max_requests = quota_config["requests_per_hour"]
        
        # 检查是否超过配额
        if current_count >= max_requests:
            return {
                "allowed": False,
                "reason": "hourly_quota_exceeded",
                "current": current_count,
                "limit": max_requests,
                "remaining": 0
            }
        
        return {
            "allowed": True,
            "current": current_count,
            "limit": max_requests,
            "remaining": max_requests - current_count
        }
    
    async def _record_tenant_request(self, tenant_id: str, request: Request):
        """
        记录租户请求
        
        参数:
            tenant_id: 租户ID
            request: HTTP请求
        """
        # 记录请求计数
        current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
        tenant_key = f"{tenant_id}:{current_hour.isoformat()}"
        
        self.tenant_request_counts[tenant_key] = (
            self.tenant_request_counts.get(tenant_key, 0) + 1
        )
        
        # 记录访问日志
        logger.info(
            f"租户请求 - 租户: {tenant_id}, 路径: {request.url.path}, "
            f"方法: {request.method}, IP: {request.client.host if request.client else 'unknown'}"
        )
        
        # 清理过期的计数记录
        self._cleanup_expired_counts()
    
    def _cleanup_expired_counts(self):
        """清理过期的请求计数记录"""
        current_time = datetime.now()
        expired_keys = []
        
        for key in self.tenant_request_counts.keys():
            try:
                # 提取时间戳
                timestamp_str = key.split(":", 1)[1]
                timestamp = datetime.fromisoformat(timestamp_str)
                
                # 如果记录超过2小时，标记为过期
                if current_time - timestamp > timedelta(hours=2):
                    expired_keys.append(key)
            except (ValueError, IndexError):
                # 无法解析的key也删除
                expired_keys.append(key)
        
        # 删除过期记录
        for key in expired_keys:
            del self.tenant_request_counts[key]
    
    async def _get_tenant_context(self, tenant_id: str) -> Dict[str, Any]:
        """
        获取租户上下文信息
        
        参数:
            tenant_id: 租户ID
            
        返回:
            Dict[str, Any]: 租户上下文
        """
        return {
            "tenant_id": tenant_id,
            "quota_config": self.tenant_quotas.get(tenant_id, self.tenant_quotas["default"]),
            "access_time": datetime.now().isoformat()
        }
    
    async def _create_tenant_required_response(self) -> JSONResponse:
        """创建租户ID必需响应"""
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "TENANT_ID_REQUIRED",
                    "message": "请求必须包含租户ID",
                    "details": {
                        "methods": [
                            "Header: X-Tenant-ID",
                            "Query参数: tenant_id",
                            "路径参数: /tenant/{tenant_id}/..."
                        ]
                    }
                }
            }
        )
    
    async def _create_tenant_access_denied_response(self, tenant_id: str) -> JSONResponse:
        """创建租户访问拒绝响应"""
        return JSONResponse(
            status_code=403,
            content={
                "error": {
                    "code": "TENANT_ACCESS_DENIED",
                    "message": f"租户 {tenant_id} 访问被拒绝",
                    "details": {"tenant_id": tenant_id}
                }
            }
        )
    
    async def _create_quota_exceeded_response(
        self, 
        tenant_id: str, 
        quota_result: Dict[str, Any]
    ) -> JSONResponse:
        """创建配额超出响应"""
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "TENANT_QUOTA_EXCEEDED",
                    "message": f"租户 {tenant_id} 请求配额已超出",
                    "details": {
                        "tenant_id": tenant_id,
                        "current": quota_result["current"],
                        "limit": quota_result["limit"],
                        "reason": quota_result["reason"]
                    }
                }
            }
        )