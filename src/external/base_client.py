"""
基础HTTP客户端模块

该模块提供外部API调用的基础HTTP客户端，包括认证、重试、
熔断器等功能。所有外部API客户端都应继承此基类。

核心功能:
- HTTP请求封装
- 认证处理
- 自动重试机制
- 熔断器保护
- 错误处理
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime
import json
import time

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
    基础HTTP客户端
    
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
        
        # 会话对象
        self._session: Optional[aiohttp.ClientSession] = None
        
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
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建HTTP会话"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            connector = aiohttp.TCPConnector(
                limit=100,  # 连接池大小
                limit_per_host=30,  # 每个主机的连接数限制
                enable_cleanup_closed=True
            )
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={"User-Agent": "MAS-AI-System/1.0.0"}
            )
        return self._session
    
    async def close(self):
        """关闭HTTP会话"""
        if self._session and not self._session.closed:
            await self._session.close()
            self.logger.debug("HTTP会话已关闭")
    
    def _get_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if additional_headers:
            headers.update(additional_headers)
        
        return headers
    
    def _build_url(self, endpoint: str) -> str:
        """构建完整URL"""
        endpoint = endpoint.lstrip("/")
        return f"{self.base_url}/{endpoint}"
    
    async def _make_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """执行HTTP请求"""
        
        # 检查熔断器
        if not self.circuit_breaker.can_execute():
            self.stats["circuit_breaker_trips"] += 1
            raise CircuitBreakerError("熔断器开启，请求被阻止")
        
        session = await self._get_session()
        
        # 准备请求参数
        request_kwargs = {
            "headers": headers,
            "params": params
        }
        
        if data:
            request_kwargs["json"] = data
        
        self.stats["total_requests"] += 1
        start_time = time.time()
        
        try:
            self.logger.debug(f"发送请求: {method} {url}")
            
            async with session.request(method, url, **request_kwargs) as response:
                response_time = time.time() - start_time
                
                # 读取响应内容
                try:
                    if response.content_type == 'application/json':
                        response_data = await response.json()
                    else:
                        text_content = await response.text()
                        try:
                            response_data = json.loads(text_content)
                        except json.JSONDecodeError:
                            response_data = {"text": text_content}
                except Exception as e:
                    self.logger.warning(f"解析响应内容失败: {e}")
                    response_data = {"error": "无法解析响应内容"}
                
                # 检查HTTP状态码
                if response.status >= 400:
                    self.logger.warning(
                        f"请求失败: {method} {url}, 状态码: {response.status}, "
                        f"响应时间: {response_time:.3f}s"
                    )
                    
                    self.circuit_breaker.record_failure()
                    self.stats["failed_requests"] += 1
                    
                    # 根据状态码确定错误信息
                    if response.status == 404:
                        error_message = "资源不存在"
                    elif response.status == 401:
                        error_message = "认证失败"
                    elif response.status == 403:
                        error_message = "权限不足"
                    elif response.status == 429:
                        error_message = "请求频率过高"
                    elif response.status >= 500:
                        error_message = "服务器内部错误"
                    else:
                        error_message = response_data.get('message', f'HTTP {response.status}')
                    
                    raise ExternalAPIError(
                        error_message,
                        status_code=response.status,
                        response_data=response_data
                    )
                
                # 成功响应
                self.logger.debug(
                    f"请求成功: {method} {url}, 状态码: {response.status}, "
                    f"响应时间: {response_time:.3f}s"
                )
                
                self.circuit_breaker.record_success()
                self.stats["successful_requests"] += 1
                
                return response_data
                
        except aiohttp.ClientError as e:
            self.circuit_breaker.record_failure()
            self.stats["failed_requests"] += 1
            
            self.logger.error(f"网络请求失败: {e}")
            raise ExternalAPIError(f"网络请求失败: {str(e)}")
        
        except asyncio.TimeoutError:
            self.circuit_breaker.record_failure()
            self.stats["failed_requests"] += 1
            
            self.logger.error(f"请求超时: {url}")
            raise ExternalAPIError(f"请求超时: {url}")
    
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
                return await self._make_request(
                    method, url, request_headers, data, params
                )
                
            except ExternalAPIError as e:
                last_exception = e
                
                # 如果是客户端错误（4xx），不重试
                if e.status_code and 400 <= e.status_code < 500:
                    # 特殊情况：429（频率限制）可以重试
                    if e.status_code != 429:
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
            "circuit_breaker_state": self.circuit_breaker.state,
            "base_url": self.base_url
        }
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            await self.get("health")
            return True
        except Exception as e:
            self.logger.warning(f"健康检查失败: {e}")
            return False
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()