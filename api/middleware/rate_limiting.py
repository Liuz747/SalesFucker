"""
速率限制中间件

该中间件实现API的速率限制功能，防止滥用和过载。
支持基于IP、用户、租户的多维度限制策略。

核心功能:
- 基于滑动窗口的速率限制
- 多维度限制策略
- 动态限制调整
- 限制状态记录
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Any, Optional, Tuple
import time
import logging
from collections import defaultdict, deque

from utils import get_component_logger

logger = get_component_logger(__name__, "RateLimiting")


class RateLimiting(BaseHTTPMiddleware):
    """
    速率限制中间件
    
    使用滑动窗口算法实现多维度的速率限制。
    """
    
    def __init__(self, app):
        super().__init__(app)
        
        # 默认限制配置
        self.default_limits = {
            "ip": {"requests": 100, "window": 60},      # 每IP每分钟100次请求
            "tenant": {"requests": 1000, "window": 60}, # 每租户每分钟1000次请求
            "global": {"requests": 10000, "window": 60} # 全局每分钟10000次请求
        }
        
        # 特殊路径的限制配置
        self.path_limits = {
            "/api/v1/multimodal": {"requests": 20, "window": 60},     # 多模态处理限制更严格
            "/api/v1/llm-management": {"requests": 50, "window": 60}  # LLM管理接口限制
        }
        
        # 请求记录（生产环境应使用Redis）
        self.request_records = {
            "ip": defaultdict(deque),
            "tenant": defaultdict(deque),
            "global": deque()
        }
        
        # 白名单IP（可从配置加载）
        self.whitelist_ips = set()
        
        # 限制豁免路径
        self.exempt_paths = {
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json"
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
        # 检查是否豁免速率限制
        if self._is_exempt(request):
            return await call_next(request)
        
        # 获取客户端IP
        client_ip = self._get_client_ip(request)
        
        # 检查IP白名单
        if client_ip in self.whitelist_ips:
            return await call_next(request)
        
        # 执行速率限制检查
        rate_limit_result = await self._check_rate_limits(request, client_ip)
        
        if not rate_limit_result["allowed"]:
            return await self._create_rate_limit_response(rate_limit_result)
        
        # 记录请求
        await self._record_request(request, client_ip)
        
        # 处理请求
        response = await call_next(request)
        
        # 添加速率限制相关响应头
        self._add_rate_limit_headers(response, rate_limit_result)
        
        return response
    
    def _is_exempt(self, request: Request) -> bool:
        """
        检查请求是否豁免速率限制
        
        参数:
            request: HTTP请求
            
        返回:
            bool: 是否豁免
        """
        path = request.url.path
        return any(path.startswith(exempt_path) for exempt_path in self.exempt_paths)
    
    def _get_client_ip(self, request: Request) -> str:
        """
        获取客户端IP地址
        
        参数:
            request: HTTP请求
            
        返回:
            str: 客户端IP地址
        """
        # 优先从反向代理头获取真实IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # 取第一个IP（原始客户端IP）
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # 最后使用连接IP
        return request.client.host if request.client else "unknown"
    
    async def _check_rate_limits(self, request: Request, client_ip: str) -> Dict[str, Any]:
        """
        检查速率限制
        
        参数:
            request: HTTP请求
            client_ip: 客户端IP
            
        返回:
            Dict[str, Any]: 限制检查结果
        """
        current_time = time.time()
        path = request.url.path
        
        # 获取租户ID（如果有）
        tenant_id = request.headers.get("X-Tenant-ID")
        
        # 检查各个维度的限制
        checks = []
        
        # 1. IP维度检查
        ip_result = self._check_dimension_limit(
            "ip", client_ip, current_time, self.default_limits["ip"]
        )
        checks.append(("ip", ip_result))
        
        # 2. 租户维度检查
        if tenant_id:
            tenant_result = self._check_dimension_limit(
                "tenant", tenant_id, current_time, self.default_limits["tenant"]
            )
            checks.append(("tenant", tenant_result))
        
        # 3. 全局维度检查
        global_result = self._check_dimension_limit(
            "global", "global", current_time, self.default_limits["global"]
        )
        checks.append(("global", global_result))
        
        # 4. 路径特定限制检查
        path_limit = self._get_path_limit(path)
        if path_limit:
            path_result = self._check_dimension_limit(
                "path", f"{client_ip}:{path}", current_time, path_limit
            )
            checks.append(("path", path_result))
        
        # 找出最严格的限制
        most_restrictive = min(checks, key=lambda x: x[1]["remaining"])
        dimension, result = most_restrictive
        
        return {
            "allowed": result["allowed"],
            "dimension": dimension,
            "current": result["current"],
            "limit": result["limit"],
            "remaining": result["remaining"],
            "reset_time": result["reset_time"],
            "all_checks": dict(checks)
        }
    
    def _check_dimension_limit(
        self, 
        dimension: str, 
        key: str, 
        current_time: float,
        limit_config: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        检查特定维度的限制
        
        参数:
            dimension: 限制维度
            key: 限制键
            current_time: 当前时间
            limit_config: 限制配置
            
        返回:
            Dict[str, Any]: 检查结果
        """
        window_size = limit_config["window"]
        max_requests = limit_config["requests"]
        
        # 获取该维度的请求记录
        if dimension == "global":
            requests = self.request_records["global"]
        else:
            requests = self.request_records[dimension][key]
        
        # 清理过期请求
        cutoff_time = current_time - window_size
        while requests and requests[0] < cutoff_time:
            requests.popleft()
        
        current_count = len(requests)
        remaining = max(0, max_requests - current_count)
        allowed = current_count < max_requests
        
        # 计算重置时间
        reset_time = current_time + window_size if requests else current_time
        
        return {
            "allowed": allowed,
            "current": current_count,
            "limit": max_requests,
            "remaining": remaining,
            "reset_time": reset_time
        }
    
    def _get_path_limit(self, path: str) -> Optional[Dict[str, int]]:
        """
        获取路径特定的限制配置
        
        参数:
            path: 请求路径
            
        返回:
            Optional[Dict[str, int]]: 限制配置
        """
        for path_pattern, limit_config in self.path_limits.items():
            if path.startswith(path_pattern):
                return limit_config
        return None
    
    async def _record_request(self, request: Request, client_ip: str):
        """
        记录请求到各个维度
        
        参数:
            request: HTTP请求
            client_ip: 客户端IP
        """
        current_time = time.time()
        path = request.url.path
        tenant_id = request.headers.get("X-Tenant-ID")
        
        # 记录IP维度
        self.request_records["ip"][client_ip].append(current_time)
        
        # 记录租户维度
        if tenant_id:
            self.request_records["tenant"][tenant_id].append(current_time)
        
        # 记录全局维度
        self.request_records["global"].append(current_time)
        
        # 记录路径特定维度
        path_limit = self._get_path_limit(path)
        if path_limit:
            path_key = f"{client_ip}:{path}"
            if "path" not in self.request_records:
                self.request_records["path"] = defaultdict(deque)
            self.request_records["path"][path_key].append(current_time)
    
    def _add_rate_limit_headers(self, response: Response, rate_limit_result: Dict[str, Any]):
        """
        添加速率限制相关的响应头
        
        参数:
            response: HTTP响应
            rate_limit_result: 速率限制结果
        """
        response.headers["X-RateLimit-Limit"] = str(rate_limit_result["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_result["remaining"])
        response.headers["X-RateLimit-Reset"] = str(int(rate_limit_result["reset_time"]))
        response.headers["X-RateLimit-Dimension"] = rate_limit_result["dimension"]
    
    async def _create_rate_limit_response(self, rate_limit_result: Dict[str, Any]) -> JSONResponse:
        """
        创建速率限制响应
        
        参数:
            rate_limit_result: 速率限制结果
            
        返回:
            JSONResponse: 限制响应
        """
        retry_after = int(rate_limit_result["reset_time"] - time.time())
        
        response = JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": f"请求频率超限（{rate_limit_result['dimension']}维度）",
                    "details": {
                        "dimension": rate_limit_result["dimension"],
                        "current": rate_limit_result["current"],
                        "limit": rate_limit_result["limit"],
                        "remaining": rate_limit_result["remaining"],
                        "retry_after": retry_after
                    }
                }
            }
        )
        
        # 添加标准的限制头
        response.headers["X-RateLimit-Limit"] = str(rate_limit_result["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_result["remaining"])
        response.headers["X-RateLimit-Reset"] = str(int(rate_limit_result["reset_time"]))
        response.headers["Retry-After"] = str(retry_after)
        
        return response