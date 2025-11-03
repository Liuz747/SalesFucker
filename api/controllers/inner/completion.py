"""
LLM聊天端点
"""

import uuid
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from infra.runtimes import LLMClient, CompletionsRequest, ResponseMessageRequest
from libs.types import Message
from utils import get_component_logger

logger = get_component_logger(__name__, "LLM")

# 创建路由器
router = APIRouter()


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    system_prompt: str = "你是一个助手，请尽可能地回答问题。"
    provider: str
    model: str
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
        chat_id = uuid.uuid4()
        
        # 构建LLM请求
        llm_request = CompletionsRequest(
            id=chat_id,
            messages=[Message(role='user', content=request.message)],
            model=request.model,
            provider=request.provider,
            temperature=request.temperature,
            output_model=CalendarEvent,
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


@router.post("/responses")
async def test_responses_api(request: ChatRequest):
    """
    测试OpenAI Responses API（基础文本输出）

    使用Responses API进行简单的文本生成，
    相比Chat Completions更简洁，适合单轮对话。
    """
    try:
        # 初始化LLM客户端
        client = LLMClient()

        # 生成对话ID
        chat_id = uuid.uuid4()

        # 构建Responses请求
        llm_request = ResponseMessageRequest(
            id=chat_id,
            input=request.message,
            system_prompt=request.system_prompt,
            model=request.model,
            provider=request.provider,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )

        # 发送请求
        response = await client.responses(llm_request)

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
        logger.error(f"Responses API调用失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Responses API调用失败: {str(e)}")


# 示例：结构化输出的Pydantic模型
class CalendarEvent(BaseModel):
    """日历事件模型（用于测试结构化输出）"""
    name: str
    date: str
    participants: list[str]


@router.post("/responses/structured")
async def test_structured_outputs(request: ChatRequest):
    """
    测试OpenAI Structured Outputs（结构化输出）

    使用Responses API的parse方法获取结构化数据，
    确保输出严格遵循指定的JSON Schema。

    支持的schema类型:
    - calendar: 日历事件提取
    - research_paper: 研究论文信息提取
    """
    try:
        # 初始化LLM客户端
        client = LLMClient()

        # 生成对话ID
        chat_id = uuid.uuid4()

        # 构建Structured Responses请求
        llm_request = ResponseMessageRequest(
            id=chat_id,
            input=request.message,
            system_prompt=request.system_prompt,
            output_model=CalendarEvent,
            model=request.model,
            provider=request.provider,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )

        # 发送请求
        response = await client.responses(llm_request)

        # 返回响应
        return {
            "chat_id": response.id,
            "response": response.content,
            "provider": response.provider,
            "model": response.model,
            "usage": response.usage,
            "cost": response.cost
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Structured Outputs调用失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Structured Outputs调用失败: {str(e)}")

