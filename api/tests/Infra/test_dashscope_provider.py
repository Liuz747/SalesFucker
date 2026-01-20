"""
DashScope供应商测试

测试DashScope供应商的基本功能，包括文本和多模态API调用。
"""

import os
from uuid import uuid4

import pytest

from infra.runtimes.client import LLMClient
from infra.runtimes.entities import CompletionsRequest
from libs.types import InputContent, Message


@pytest.fixture
def llm_client():
    """创建LLM客户端实例"""
    return LLMClient()


@pytest.fixture
def dashscope_api_key():
    """获取DashScope API密钥"""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        pytest.skip("DASHSCOPE_API_KEY环境变量未设置")
    return api_key


@pytest.mark.asyncio
async def test_dashscope_text_completion(llm_client, dashscope_api_key):
    """测试DashScope纯文本API调用"""
    # 构建请求
    request = CompletionsRequest(
        id=uuid4(),
        provider="bailian",
        model="qwen-turbo",
        messages=[
            Message(role="user", content="你好，请用一句话介绍一下你自己。")
        ],
        temperature=0.7,
        max_tokens=100
    )

    # 调用API
    response = await llm_client.completions(request)

    # 验证响应
    assert response is not None
    assert response.content is not None
    assert isinstance(response.content, str)
    assert len(response.content) > 0
    assert response.provider == "bailian"
    assert response.model == "qwen-turbo"
    assert response.usage.input_tokens > 0
    assert response.usage.output_tokens > 0
    print(f"\n响应内容: {response.content}")
    print(f"Token使用: 输入={response.usage.input_tokens}, 输出={response.usage.output_tokens}")


@pytest.mark.asyncio
async def test_dashscope_multimodal_completion(llm_client, dashscope_api_key):
    """测试DashScope多模态API调用（带图像）"""
    # 使用一个公开的测试图像URL
    test_image_url = "https://dashscope.oss-cn-beijing.aliyuncs.com/images/dog_and_girl.jpeg"

    # 构建多模态请求
    request = CompletionsRequest(
        id=uuid4(),
        provider="bailian",
        model="qwen-vl-plus",
        messages=[
            Message(
                role="user",
                content=[
                    InputContent(type="text", content="这张图片里有什么？"),
                    InputContent(type="input_image", content=test_image_url)
                ]
            )
        ],
        temperature=0.7,
        max_tokens=200
    )

    # 调用API
    response = await llm_client.completions(request)

    # 验证响应
    assert response is not None
    assert response.content is not None
    assert isinstance(response.content, str)
    assert len(response.content) > 0
    assert response.provider == "bailian"
    assert response.model == "qwen-vl-plus"
    assert response.usage.input_tokens > 0
    assert response.usage.output_tokens > 0
    print(f"\n多模态响应内容: {response.content}")
    print(f"Token使用: 输入={response.usage.input_tokens}, 输出={response.usage.output_tokens}")


@pytest.mark.asyncio
async def test_dashscope_conversation(llm_client, dashscope_api_key):
    """测试DashScope多轮对话"""
    # 构建多轮对话请求
    request = CompletionsRequest(
        id=uuid4(),
        provider="bailian",
        model="qwen-plus",
        messages=[
            Message(role="user", content="请告诉我Python的主要特点。"),
            Message(role="assistant", content="Python是一种高级编程语言，具有简洁易读的语法、丰富的标准库和强大的第三方生态系统。"),
            Message(role="user", content="那它适合做什么？")
        ],
        temperature=0.7,
        max_tokens=150
    )

    # 调用API
    response = await llm_client.completions(request)

    # 验证响应
    assert response is not None
    assert response.content is not None
    assert isinstance(response.content, str)
    assert len(response.content) > 0
    print(f"\n对话响应: {response.content}")


@pytest.mark.asyncio
async def test_dashscope_error_handling(llm_client, dashscope_api_key):
    """测试DashScope错误处理"""
    # 使用无效的模型名称
    request = CompletionsRequest(
        id=uuid4(),
        provider="bailian",
        model="invalid-model-name",
        messages=[
            Message(role="user", content="测试")
        ],
        temperature=0.7,
        max_tokens=50
    )

    # 应该抛出异常
    with pytest.raises(Exception):
        await llm_client.completions(request)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])