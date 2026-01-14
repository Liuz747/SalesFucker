"""
简单路由器

提供基本的LLM请求路由功能，支持中文内容检测、视觉内容路由等。
"""

from typing import List, Dict, Any

from .entities import ProviderType, LLMRequest

class SimpleRouter:
    """简单路由器"""

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化路由器
        
        参数:
            config: 路由配置字典
        """
        self.config = config or {}
        self.stats: Dict[ProviderType, Dict[str, Any]] = {}

    def route(self, request: LLMRequest, available_providers: List[ProviderType]) -> ProviderType:
        """
        简单路由逻辑
        
        参数:
            request: LLM请求
            available_providers: 可用供应商列表
            
        返回:
            ProviderType: 选择的供应商类型
        """

        # 规则0: 基于模型的路由 (最高优先级)
        if request.model:
            if "claude" in request.model.lower() and ProviderType.ANTHROPIC in available_providers:
                return ProviderType.ANTHROPIC
            elif "gpt" in request.model.lower() and ProviderType.OPENAI in available_providers:
                return ProviderType.OPENAI

        # 规则1: 中文内容 -> 偏好DeepSeek/OpenAI
        if self._is_chinese_content(request):
            return ProviderType.OPENAI

        # 规则2: 视觉内容 -> OpenAI/Anthropic
        if self._has_vision_content(request):
            return ProviderType.ANTHROPIC

        # 规则3: 默认使用第一个可用供应商
        return available_providers[0] if available_providers else ProviderType.OPENAI

    def _is_chinese_content(self, request: LLMRequest) -> bool:
        """
        简单中文检测
        
        参数:
            request: LLM请求
            
        返回:
            bool: 是否包含中文内容
        """
        text = " ".join([msg.get("content", "") for msg in request.messages])
        return any('\u4e00' <= char <= '\u9fff' for char in text)

    def _has_vision_content(self, request: LLMRequest) -> bool:
        """
        检查是否包含图像内容
        
        参数:
            request: LLM请求
            
        返回:
            bool: 是否包含图像内容
        """
        for msg in request.messages:
            if isinstance(msg.get("content"), list):
                return True
        return False


