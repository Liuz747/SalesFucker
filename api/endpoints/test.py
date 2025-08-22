"""简单LLM测试端点"""

from fastapi import APIRouter
from pydantic import BaseModel

from infra.runtimes.client import LLMClient
from infra.runtimes.config import LLMConfig
from infra.runtimes.entities import LLMRequest

router = APIRouter(prefix="/test", tags=["test"])

class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
async def test_chat(request: ChatRequest):
    """简单聊天测试"""
    try:
        config = LLMConfig()
        client = LLMClient(config)
        
        llm_request = LLMRequest(
            messages=[
                {"role": "user", "content": request.message}
            ],
            model="claude-3-5-sonnet-20241022",
            # model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=4000
        )
        
        response = await client.chat(llm_request)
        
        return {
            "message": request.message,
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