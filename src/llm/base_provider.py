"""
LLM供应商基类模块

该模块定义了所有LLM供应商的抽象基类，提供统一的接口和通用功能。
所有具体的供应商实现都应该继承此基类。

核心功能:
- 统一的LLM请求/响应接口
- 标准化错误处理和重试机制
- 成本追踪和使用统计
- 中文语言优化支持
- 流式响应处理
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, AsyncGenerator, Union
from datetime import datetime
from pydantic import BaseModel, Field
import asyncio
import time
from enum import Enum

from .provider_config import (
    ProviderType, 
    ProviderConfig, 
    ModelConfig,
    ProviderHealth
)
from src.utils import get_component_logger, ErrorHandler


class RequestType(str, Enum):
    """请求类型枚举"""
    TEXT_COMPLETION = "text_completion"
    CHAT_COMPLETION = "chat_completion"
    EMBEDDING = "embedding"
    MULTIMODAL = "multimodal"


class LLMRequest(BaseModel):
    """LLM请求数据模型"""
    request_id: str = Field(..., description="请求唯一ID")
    request_type: RequestType = Field(..., description="请求类型")
    messages: List[Dict[str, Any]] = Field(..., description="消息列表")
    model: Optional[str] = Field(None, description="指定模型")
    temperature: Optional[float] = Field(None, description="温度参数")
    max_tokens: Optional[int] = Field(None, description="最大令牌数")
    stream: bool = Field(False, description="是否流式响应")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tenant_id: Optional[str] = Field(None, description="租户ID")
    agent_type: Optional[str] = Field(None, description="智能体类型")


class LLMResponse(BaseModel):
    """LLM响应数据模型"""
    request_id: str = Field(..., description="请求ID")
    provider_type: ProviderType = Field(..., description="供应商类型")
    model: str = Field(..., description="使用的模型")
    content: str = Field(..., description="响应内容")
    usage_tokens: int = Field(0, description="使用的令牌数")
    cost: float = Field(0.0, description="请求成本")
    response_time: float = Field(0.0, description="响应时间(秒)")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


class ProviderError(Exception):
    """供应商错误基类"""
    def __init__(self, message: str, provider_type: ProviderType, error_code: str = None):
        self.message = message
        self.provider_type = provider_type
        self.error_code = error_code
        super().__init__(message)


class RateLimitError(ProviderError):
    """速率限制错误"""
    pass


class AuthenticationError(ProviderError):
    """认证错误"""
    pass


class ModelNotFoundError(ProviderError):
    """模型未找到错误"""
    pass


class BaseProvider(ABC):
    """
    LLM供应商抽象基类
    
    定义所有LLM供应商必须实现的基础接口和通用功能。
    提供统一的请求/响应处理、错误处理和性能监控。
    
    子类必须实现:
        _make_request: 具体的API请求实现
        _handle_streaming: 流式响应处理
        get_available_models: 获取可用模型列表
    """
    
    def __init__(self, config: ProviderConfig):
        """
        初始化供应商基础配置
        
        参数:
            config: 供应商配置对象
        """
        self.config = config
        self.provider_type = config.provider_type
        self.logger = get_component_logger(__name__, str(self.provider_type))
        self.error_handler = ErrorHandler(f"provider_{self.provider_type}")
        
        # 性能统计
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "avg_response_time": 0.0,
            "last_request_time": None
        }
        
        # 健康状态
        self.health = ProviderHealth(provider_type=self.provider_type)
        
        # 速率限制追踪
        self.rate_limiter = {
            "requests_per_minute": [],
            "tokens_per_minute": []
        }
        
        self.logger.info(f"{self.provider_type} 供应商初始化完成")
    
    @abstractmethod
    async def _make_request(self, request: LLMRequest) -> LLMResponse:
        """
        执行具体的API请求 (抽象方法)
        
        每个供应商子类必须实现此方法来定义具体的API调用逻辑。
        
        参数:
            request: LLM请求对象
            
        返回:
            LLMResponse: API响应对象
            
        异常:
            ProviderError: 供应商相关错误
        """
        pass
    
    @abstractmethod
    async def _handle_streaming(
        self, 
        request: LLMRequest
    ) -> AsyncGenerator[str, None]:
        """
        处理流式响应 (抽象方法)
        
        子类必须实现此方法来处理流式API响应。
        
        参数:
            request: LLM请求对象
            
        生成:
            str: 流式响应内容片段
        """
        pass
    
    @abstractmethod
    async def get_available_models(self) -> List[ModelConfig]:
        """
        获取可用模型列表 (抽象方法)
        
        返回:
            List[ModelConfig]: 可用模型配置列表
        """
        pass
    
    async def process_request(self, request: LLMRequest) -> Union[LLMResponse, AsyncGenerator[str, None]]:
        """
        处理LLM请求的主要接口
        
        提供统一的请求处理流程，包括验证、执行、错误处理和统计更新。
        
        参数:
            request: LLM请求对象
            
        返回:
            Union[LLMResponse, AsyncGenerator]: 普通响应或流式响应
            
        异常:
            ProviderError: 处理过程中的各种错误
        """
        start_time = time.time()
        
        try:
            # 请求验证
            await self._validate_request(request)
            
            # 速率限制检查
            await self._check_rate_limits()
            
            # 处理请求
            if request.stream:
                return self._handle_streaming(request)
            else:
                response = await self._make_request(request)
                
                # 更新统计信息
                processing_time = time.time() - start_time
                await self._update_stats(response, processing_time)
                
                return response
                
        except Exception as e:
            # 错误处理和统计更新
            processing_time = time.time() - start_time
            await self._handle_request_error(e, request, processing_time)
            raise
    
    async def _validate_request(self, request: LLMRequest):
        """验证请求参数"""
        if not request.messages:
            raise ProviderError("消息列表不能为空", self.provider_type, "EMPTY_MESSAGES")
        
        # 检查模型可用性
        if request.model:
            available_models = await self.get_available_models()
            model_names = [model.model_name for model in available_models]
            if request.model not in model_names:
                raise ModelNotFoundError(
                    f"模型 {request.model} 不可用", 
                    self.provider_type, 
                    "MODEL_NOT_FOUND"
                )
    
    async def _check_rate_limits(self):
        """检查速率限制"""
        current_time = time.time()
        minute_ago = current_time - 60
        
        # 清理过期的记录
        self.rate_limiter["requests_per_minute"] = [
            t for t in self.rate_limiter["requests_per_minute"] 
            if t > minute_ago
        ]
        
        # 检查请求限制
        if len(self.rate_limiter["requests_per_minute"]) >= self.config.rate_limit_rpm:
            raise RateLimitError(
                f"已达到每分钟请求限制: {self.config.rate_limit_rpm}",
                self.provider_type,
                "RATE_LIMIT_EXCEEDED"
            )
        
        # 记录当前请求
        self.rate_limiter["requests_per_minute"].append(current_time)
    
    async def _update_stats(self, response: LLMResponse, processing_time: float):
        """更新统计信息"""
        self.stats["total_requests"] += 1
        self.stats["successful_requests"] += 1
        self.stats["total_tokens"] += response.usage_tokens
        self.stats["total_cost"] += response.cost
        self.stats["last_request_time"] = datetime.now()
        
        # 更新平均响应时间
        total_requests = self.stats["total_requests"]
        current_avg = self.stats["avg_response_time"]
        self.stats["avg_response_time"] = (
            (current_avg * (total_requests - 1) + processing_time) / total_requests
        )
        
        # 更新健康状态
        self.health.avg_response_time = self.stats["avg_response_time"] * 1000  # 转换为毫秒
        self.health.last_check = datetime.now()
        self.health.consecutive_failures = 0
        
        self.logger.debug(f"请求处理完成: {response.request_id}, 耗时: {processing_time:.3f}s")
    
    async def _handle_request_error(self, error: Exception, request: LLMRequest, processing_time: float):
        """处理请求错误"""
        self.stats["total_requests"] += 1
        self.stats["failed_requests"] += 1
        
        # 更新健康状态
        self.health.consecutive_failures += 1
        self.health.error_rate = self.stats["failed_requests"] / self.stats["total_requests"]
        
        # 检查是否需要标记为不健康
        if self.health.consecutive_failures >= 5 or self.health.error_rate > 0.5:
            self.health.is_healthy = False
            
        error_context = {
            "provider_type": self.provider_type,
            "request_id": request.request_id,
            "processing_time": processing_time,
            "error_type": type(error).__name__
        }
        
        self.error_handler.handle_error(error, error_context)
        self.logger.error(f"请求处理失败: {request.request_id}, 错误: {str(error)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "provider_type": self.provider_type,
            "stats": self.stats.copy(),
            "health": self.health.dict(),
            "config": {
                "is_enabled": self.config.is_enabled,
                "priority": self.config.priority,
                "rate_limit_rpm": self.config.rate_limit_rpm
            }
        }
    
    def reset_health(self):
        """重置健康状态"""
        self.health.is_healthy = True
        self.health.consecutive_failures = 0
        self.health.error_rate = 0.0
        self.logger.info(f"{self.provider_type} 健康状态已重置")
    
    async def health_check(self) -> bool:
        """执行健康检查"""
        try:
            # 创建简单的测试请求
            test_request = LLMRequest(
                request_id=f"health_check_{int(time.time())}",
                request_type=RequestType.TEXT_COMPLETION,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=1
            )
            
            start_time = time.time()
            await self._make_request(test_request)
            response_time = (time.time() - start_time) * 1000
            
            # 更新健康状态
            self.health.is_healthy = True
            self.health.avg_response_time = response_time
            self.health.last_check = datetime.now()
            
            return True
            
        except Exception as e:
            self.health.is_healthy = False
            self.logger.warning(f"健康检查失败: {str(e)}")
            return False