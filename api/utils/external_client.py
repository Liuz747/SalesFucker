"""
外部HTTP请求工具模块

提供简单的HTTP客户端功能，用于与外部服务通信。
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional

from .logger_utils import get_component_logger

logger = get_component_logger(__name__, "ExternalClient")


class ExternalClient:
    """外部客户端"""
    
    def __init__(self, base_url: Optional[str] = None, config: Optional[Dict] = None):
        self.base_url = base_url.rstrip("/") if base_url else None
        self.config = config or {}

    async def make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 10.0,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        发送HTTP请求
        
        参数:
            method: HTTP方法 (GET, POST, PUT, DELETE)
            endpoint: 请求URL
            data: 请求体数据
            params: 查询参数
            headers: 请求头
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
        
        返回:
            响应数据字典
        """
        # 构建完整URL
        if endpoint.startswith(("http://", "https://")):
            url = endpoint
        elif self.base_url:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
        else:
            raise ValueError("需要提供完整的请求URL")

        # 准备请求头
        default_headers = {"User-Agent": "MAS-AI-System/1.0.0", **(headers or {}), **self.config}
        
        for attempt in range(max_retries + 1):
            try:
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=timeout),
                    headers=default_headers
                    ) as session:
                    
                    async with session.request(
                        method,
                        url,
                        params=params,
                        json=data,
                        ) as response:
                        # 解析响应
                        response.raise_for_status()
                        if response.content_type == 'application/json':
                            response_data = await response.json()
                        else:
                            response_data = await response.text()
                        
                        logger.debug(f"请求成功: {method} {url}")
                        return response_data
            
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                # 如果还有重试机会，等待后重试
                if attempt < max_retries:
                    delay = 0.5 * (2 ** attempt)  # 指数退避
                    logger.warning(f"请求失败，{delay}秒后重试: {e}")
                    await asyncio.sleep(delay)
            raise e