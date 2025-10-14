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
        user_prompt = request.messages[-1].content
        if "keywords、count 和 summary 字段" in user_prompt:
            payload = {
                "keywords": ["新品", "优惠"],
                "count": 2,
                "summary": "用户关注优惠信息，可引导至私域领取更多福利。",
            }
        else:
            payload = {
                "message": "这波福利太香啦！私信我们领取专属优惠码，限时发放。",
                "rationale": "强调限时优惠并引导用户进入私域渠道。",
                "follow_up_prompt": "想了解更多新品福利吗？快来添加我们的企业微信~",
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
            "platform": "douyin",
            "goal_prompt": "引导用户添加企业微信获取新品优惠",
            "comment_prompt": "突出限时福利，鼓励加入私域社群",
            "task_list": [
                {
                    "product_content": "智能健身镜限时7折，评论区留言抽五人送体脂秤。",
                    "likes_num": 986,
                    "replies_num": 142,
                    "favorite_num": 312,
                    "forward_num": 88,
                }
            ],
        }
        response = await client.post("/social-media/public/comment", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "rationale" in data


@pytest.mark.asyncio()
async def test_summary_request_invalid_expect_count(app):
    """验证关键词摘要接口的数量限制"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "platform": "rednote",
            "goal_prompt": "梳理用户对新品精华液的关注点",
            "expecting_count": 25,
        }
        response = await client.post("/social-media/public/keywords", json=payload)
        assert response.status_code == 422
