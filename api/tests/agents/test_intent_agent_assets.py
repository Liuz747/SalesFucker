"""
IntentAgent素材功能集成测试

测试IntentAgent与AssetsService的集成，验证:
1. 素材意向检测
2. 素材查询和缓存
3. 关键词搜索和过滤
4. 状态更新
"""

import os
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from core.agents.intent.agent import IntentAgent
from core.entities import WorkflowExecutionModel
from libs.types import UserMessage, AgentNodeType
from utils import get_component_logger

logger = get_component_logger(__name__)


@pytest.fixture
def mock_llm_client():
    """Mock LLM客户端"""
    client = AsyncMock()

    # Mock意向分析响应（检测到素材意向）
    client.completions.return_value = AsyncMock(
        content="""```json
{
  "appointment_intent": {
    "detected": false
  },
  "invitation_intent": {
    "detected": false
  },
  "assets_intent": {
    "detected": true,
    "keywords": ["产品介绍", "价格表"]
  },
  "audio_output_intent": {
    "detected": false
  }
}
```""",
        input_tokens=100,
        output_tokens=50
    )

    return client


@pytest.fixture
def mock_assets_service():
    """Mock AssetsService"""
    service = AsyncMock()

    # Mock素材查询响应
    service.query_assets.return_value = {
        "assets": [
            {
                "id": 1,
                "name": "产品介绍视频",
                "content": "这是一个关于我们产品的介绍视频",
                "remark": "适合新客户"
            },
            {
                "id": 2,
                "name": "价格表2024",
                "content": "最新的产品价格表",
                "remark": "2024年版本"
            },
            {
                "id": 3,
                "name": "使用手册",
                "content": "详细的产品使用说明",
                "remark": "包含常见问题"
            }
        ],
        "total": 3,
        "from_cache": False
    }

    return service


@pytest.fixture
def workflow_state():
    """创建工作流状态"""
    user_message = UserMessage(
        role="user",
        content="你好，我想要产品介绍和价格表"
    )

    state = WorkflowExecutionModel(
        tenant_id="test-tenant",
        thread_id=uuid4(),
        assistant_id=uuid4(),
        workflow_id=uuid4(),
        user_id="test-user",
        input=[user_message],
        messages=[user_message],
        actions=[],
        agent_node_type=AgentNodeType.INTENT,
        input_tokens=0,
        output_tokens=0
    )

    return state


class TestIntentAgentAssets:
    """IntentAgent素材功能测试"""

    @pytest.mark.asyncio
    async def test_assets_intent_detection(self, mock_llm_client, mock_assets_service, workflow_state):
        """测试素材意向检测"""
        with patch('core.agents.intent.agent.AssetsService', return_value=mock_assets_service):
            agent = IntentAgent(llm_client=mock_llm_client)

            result = await agent.run(workflow_state)

            # 验证意向分析结果
            assert "intent_analysis" in result
            intent_analysis = result["intent_analysis"]
            assert intent_analysis["assets_intent"]["detected"] is True
            assert "产品介绍" in intent_analysis["assets_intent"]["keywords"]
            assert "价格表" in intent_analysis["assets_intent"]["keywords"]

    @pytest.mark.asyncio
    async def test_assets_query_when_detected(self, mock_llm_client, mock_assets_service, workflow_state):
        """测试检测到素材意向时查询素材"""
        with patch('core.agents.intent.agent.AssetsService', return_value=mock_assets_service):
            agent = IntentAgent(llm_client=mock_llm_client)

            result = await agent.run(workflow_state)

            # 验证调用了素材查询
            mock_assets_service.query_assets.assert_called_once()
            call_kwargs = mock_assets_service.query_assets.call_args[1]
            assert call_kwargs["tenant_id"] == "test-tenant"
            assert call_kwargs["thread_id"] == workflow_state.thread_id

            # 验证素材数据添加到状态
            assert "assets_data" in result
            assert result["assets_data"] is not None
            assert "assets" in result["assets_data"]
            assert result["assets_data"]["total"] > 0

    @pytest.mark.asyncio
    async def test_assets_keyword_filtering(self, mock_llm_client, mock_assets_service, workflow_state):
        """测试关键词过滤素材"""
        with patch('core.agents.intent.agent.AssetsService', return_value=mock_assets_service):
            with patch('services.assets_service.AssetsService.search_assets') as mock_search:
                # Mock搜索结果
                mock_search.return_value = [
                    {
                        "id": 1,
                        "name": "产品介绍视频",
                        "content": "这是一个关于我们产品的介绍视频",
                        "remark": "适合新客户",
                        "search_score": 10,
                        "matched_keywords": ["产品介绍(name)"]
                    },
                    {
                        "id": 2,
                        "name": "价格表2024",
                        "content": "最新的产品价格表",
                        "remark": "2024年版本",
                        "search_score": 8,
                        "matched_keywords": ["价格表(name)"]
                    }
                ]

                agent = IntentAgent(llm_client=mock_llm_client)
                result = await agent.run(workflow_state)

                # 验证调用了搜索
                mock_search.assert_called_once()
                call_args = mock_search.call_args[1]
                assert "keywords" in call_args
                assert "产品介绍" in call_args["keywords"]
                assert "价格表" in call_args["keywords"]

                # 验证过滤后的结果
                assert result["assets_data"]["filtered"] is True
                assert len(result["assets_data"]["assets"]) == 2

    @pytest.mark.asyncio
    async def test_no_assets_query_when_not_detected(self, mock_llm_client, mock_assets_service, workflow_state):
        """测试未检测到素材意向时不查询"""
        # Mock未检测到素材意向
        mock_llm_client.completions.return_value = AsyncMock(
            content="""```json
{
  "appointment_intent": {
    "detected": false
  },
  "invitation_intent": {
    "detected": false
  },
  "assets_intent": {
    "detected": false,
    "keywords": []
  },
  "audio_output_intent": {
    "detected": false
  }
}
```""",
            input_tokens=100,
            output_tokens=50
        )

        with patch('core.agents.intent.agent.AssetsService', return_value=mock_assets_service):
            agent = IntentAgent(llm_client=mock_llm_client)
            result = await agent.run(workflow_state)

            # 验证未调用素材查询
            mock_assets_service.query_assets.assert_not_called()

            # 验证assets_data为None
            assert result.get("assets_data") is None

    @pytest.mark.asyncio
    async def test_assets_query_error_handling(self, mock_llm_client, mock_assets_service, workflow_state):
        """测试素材查询错误处理"""
        # Mock查询失败
        mock_assets_service.query_assets.side_effect = Exception("API连接失败")

        with patch('core.agents.intent.agent.AssetsService', return_value=mock_assets_service):
            agent = IntentAgent(llm_client=mock_llm_client)

            # 应该不抛出异常，而是返回错误信息
            result = await agent.run(workflow_state)

            # 验证错误被捕获
            assert "assets_data" in result
            assert result["assets_data"]["total"] == 0
            assert "error" in result["assets_data"]

    @pytest.mark.asyncio
    async def test_assets_data_in_state_update(self, mock_llm_client, mock_assets_service, workflow_state):
        """测试素材数据正确添加到状态更新"""
        with patch('core.agents.intent.agent.AssetsService', return_value=mock_assets_service):
            agent = IntentAgent(llm_client=mock_llm_client)
            result = await agent.run(workflow_state)

            # 验证状态更新包含所有必要字段
            assert "actions" in result
            assert "assets_data" in result
            assert "intent_analysis" in result
            assert "business_outputs" in result
            assert "input_tokens" in result
            assert "output_tokens" in result

            # 验证素材数据结构
            assets_data = result["assets_data"]
            assert isinstance(assets_data, dict)
            assert "assets" in assets_data
            assert "total" in assets_data
            assert "from_cache" in assets_data
            assert "keywords" in assets_data
            assert "filtered" in assets_data


# 如果直接运行此文件
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])