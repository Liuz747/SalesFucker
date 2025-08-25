"""
LLM供应商基类

定义所有LLM供应商的统一接口。
所有具体供应商实现都必须继承此基类。
"""

from abc import ABC, abstractmethod
from typing import List, Dict
from infra.runtimes.entities import LLMRequest, LLMResponse, Provider

class BaseProvider(ABC):
    """LLM供应商抽象基类"""
    
    def __init__(self, provider: Provider):
        """
        初始化供应商
        
        参数:
            provider: 供应商配置
        """
        self.provider = provider
        # TODO: 简单的内存存储，生产环境应使用Redis/Elasticsearch
        self.conversation_history: Dict[str, List[Dict[str, str]]] = {}

    @abstractmethod
    async def completions(self, request: LLMRequest) -> LLMResponse:
        """
        发送聊天请求 (抽象方法)
        
        参数:
            request: LLM请求
            
        返回:
            LLMResponse: LLM响应
        """
        pass
    
    def _build_conversation_context(self, request: LLMRequest) -> List[Dict[str, str]]:
        """
        构建对话上下文，包含历史消息
        
        参数:
            request: LLM请求
            
        返回:
            包含历史消息的完整对话上下文
        """
        if not request.chat_id:
            return request.messages
        
        # 获取历史对话
        history = self.conversation_history.get(request.chat_id, [])
        
        # 合并历史消息和当前消息
        full_context = history + request.messages
        
        return full_context
    
    def _save_conversation_turn(self, request: LLMRequest, response: LLMResponse):
        """
        保存一轮对话到历史记录
        
        参数:
            request: LLM请求
            response: LLM响应
        """
        if not request.chat_id:
            return
        
        if request.chat_id not in self.conversation_history:
            self.conversation_history[request.chat_id] = []
        
        # 添加用户消息和助手回复
        self.conversation_history[request.chat_id].extend([
            *request.messages,  # 用户的新消息
            {"role": "assistant", "content": response.content}  # 助手回复
        ])

