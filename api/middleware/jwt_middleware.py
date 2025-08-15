"""
JWT认证中间件

轻量级中间件，用于验证后端服务JWT令牌。
自动为除认证路径外的所有端点验证服务认证。
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, List, Optional

from infra.auth import get_service_context, ServiceContext
from utils import get_component_logger

logger = get_component_logger(__name__, "JWTMiddleware")


class JWTMiddleware(BaseHTTPMiddleware):
    """
    JWT认证中间件
    
    验证后端服务JWT令牌并在request.state中填充服务上下文。
    """
    
    def __init__(
        self,
        app,
        exclude_paths: Optional[List[str]] = None,
        exclude_prefixes: Optional[List[str]] = None
    ):
        """
        初始化JWT中间件
        
        参数:
            app: FastAPI应用实例
            exclude_paths: 需要排除JWT验证的具体路径
            exclude_prefixes: 需要排除JWT验证的路径前缀
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths
        self.exclude_prefixes = exclude_prefixes
    
    def should_exclude_path(self, path: str) -> bool:
        """检查路径是否应排除JWT验证"""
        # 精确路径匹配
        if self.exclude_paths and path in self.exclude_paths:
            return True
            
        # 前缀匹配
        if self.exclude_prefixes:
            for prefix in self.exclude_prefixes:
                if path.startswith(prefix):
                    return True
                
        return False
    
    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        """
        处理请求的JWT认证
        
        参数:
            request: FastAPI请求对象
            call_next: 链中的下一个中间件/端点
            
        返回:
            来自下一个处理器的响应或JWT错误响应
        """
        try:
            # 跳过排除路径的JWT验证
            if self.should_exclude_path(request.url.path):
                logger.debug(f"跳过JWT验证路径: {request.url.path}")
                return await call_next(request)
            
            # 从Authorization头中提取JWT令牌
            authorization = request.headers.get("Authorization")
            if not authorization:
                logger.warning(f"缺少Authorization头: {request.url.path}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "authentication_required",
                        "message": "缺少Authorization头",
                        "details": "请在Authorization头中提供有效的JWT令牌"
                    }
                )
            
            # 验证Bearer令牌格式
            try:
                scheme, _ = authorization.split(" ", 1)
                if scheme.lower() != "bearer":
                    raise ValueError("无效的认证方案")
            except ValueError:
                logger.warning(f"无效的Authorization头格式: {request.url.path}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "invalid_token_format",
                        "message": "无效的Authorization头格式",
                        "details": "请使用 'Bearer <token>' 格式"
                    }
                )
            
            # 验证JWT令牌
            try:
                service_context: ServiceContext = await get_service_context(authorization)
                
                logger.debug(f"JWT验证成功: {service_context.sub}")
                
                # 在请求状态中存储服务上下文
                request.state.service_context = service_context
                request.state.authenticated = True
                
            except HTTPException as http_exc:
                logger.warning(f"服务JWT验证失败: {http_exc.detail}")
                return JSONResponse(
                    status_code=http_exc.status_code,
                    content=http_exc.detail if isinstance(http_exc.detail, dict) else {
                        "error": "SERVICE_AUTHENTICATION_FAILED",
                        "message": str(http_exc.detail)
                    }
                )
            except Exception as jwt_error:
                logger.error(f"JWT验证失败: {jwt_error}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "invalid_token",
                        "message": "JWT令牌验证失败",
                        "details": str(jwt_error)
                    }
                )
            
            # 使用已认证的上下文处理请求
            response = await call_next(request)
            
            # 添加安全头到响应
            # response.headers["X-Service-Authenticated"] = "true"
            response.headers["X-Auth-Method"] = "JWT"
            
            return response
            
        except Exception as e:
            logger.error(f"JWT中间件错误: {e}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "authentication_error",
                    "message": "认证处理失败",
                    "details": "请重试或联系技术支持"
                }
            )