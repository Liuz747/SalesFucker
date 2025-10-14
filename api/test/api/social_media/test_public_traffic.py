import json

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from controllers.workspace.social_media import public_traffic
from infra.runtimes.entities import LLMResponse
from services import social_media_service


class DummyLLMClient:
    """用于单元测试的LLM假实现"""

    async def completions(self, request):
        payload = {
            "message": "感谢关注，我们已为粉丝准备专属福利，快来加入私域社群了解详情。",
            "rationale": "结合活动目标与行动号召，提供正向引导。",
            "safety_flags": [
                {"code": "platform_guideline", "severity": "low", "detail": "需避免夸大其词"}
            ],
        }
        return LLMResponse(
            id="test",
            content=json.dumps(payload, ensure_ascii=False),
            provider=request.provider,
            model=request.model,
            usage={"input_tokens": 100, "output_tokens": 150},
        )


@pytest.fixture()
def app(monkeypatch):
    """构建测试用FastAPI应用"""
    monkeypatch.setattr(social_media_service, "LLMClient", lambda: DummyLLMClient())
    application = FastAPI()
    application.include_router(public_traffic.router, prefix="/social-media/public")
    return application


@pytest.mark.asyncio()
async def test_generate_comment_success(app):
    """验证评论生成接口返回结构化数据"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "platform": "tiktok",
            "post_excerpt": "新品开箱视频，展示智能健身镜的核心功能和优惠。",
            "call_to_action": "添加客服微信领取专属训练方案",
        }
        response = await client.post("/social-media/public/comment", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["safety_flags"][0]["code"] == "platform_guideline"


@pytest.mark.asyncio()
async def test_summary_request_too_many_comments(app):
    """验证关键词摘要请求的数量限制"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "platform": "instagram",
            "comments": ["test"] * 51,
        }
        response = await client.post("/social-media/public/keywords", json=payload)
        assert response.status_code == 422
