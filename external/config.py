"""
外部API配置模块

该模块定义外部服务的连接配置，包括URL、认证、超时等参数。
支持环境变量和默认配置。
"""

import os
from typing import Optional
from dataclasses import dataclass

from utils import get_component_logger

logger = get_component_logger(__name__, "ExternalConfig")


@dataclass
class ExternalConfig:
    """外部API配置类"""
    
    # 后端API配置
    backend_api_base_url: str
    backend_api_key: Optional[str] = None
    backend_api_timeout: float = 5.0
    backend_api_max_retries: int = 3
    
    # 连接池配置
    connection_pool_size: int = 10
    connection_timeout: float = 30.0
    
    # 重试配置
    retry_backoff_factor: float = 1.0
    retry_max_delay: float = 60.0
    
    # 熔断器配置
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout: int = 60
    
    @classmethod
    def from_env(cls) -> "ExternalConfig":
        """从环境变量创建配置"""
        
        # 必需的配置
        backend_base_url = os.getenv("BACKEND_API_BASE_URL")
        if not backend_base_url:
            logger.warning("BACKEND_API_BASE_URL 未设置，使用默认值")
            backend_base_url = "http://localhost:8001/api/v1"
        
        # 可选配置
        backend_api_key = os.getenv("BACKEND_API_KEY")
        
        # 超时配置
        timeout = float(os.getenv("BACKEND_API_TIMEOUT", "5.0"))
        max_retries = int(os.getenv("BACKEND_API_MAX_RETRIES", "3"))
        
        # 连接池配置
        pool_size = int(os.getenv("CONNECTION_POOL_SIZE", "10"))
        conn_timeout = float(os.getenv("CONNECTION_TIMEOUT", "30.0"))
        
        # 重试配置
        backoff_factor = float(os.getenv("RETRY_BACKOFF_FACTOR", "1.0"))
        max_delay = float(os.getenv("RETRY_MAX_DELAY", "60.0"))
        
        # 熔断器配置
        failure_threshold = int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5"))
        breaker_timeout = int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "60"))
        
        config = cls(
            backend_api_base_url=backend_base_url,
            backend_api_key=backend_api_key,
            backend_api_timeout=timeout,
            backend_api_max_retries=max_retries,
            connection_pool_size=pool_size,
            connection_timeout=conn_timeout,
            retry_backoff_factor=backoff_factor,
            retry_max_delay=max_delay,
            circuit_breaker_failure_threshold=failure_threshold,
            circuit_breaker_timeout=breaker_timeout
        )
        
        logger.info(f"外部API配置已加载: {backend_base_url}")
        return config
    
    @property
    def backend_headers(self) -> dict:
        """获取后端API请求头"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "MAS-AI-System/1.0.0"
        }
        
        if self.backend_api_key:
            headers["Authorization"] = f"Bearer {self.backend_api_key}"
        
        return headers
    
    def get_device_api_url(self, endpoint: str = "") -> str:
        """获取设备API的完整URL"""
        base_url = self.backend_api_base_url.rstrip("/")
        endpoint = endpoint.lstrip("/")
        
        if endpoint:
            return f"{base_url}/devices/{endpoint}"
        return f"{base_url}/devices"
    
    def validate_config(self) -> bool:
        """验证配置是否有效"""
        try:
            # 验证URL格式
            if not self.backend_api_base_url.startswith(("http://", "https://")):
                logger.error("后端API URL格式无效")
                return False
            
            # 验证数值配置
            if self.backend_api_timeout <= 0:
                logger.error("API超时时间必须大于0")
                return False
                
            if self.backend_api_max_retries < 0:
                logger.error("最大重试次数不能小于0")
                return False
            
            logger.info("外部API配置验证通过")
            return True
            
        except Exception as e:
            logger.error(f"配置验证失败: {e}")
            return False


# 全局配置实例
_global_config: Optional[ExternalConfig] = None


def get_external_config() -> ExternalConfig:
    """获取全局外部API配置"""
    global _global_config
    
    if _global_config is None:
        _global_config = ExternalConfig.from_env()
        
        # 验证配置
        if not _global_config.validate_config():
            logger.warning("外部API配置验证失败，使用默认配置")
    
    return _global_config


def set_external_config(config: ExternalConfig):
    """设置全局外部API配置（主要用于测试）"""
    global _global_config
    _global_config = config
    logger.info("外部API配置已更新")