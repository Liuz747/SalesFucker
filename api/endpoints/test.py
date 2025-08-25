"""简单LLM测试端点"""
import uuid
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from infra.runtimes.client import LLMClient
from infra.runtimes.config import LLMConfig
from infra.runtimes.entities import LLMRequest

router = APIRouter(prefix="/test", tags=["test"])

class ChatRequest(BaseModel):
    message: str
    provider: str
    model: str
    chat_id: Optional[str] = None

@router.post("/chat")
async def test_chat(request: ChatRequest):
    """简单聊天测试"""
    try:
        config = LLMConfig()
        client = LLMClient(config)
        
        # 生成对话ID
        if request.chat_id:
            chat_id = request.chat_id
        else:
            chat_id = str(uuid.uuid4())
        
        llm_request = LLMRequest(
            messages=[
                {"role": "user", "content": request.message}
            ],
            id=chat_id,
            model=request.model,
            provider=request.provider,
            temperature=0.7,
            max_tokens=4000
        )
        
        response = await client.completions(llm_request)
        
        return {
            "chat_id": response.id,
            "response": response.content,
            "provider": response.provider,
            "model": response.model,
            "usage": response.usage,
            "cost": response.cost
        }
        
    except Exception as e:
        return {
            "error": str(e)
        }


@router.get("/config")
async def test_config():
    """检查配置"""
    try:
        config = LLMConfig()
        return {
            "openai_configured": config.openai is not None,
            "anthropic_configured": config.anthropic is not None,
            "openai_enabled": config.openai.enabled if config.openai else False,
            "anthropic_enabled": config.anthropic.enabled if config.anthropic else False
        }
    except Exception as e:
        return {"error": str(e)}