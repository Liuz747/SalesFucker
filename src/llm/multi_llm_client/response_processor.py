"""
响应处理器模块

负责处理和格式化LLM响应。
"""

from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime

from ..base_provider import LLMResponse
from src.utils import get_component_logger


class ResponseProcessor:
    """LLM响应处理器"""
    
    def __init__(self):
        """初始化响应处理器"""
        self.logger = get_component_logger(__name__, "ResponseProcessor")
    
    def process_chat_response(
        self, 
        response: LLMResponse,
        format_type: str = "standard"
    ) -> Dict[str, Any]:
        """
        处理聊天完成响应
        
        参数:
            response: LLM响应对象
            format_type: 格式类型
            
        返回:
            Dict[str, Any]: 格式化的响应
        """
        if format_type == "openai":
            return self._format_openai_style(response)
        elif format_type == "anthropic":
            return self._format_anthropic_style(response)
        else:
            return self._format_standard_style(response)
    
    def _format_standard_style(self, response: LLMResponse) -> Dict[str, Any]:
        """标准格式化"""
        return {
            "id": response.request_id,
            "content": response.content,
            "model": response.model,
            "provider": response.provider_type.value if response.provider_type else None,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0
            },
            "metadata": {
                "response_time": response.response_time,
                "created_at": response.created_at.isoformat() if response.created_at else None,
                "finish_reason": response.finish_reason,
                **response.metadata
            }
        }
    
    def _format_openai_style(self, response: LLMResponse) -> Dict[str, Any]:
        """OpenAI风格格式化"""
        return {
            "id": response.request_id,
            "object": "chat.completion",
            "created": int(response.created_at.timestamp()) if response.created_at else None,
            "model": response.model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response.content
                },
                "finish_reason": response.finish_reason or "stop"
            }],
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0
            }
        }
    
    def _format_anthropic_style(self, response: LLMResponse) -> Dict[str, Any]:
        """Anthropic风格格式化"""
        return {
            "id": response.request_id,
            "type": "message",
            "role": "assistant",
            "content": [{
                "type": "text",
                "text": response.content
            }],
            "model": response.model,
            "stop_reason": response.finish_reason or "end_turn",
            "usage": {
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0
            }
        }
    
    def process_embedding_response(self, response: LLMResponse) -> Dict[str, Any]:
        """
        处理嵌入响应
        
        参数:
            response: LLM响应对象
            
        返回:
            Dict[str, Any]: 格式化的嵌入响应
        """
        embeddings = response.metadata.get('embeddings', [])
        
        return {
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "index": i,
                    "embedding": embedding
                }
                for i, embedding in enumerate(embeddings)
            ],
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0
            }
        }
    
    async def process_streaming_response(
        self, 
        response_stream: AsyncGenerator[LLMResponse, None],
        format_type: str = "standard"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理流式响应
        
        参数:
            response_stream: 响应流
            format_type: 格式类型
            
        生成:
            Dict[str, Any]: 格式化的流式响应块
        """
        async for chunk in response_stream:
            try:
                if format_type == "openai":
                    yield self._format_streaming_openai_style(chunk)
                elif format_type == "anthropic":
                    yield self._format_streaming_anthropic_style(chunk)
                else:
                    yield self._format_streaming_standard_style(chunk)
            except Exception as e:
                self.logger.error(f"流式响应处理失败: {str(e)}")
                break
    
    def _format_streaming_standard_style(self, chunk: LLMResponse) -> Dict[str, Any]:
        """标准流式格式化"""
        return {
            "id": chunk.request_id,
            "delta": {
                "content": chunk.content
            },
            "model": chunk.model,
            "provider": chunk.provider_type.value if chunk.provider_type else None,
            "finished": chunk.finish_reason is not None
        }
    
    def _format_streaming_openai_style(self, chunk: LLMResponse) -> Dict[str, Any]:
        """OpenAI流式格式化"""
        return {
            "id": chunk.request_id,
            "object": "chat.completion.chunk",
            "created": int(chunk.created_at.timestamp()) if chunk.created_at else None,
            "model": chunk.model,
            "choices": [{
                "index": 0,
                "delta": {
                    "content": chunk.content
                } if chunk.content else {},
                "finish_reason": chunk.finish_reason
            }]
        }
    
    def _format_streaming_anthropic_style(self, chunk: LLMResponse) -> Dict[str, Any]:
        """Anthropic流式格式化"""
        if chunk.content:
            return {
                "type": "content_block_delta",
                "index": 0,
                "delta": {
                    "type": "text_delta",
                    "text": chunk.content
                }
            }
        elif chunk.finish_reason:
            return {
                "type": "message_stop"
            }
        else:
            return {
                "type": "ping"
            }
    
    def extract_response_metadata(self, response: LLMResponse) -> Dict[str, Any]:
        """
        提取响应元数据
        
        参数:
            response: LLM响应对象
            
        返回:
            Dict[str, Any]: 响应元数据
        """
        metadata = {
            "request_id": response.request_id,
            "model": response.model,
            "provider": response.provider_type.value if response.provider_type else None,
            "response_time": response.response_time,
            "finish_reason": response.finish_reason,
            "created_at": response.created_at.isoformat() if response.created_at else None
        }
        
        if response.usage:
            metadata["usage"] = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        
        # 添加自定义元数据
        metadata.update(response.metadata)
        
        return metadata