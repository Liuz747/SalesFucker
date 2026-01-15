"""
LLM聊天测试端点
"""

from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from infra.runtimes import CompletionsRequest, LLMClient, ResponseMessageRequest
from libs.types import InputContentParams, Message
from utils import get_component_logger

logger = get_component_logger(__name__, "LLM")

# 创建路由器
router = APIRouter()


class ChatRequest(BaseModel):
    """聊天请求"""
    provider: str
    model: str
    message: InputContentParams
    system_prompt: str = "你是一个助手，请尽可能地回答问题。"
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4000


@router.post("/completion")
async def test_completion_message(request: ChatRequest):
    """
    测试Completion API
    """
    try:
        # 初始化LLM客户端
        client = LLMClient()

        # 构建LLM请求
        llm_request = CompletionsRequest(
            id=uuid4(),
            messages=[Message(role='user', content=request.message)],
            model=request.model,
            provider=request.provider,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )

        return await client.completions(llm_request)

    except Exception as e:
        logger.error(f"Completion API调用失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Completion API调用失败: {str(e)}")


@router.post("/response")
async def test_responses_message(request: ChatRequest):
    """
    测试OpenAI Responses API（基础文本输出）

    使用Responses API进行简单的文本生成，
    相比Chat Completions更简洁，适合单轮对话。
    """
    try:
        # 初始化LLM客户端
        client = LLMClient()

        # 构建Responses请求
        llm_request = ResponseMessageRequest(
            id=uuid4(),
            input=request.message,
            system_prompt=request.system_prompt,
            model=request.model,
            provider=request.provider,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )

        return await client.responses(llm_request)

    except Exception as e:
        logger.error(f"Responses API调用失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Responses API调用失败: {str(e)}")


# 示例：结构化输出的Pydantic模型
class CalendarEvent(BaseModel):
    """日历事件模型（用于测试结构化输出）"""
    name: str
    date: str
    participants: list[str]


@router.post("/completion-structured")
async def test_completion_structured_outputs(request: ChatRequest):
    """
    测试Completion API结构化输出

    使用Completion API的结构化输出功能。
    """
    try:
        # 初始化LLM客户端
        client = LLMClient()

        # 构建LLM请求
        llm_request = CompletionsRequest(
            id=uuid4(),
            messages=[Message(role='user', content=request.message)],
            model=request.model,
            provider=request.provider,
            temperature=request.temperature,
            output_model=CalendarEvent,
            max_tokens=request.max_tokens
        )

        # 返回响应
        return await client.completions(llm_request)

    except Exception as e:
        logger.error(f"Completion结构化输出调用失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Completion结构化输出调用失败: {str(e)}")


@router.post("/response-structured")
async def test_response_structured_outputs(request: ChatRequest):
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

        # 构建Structured Responses请求
        llm_request = ResponseMessageRequest(
            id=uuid4(),
            input=request.message,
            system_prompt=request.system_prompt,
            output_model=CalendarEvent,
            model=request.model,
            provider=request.provider,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )

        return await client.responses(llm_request)

    except Exception as e:
        logger.error(f"Structured Outputs调用失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Structured Outputs调用失败: {str(e)}")
