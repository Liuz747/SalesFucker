"""
基础HTTP客户端模块（简化版）

该模块提供外部API调用的基础HTTP客户端，包括认证、重试、
熔断器等功能。所有外部API客户端都应继承此基类。

注意：当前为简化实现，生产环境建议安装aiohttp获得完整功能。
"""

import asyncio
from typing import Dict, Any, Optional
import json
import time
from datetime import datetime

from src.utils import get_component_logger, ErrorHandler


# 自定义异常
class ExternalAPIError(Exception):
    """外部API调用异常"""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class CircuitBreakerError(ExternalAPIError):
    """熔断器开启异常"""
    pass


class CircuitBreaker:
    """简单熔断器实现"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self) -> bool:
        """检查是否可以执行请求"""
        if self.state == "CLOSED":
            return True
        
        if self.state == "OPEN":
            # 检查是否可以转为半开状态
            if (datetime.now() - self.last_failure_time).seconds > self.timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        
        # HALF_OPEN状态允许一次尝试
        return True
    
    def record_success(self):
        """记录成功调用"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        """记录失败调用"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class BaseClient:
    """
    基础HTTP客户端（简化版）
    
    提供外部API调用的基础功能，包括认证、重试、熔断器等。
    """
    
    def __init__(self, base_url: str, timeout: float = 5.0, max_retries: int = 3):
        """
        初始化基础客户端
        
        参数:
            base_url: API基础URL
            timeout: 请求超时时间
            max_retries: 最大重试次数
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        
        self.logger = get_component_logger(__name__, "BaseClient")
        self.error_handler = ErrorHandler("external_client")
        
        # 熔断器
        self.circuit_breaker = CircuitBreaker()
        
        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "circuit_breaker_trips": 0
        }
        
        self.logger.info(f"基础客户端初始化完成: {base_url}")
    
    async def close(self):
        """关闭HTTP会话"""
        self.logger.debug("客户端会话已关闭")
    
    def _get_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "MAS-AI-System/1.0.0"
        }
        
        if additional_headers:
            headers.update(additional_headers)
        
        return headers
    
    def _build_url(self, endpoint: str) -> str:
        """构建完整URL"""
        endpoint = endpoint.lstrip("/")
        return f"{self.base_url}/{endpoint}"
    
    async def _mock_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        模拟HTTP请求（开发环境使用）
        
        注意：这是简化实现，生产环境应使用真实HTTP客户端
        """
        
        # 检查熔断器
        if not self.circuit_breaker.can_execute():
            self.stats["circuit_breaker_trips"] += 1
            raise CircuitBreakerError("熔断器开启，请求被阻止")
        
        self.stats["total_requests"] += 1
        start_time = time.time()
        
        try:
            self.logger.debug(f"模拟请求: {method} {url}")
            
            # 模拟网络延迟
            await asyncio.sleep(0.1)
            
            # 模拟响应（根据URL路径返回不同的模拟数据）
            if "devices" in url:
                if method == "GET":
                    # 模拟设备查询成功
                    response_data = {
                        "device_id": "mock_device_001",
                        "device_name": "模拟设备",
                        "tenant_id": "default",
                        "status": "active",
                        "capabilities": ["camera", "microphone", "speaker"],
                        "is_online": True
                    }
                else:
                    response_data = {"success": True, "message": "操作成功"}
            elif "health" in url:
                response_data = {"status": "ok", "timestamp": datetime.now().isoformat()}
            else:
                response_data = {"message": "模拟响应", "timestamp": datetime.now().isoformat()}
            
            response_time = time.time() - start_time
            
            self.logger.debug(
                f"模拟请求成功: {method} {url}, "
                f"响应时间: {response_time:.3f}s"
            )
            
            self.circuit_breaker.record_success()
            self.stats["successful_requests"] += 1
            
            return response_data
            
        except Exception as e:
            self.circuit_breaker.record_failure()
            self.stats["failed_requests"] += 1
            
            self.logger.error(f"模拟请求失败: {e}")
            raise ExternalAPIError(f"请求失败: {str(e)}")
    
    async def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        带重试的HTTP请求
        
        参数:
            method: HTTP方法
            endpoint: API端点
            data: 请求体数据
            params: 查询参数
            headers: 额外请求头
            
        返回:
            响应数据
        """
        url = self._build_url(endpoint)
        request_headers = self._get_headers(headers)
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await self._mock_request(
                    method, url, request_headers, data, params
                )
                
            except ExternalAPIError as e:
                last_exception = e
                
                # 如果是客户端错误（4xx），不重试
                if e.status_code and 400 <= e.status_code < 500:
                    break
                
                # 如果还有重试机会，等待后重试
                if attempt < self.max_retries:
                    backoff_delay = (2 ** attempt) * 1.0  # 指数退避
                    self.logger.warning(
                        f"请求失败，第{attempt + 1}次尝试，{backoff_delay}秒后重试: {e}"
                    )
                    await asyncio.sleep(backoff_delay)
                else:
                    self.logger.error(f"请求失败，已达到最大重试次数: {e}")
        
        # 抛出最后一次异常
        raise last_exception
    
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """GET请求"""
        return await self._request_with_retry("GET", endpoint, params=params, headers=headers)
    
    async def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """POST请求"""
        return await self._request_with_retry("POST", endpoint, data=data, params=params, headers=headers)
    
    async def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """PUT请求"""
        return await self._request_with_retry("PUT", endpoint, data=data, params=params, headers=headers)
    
    async def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """DELETE请求"""
        return await self._request_with_retry("DELETE", endpoint, params=params, headers=headers)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取客户端统计信息"""
        success_rate = 0.0
        if self.stats["total_requests"] > 0:
            success_rate = self.stats["successful_requests"] / self.stats["total_requests"]
        
        return {
            **self.stats,
            "success_rate": success_rate,
            "circuit_breaker_state": self.circuit_breaker.state
        }
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            await self.get("health")
            return True
        except Exception as e:
            self.logger.warning(f"健康检查失败: {e}")
            return False