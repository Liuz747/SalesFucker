"""
上下文保持模块

负责在故障转移过程中保持对话上下文的完整性。
"""

import copy
from typing import List, Dict, Any, Optional

from .models import FailureContext, FailoverConfig
from ..base_provider import LLMRequest, BaseProvider
from ..intelligent_router import RoutingContext
from src.utils import get_component_logger


class ContextPreserver:
    """上下文保持器"""
    
    def __init__(self, config: FailoverConfig):
        """
        初始化上下文保持器
        
        参数:
            config: 故障转移配置
        """
        self.config = config
        self.logger = get_component_logger(__name__, "ContextPreserver")
    
    def preserve_context_for_failover(
        self,
        original_request: LLMRequest,
        failure_context: FailureContext,
        target_provider: BaseProvider
    ) -> LLMRequest:
        """
        为故障转移保持上下文
        
        参数:
            original_request: 原始请求
            failure_context: 故障上下文
            target_provider: 目标供应商
            
        返回:
            LLMRequest: 调整后的请求
        """
        if not self.config.context_preservation_enabled:
            return original_request
        
        # 深拷贝原始请求以避免修改
        adapted_request = copy.deepcopy(original_request)
        
        # 根据目标供应商调整请求格式
        adapted_request = self._adapt_request_for_provider(adapted_request, target_provider)
        
        # 添加故障转移上下文信息
        adapted_request = self._add_failover_metadata(adapted_request, failure_context)
        
        # 调整消息格式以确保兼容性
        adapted_request = self._ensure_message_compatibility(adapted_request, target_provider)
        
        self.logger.debug(f"上下文保持完成，转移到 {target_provider.provider_type}")
        return adapted_request
    
    def _adapt_request_for_provider(
        self, 
        request: LLMRequest, 
        target_provider: BaseProvider
    ) -> LLMRequest:
        """
        根据目标供应商调整请求
        
        参数:
            request: 原始请求
            target_provider: 目标供应商
            
        返回:
            LLMRequest: 调整后的请求
        """
        # 获取目标供应商支持的模型
        available_models = target_provider.get_available_models()
        
        # 模型映射和选择逻辑
        if request.model not in available_models:
            # 尝试映射到兼容模型
            mapped_model = self._map_to_compatible_model(request.model, available_models)
            if mapped_model:
                request.model = mapped_model
                self.logger.info(f"模型映射: {request.model} -> {mapped_model}")
            else:
                # 使用默认模型
                request.model = available_models[0] if available_models else request.model
                self.logger.warning(f"使用默认模型: {request.model}")
        
        # 调整供应商特定参数
        request = self._adjust_provider_specific_params(request, target_provider)
        
        return request
    
    def _map_to_compatible_model(self, original_model: str, available_models: List[str]) -> Optional[str]:
        """
        映射到兼容模型
        
        参数:
            original_model: 原始模型名称
            available_models: 可用模型列表
            
        返回:
            Optional[str]: 兼容模型名称
        """
        # 模型兼容性映射表
        compatibility_map = {
            # OpenAI模型映射
            "gpt-4": ["gpt-4", "claude-3-sonnet-20240229", "gemini-pro"],
            "gpt-3.5-turbo": ["gpt-3.5-turbo", "claude-3-haiku-20240307", "gemini-pro"],
            
            # Anthropic模型映射
            "claude-3-sonnet-20240229": ["claude-3-sonnet-20240229", "gpt-4", "gemini-pro"],
            "claude-3-haiku-20240307": ["claude-3-haiku-20240307", "gpt-3.5-turbo", "gemini-pro"],
            
            # Google模型映射
            "gemini-pro": ["gemini-pro", "gpt-4", "claude-3-sonnet-20240229"],
            
            # DeepSeek模型映射
            "deepseek-chat": ["deepseek-chat", "gpt-3.5-turbo", "claude-3-haiku-20240307"]
        }
        
        compatible_models = compatibility_map.get(original_model, [])
        
        # 查找第一个可用的兼容模型
        for model in compatible_models:
            if model in available_models:
                return model
        
        return None
    
    def _adjust_provider_specific_params(
        self, 
        request: LLMRequest, 
        target_provider: BaseProvider
    ) -> LLMRequest:
        """
        调整供应商特定参数
        
        参数:
            request: 请求对象
            target_provider: 目标供应商
            
        返回:
            LLMRequest: 调整后的请求
        """
        provider_type = target_provider.provider_type
        
        # 参数兼容性调整
        if hasattr(request, 'parameters') and request.parameters:
            adjusted_params = copy.deepcopy(request.parameters)
            
            # 根据供应商类型调整参数
            if provider_type.value == "anthropic":
                # Anthropic特定调整
                if 'top_p' in adjusted_params and adjusted_params['top_p'] == 1.0:
                    adjusted_params['top_p'] = 0.99  # Anthropic不支持top_p=1.0
            
            elif provider_type.value == "gemini":
                # Gemini特定调整
                if 'frequency_penalty' in adjusted_params:
                    del adjusted_params['frequency_penalty']  # Gemini不支持frequency_penalty
                if 'presence_penalty' in adjusted_params:
                    del adjusted_params['presence_penalty']  # Gemini不支持presence_penalty
            
            request.parameters = adjusted_params
        
        return request
    
    def _add_failover_metadata(
        self, 
        request: LLMRequest, 
        failure_context: FailureContext
    ) -> LLMRequest:
        """
        添加故障转移元数据
        
        参数:
            request: 请求对象
            failure_context: 故障上下文
            
        返回:
            LLMRequest: 添加元数据的请求
        """
        if not hasattr(request, 'metadata'):
            request.metadata = {}
        
        request.metadata.update({
            'failover_context': {
                'original_provider': failure_context.provider_type.value,
                'failure_type': failure_context.failure_type.value,
                'attempt_count': failure_context.attempt_count,
                'request_id': failure_context.request_id
            }
        })
        
        return request
    
    def _ensure_message_compatibility(
        self, 
        request: LLMRequest, 
        target_provider: BaseProvider
    ) -> LLMRequest:
        """
        确保消息格式兼容性
        
        参数:
            request: 请求对象
            target_provider: 目标供应商
            
        返回:
            LLMRequest: 兼容的请求
        """
        if not hasattr(request, 'messages') or not request.messages:
            return request
        
        provider_type = target_provider.provider_type
        
        # 确保消息格式符合目标供应商要求
        for message in request.messages:
            if isinstance(message, dict):
                # 标准化消息角色
                if 'role' in message:
                    role = message['role'].lower()
                    if role not in ['system', 'user', 'assistant']:
                        message['role'] = 'user'  # 默认为用户消息
                
                # 供应商特定的消息格式调整
                if provider_type.value == "anthropic":
                    # Anthropic特定调整
                    if message.get('role') == 'system' and len(request.messages) > 1:
                        # Anthropic系统消息处理
                        pass
                
                elif provider_type.value == "gemini":
                    # Gemini特定调整
                    if message.get('role') == 'system':
                        # Gemini将系统消息转换为用户消息
                        message['role'] = 'user'
                        message['content'] = f"System: {message['content']}"
        
        return request