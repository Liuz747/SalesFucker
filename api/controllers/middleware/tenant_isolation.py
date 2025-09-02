"""
多租户隔离中间件

该中间件确保多租户环境下的数据隔离和访问控制。
防止租户之间的数据泄露和越权访问。

核心功能:
- 租户身份验证
- 资源访问隔离
- 租户上下文管理
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional

from utils import get_component_logger
from services.tenant_service import TenantService

logger = get_component_logger(__name__, "TenantIsolation")


class TenantIsolation(BaseHTTPMiddleware):
    """
    多租户隔离中间件
    
    确保每个租户只能访问自己的资源，防止数据泄露。
    """
    
    def __init__(self, app):
        super().__init__(app)
        
        # 需要租户隔离的路径模式
        self.tenant_required_paths = {
            "/v1/threads",
            "/v1/agents",
            "/v1/chat", 
            "/v1/multimodal"
        }
        
        # 管理员路径（不需要租户隔离）
        self.admin_paths = {
            "/v1/admin",
            "/v1/health"
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
        if not await self._validate_tenant_access(tenant_id):
            return await self._create_tenant_access_denied_response(tenant_id)
        
        # 添加租户上下文到请求
        request.state.tenant_id = tenant_id
        
        # 处理请求
        response = await call_next(request)
        
        # 添加租户相关响应头
        response.headers["X-Tenant-ID"] = tenant_id
        
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
        3. 路径参数: /tenants/{tenant_id}/...
        
        参数:
            request: HTTP请求
            
        返回:
            Optional[str]: 租户ID
        """
        # 方式1: 从Header获取 (推荐)
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return tenant_id
        
        # 方式2: 从Query参数获取
        tenant_id = request.query_params.get("tenant_id")
        if tenant_id:
            return tenant_id
        
        # 方式3: 从路径参数获取
        path_parts = request.url.path.split("/")
        if "tenants" in path_parts:
            try:
                tenant_index = path_parts.index("tenants")
                if tenant_index + 1 < len(path_parts):
                    return path_parts[tenant_index + 1]
            except (ValueError, IndexError):
                pass
        
        return None
    
    async def _validate_tenant_access(self, tenant_id: str) -> bool:
        """
        验证租户访问权限
        
        参数:
            tenant_id: 租户ID
            
        返回:
            bool: 是否有访问权限
        """
        # 基础验证：租户ID格式
        if not tenant_id or len(tenant_id) < 3:
            return False
        
        try:
            # 验证租户是否存在且激活
            tenant = await TenantService.query(tenant_id)
            if not tenant:
                logger.warning(f"租户不存在: {tenant_id}")
                return False
            
            # 检查租户状态是否激活
            if not tenant.status:
                logger.warning(f"租户已禁用: {tenant_id}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"租户验证失败: {tenant_id}, 错误: {e}")
            return False
    
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
                            "Header: X-Tenant-ID (推荐)",
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
                    "message": f"访问拒绝，租户 {tenant_id} 不存在，或已被禁用",
                    "details": {"tenant_id": tenant_id}
                }
            }
        )
