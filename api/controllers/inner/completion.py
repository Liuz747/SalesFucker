"""
LLM聊天端点
"""

import uuid
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from infra.runtimes import LLMClient, LLMRequest
from libs.types import Message
from utils import get_component_logger

logger = get_component_logger(__name__, "LLM")

# 创建路由器
router = APIRouter()


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    provider: str
    model: str
    chat_id: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4000


@router.post("/")
async def send_message(request: ChatRequest):
    """
    发送聊天消息
    
    简单的聊天接口，直接使用LLMClient
    """
    try:
        # 初始化LLM客户端
        client = LLMClient()
        
        # 生成对话ID
        chat_id = request.chat_id or str(uuid.uuid4())
        
        # 构建LLM请求
        llm_request = LLMRequest(
            id=chat_id,
            messages=[Message(role='user', content=request.message)],
            model=request.model,
            provider=request.provider,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        # 发送请求
        response = await client.completions(llm_request)
        
        # 返回响应
        return {
            "chat_id": response.id,
            "response": response.content,
            "provider": response.provider,
            "model": response.model,
            "usage": response.usage,
            "cost": response.cost
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"聊天失败: {str(e)}")
