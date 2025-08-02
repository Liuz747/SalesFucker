"""
请求构建器模块

负责构建和验证LLM请求对象。
"""

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..base_provider import LLMRequest, RequestType
from ..intelligent_router import RoutingContext, RoutingStrategy
from src.utils import get_component_logger


class RequestBuilder:
    """LLM请求构建器"""
    
    def __init__(self):
        """初始化请求构建器"""
        self.logger = get_component_logger(__name__, "RequestBuilder")
    
    def build_chat_request(
        self,
        messages: List[Dict[str, Any]],
        agent_type: Optional[str] = None,
        tenant_id: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> LLMRequest:
        """
        构建聊天完成请求
        
        参数:
            messages: 消息列表
            agent_type: 智能体类型
            tenant_id: 租户ID
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大令牌数
            stream: 是否流式响应
            **kwargs: 其他参数
            
        返回:
            LLMRequest: 构建的请求对象
        """
        # 生成请求ID
        request_id = kwargs.get('request_id', str(uuid.uuid4()))
        
        # 构建参数
        parameters = {}
        if temperature is not None:
            parameters['temperature'] = temperature
        if max_tokens is not None:
            parameters['max_tokens'] = max_tokens
        
        # 添加其他参数
        for key, value in kwargs.items():
            if key not in ['request_id'] and value is not None:
                parameters[key] = value
        
        # 构建请求对象
        request = LLMRequest(
            request_id=request_id,
            request_type=RequestType.CHAT_COMPLETION,
            messages=messages,
            model=model or "default",
            parameters=parameters,
            stream=stream,
            metadata={
                'agent_type': agent_type,
                'tenant_id': tenant_id,
                'created_at': datetime.now().isoformat()
            }
        )
        
        self.logger.debug(f"构建聊天请求: {request_id}")
        return request
    
    def build_embedding_request(
        self,
        texts: List[str],
        tenant_id: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> LLMRequest:
        """
        构建嵌入请求
        
        参数:
            texts: 文本列表
            tenant_id: 租户ID
            model: 模型名称
            **kwargs: 其他参数
            
        返回:
            LLMRequest: 构建的请求对象
        """
        request_id = kwargs.get('request_id', str(uuid.uuid4()))
        
        request = LLMRequest(
            request_id=request_id,
            request_type=RequestType.EMBEDDING,
            messages=[{"role": "user", "content": text} for text in texts],
            model=model or "default",
            parameters=kwargs,
            metadata={
                'tenant_id': tenant_id,
                'created_at': datetime.now().isoformat()
            }
        )
        
        self.logger.debug(f"构建嵌入请求: {request_id}")
        return request
    
    def build_routing_context(
        self,
        request: LLMRequest,
        strategy: Optional[RoutingStrategy] = None,
        priority_providers: Optional[List[str]] = None
    ) -> RoutingContext:
        """
        构建路由上下文
        
        参数:
            request: LLM请求
            strategy: 路由策略
            priority_providers: 优先供应商列表
            
        返回:
            RoutingContext: 路由上下文
        """
        tenant_id = request.metadata.get('tenant_id', 'default')
        agent_type = request.metadata.get('agent_type', 'default')
        
        context = RoutingContext(
            request_id=request.request_id,
            tenant_id=tenant_id,
            agent_type=agent_type,
            request_type=request.request_type,
            model_requirements={
                'model': request.model,
                'max_tokens': request.parameters.get('max_tokens'),
                'stream': request.stream
            },
            performance_requirements={
                'max_latency': request.parameters.get('max_latency'),
                'min_quality': request.parameters.get('min_quality')
            },
            cost_constraints={
                'max_cost_per_token': request.parameters.get('max_cost_per_token'),
                'budget_limit': request.parameters.get('budget_limit')
            },
            priority_providers=priority_providers or [],
            strategy=strategy
        )
        
        self.logger.debug(f"构建路由上下文: {request.request_id}")
        return context
    
    def validate_request(self, request: LLMRequest) -> bool:
        """
        验证请求对象
        
        参数:
            request: LLM请求对象
            
        返回:
            bool: 验证是否通过
        """
        # 基础验证
        if not request.request_id:
            raise ValueError("请求ID不能为空")
        
        if not request.messages:
            raise ValueError("消息列表不能为空")
        
        if not request.model:
            raise ValueError("模型名称不能为空")
        
        # 消息格式验证
        for i, message in enumerate(request.messages):
            if not isinstance(message, dict):
                raise ValueError(f"消息 {i} 必须是字典格式")
            
            if 'role' not in message:
                raise ValueError(f"消息 {i} 缺少role字段")
            
            if 'content' not in message:
                raise ValueError(f"消息 {i} 缺少content字段")
            
            if message['role'] not in ['system', 'user', 'assistant']:
                raise ValueError(f"消息 {i} role字段值无效: {message['role']}")
        
        # 参数验证
        if 'temperature' in request.parameters:
            temp = request.parameters['temperature']
            if not isinstance(temp, (int, float)) or temp < 0 or temp > 2:
                raise ValueError("temperature参数必须在0-2之间")
        
        if 'max_tokens' in request.parameters:
            max_tokens = request.parameters['max_tokens']
            if not isinstance(max_tokens, int) or max_tokens <= 0:
                raise ValueError("max_tokens参数必须是正整数")
        
        return True