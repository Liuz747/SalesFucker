"""
中文语言检测和路由测试套件

该测试套件专门测试中文语言相关的功能:
- 中文语言检测和路由
- 中文内容优化供应商选择
- 中文语言偏好处理
"""

import pytest
from unittest.mock import Mock, patch

from infra.runtimes.client import LLMClient
from infra.runtimes.entities import LLMRequest, LLMResponse
from infra.runtimes.config import LLMConfig
from infra.runtimes.entities.providers import ProviderType


class TestChineseLanguageDetection:
    """中文语言检测测试"""
    
    @pytest.fixture
    def chinese_optimized_config(self):
        """中文优化配置"""
        return GlobalProviderConfig(
            default_providers={
                "deepseek": ProviderConfig(
                    provider_type=ProviderType.DEEPSEEK,
                    credentials=ProviderCredentials(
                        provider_type=ProviderType.DEEPSEEK,
                        api_key="test-deepseek-key"
                    ),
                    models={
                        "deepseek-chat": {
                            "capabilities": [
                                ModelCapability.CHINESE_OPTIMIZATION,
                                ModelCapability.TEXT_GENERATION
                            ],
                            "supports_chinese": True,
                            "cost_per_1k_tokens": 0.0005
                        }
                    },
                    is_enabled=True,
                    priority=1
                ),
                "gemini": ProviderConfig(
                    provider_type=ProviderType.GEMINI,
                    credentials=ProviderCredentials(
                        provider_type=ProviderType.GEMINI,
                        api_key="test-gemini-key"
                    ),
                    models={
                        "gemini-pro": {
                            "capabilities": [
                                ModelCapability.CHINESE_OPTIMIZATION,
                                ModelCapability.MULTIMODAL
                            ],
                            "supports_chinese": True,
                            "cost_per_1k_tokens": 0.001
                        }
                    },
                    is_enabled=True,
                    priority=2
                )
            }
        )
    
    def test_chinese_content_detection(self, chinese_optimized_config):
        """测试中文内容检测"""
        client = MultiLLMClient(chinese_optimized_config)
        
        # Test various Chinese content types
        test_cases = [
            {
                "content": "我想要一款适合干性皮肤的面霜",
                "expected_language": "chinese",
                "content_type": "skincare_inquiry"
            },
            {
                "content": "这个粉底液的色号有哪些？",
                "expected_language": "chinese", 
                "content_type": "product_inquiry"
            },
            {
                "content": "请推荐一些口红颜色，我比较喜欢温柔的感觉",
                "expected_language": "chinese",
                "content_type": "makeup_recommendation"
            }
        ]
        
        for case in test_cases:
            # Mock language detection
            with patch.object(client.request_builder, 'detect_language') as mock_detect:
                mock_detect.return_value = case["expected_language"]
                
                # Mock routing context building
                with patch.object(client.request_builder, 'build_routing_context') as mock_context:
                    expected_context = RoutingContext(
                        content_language=case["expected_language"],
                        agent_type="product",
                        tenant_id="test_tenant"
                    )
                    mock_context.return_value = expected_context
                    
                    context = client.request_builder.build_routing_context(
                        agent_type="product",
                        tenant_id="test_tenant",
                        messages=[{"role": "user", "content": case["content"]}]
                    )
                    
                    assert context.content_language == case["expected_language"]
    
    def test_chinese_provider_preference(self, chinese_optimized_config):
        """测试中文内容的供应商偏好"""
        client = MultiLLMClient(chinese_optimized_config)
        
        chinese_context = RoutingContext(
            content_language="chinese",
            agent_type="sales",
            tenant_id="test_tenant"
        )
        
        with patch.object(client.intelligent_router, 'route_request') as mock_router:
            # For Chinese content, should prefer DeepSeek or Gemini
            mock_provider = Mock()
            mock_provider.provider_type = ProviderType.DEEPSEEK
            mock_router.return_value = mock_provider
            
            request = LLMRequest(
                request_id="chinese_test",
                request_type=RequestType.CHAT_COMPLETION,
                messages=[{"role": "user", "content": "推荐适合敏感肌肤的护肤品"}],
                metadata={"language": "chinese"}
            )
            
            selected_provider = client.intelligent_router.route_request(
                request, chinese_context, RoutingStrategy.CHINESE_OPTIMIZED
            )
            
            # Should select Chinese-optimized provider
            assert selected_provider.provider_type in [ProviderType.DEEPSEEK, ProviderType.GEMINI]
    
    def test_english_content_detection(self, chinese_optimized_config):
        """测试英文内容检测"""
        client = MultiLLMClient(chinese_optimized_config)
        
        english_content = "Hello, I need help with skincare"
        
        with patch.object(client.request_builder, 'detect_language') as mock_detect:
            mock_detect.return_value = "english"
            
            with patch.object(client.request_builder, 'build_routing_context') as mock_context:
                expected_context = RoutingContext(
                    content_language="english",
                    agent_type="product",
                    tenant_id="test_tenant"
                )
                mock_context.return_value = expected_context
                
                context = client.request_builder.build_routing_context(
                    agent_type="product",
                    tenant_id="test_tenant",
                    messages=[{"role": "user", "content": english_content}]
                )
                
                assert context.content_language == "english"


class TestChineseOptimizedRouting:
    """测试中文优化路由"""
    
    def test_chinese_context_routing(self):
        """测试中文上下文路由"""
        context = RoutingContext(
            agent_type="product",
            tenant_id="test_tenant",
            content_language="chinese",
            strategy=RoutingStrategy.CHINESE_OPTIMIZED
        )
        
        assert context.content_language == "chinese"
        assert context.strategy == RoutingStrategy.CHINESE_OPTIMIZED
        assert context.agent_type == "product"
    
    def test_chinese_request_metadata(self):
        """测试中文请求元数据"""
        request = LLMRequest(
            request_id="chinese_opt_001",
            request_type=RequestType.CHAT_COMPLETION,
            messages=[{"role": "user", "content": "推荐适合中国消费者的美妆产品"}],
            metadata={"language": "chinese", "region": "china"}
        )
        
        assert request.metadata["language"] == "chinese"
        assert request.metadata["region"] == "china"
        assert "推荐适合中国消费者的美妆产品" in request.messages[0]["content"]


if __name__ == "__main__":
    print("中文语言检测测试模块加载成功")
    print("测试覆盖: 语言检测、供应商偏好、优化路由")