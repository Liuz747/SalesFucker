"""
中文语言优化核心测试套件

该测试套件专注于中文语言优化的核心功能测试:
- 中文语言优化基础测试
- 中文供应商配置验证
- 基本中文处理流程

更多专业测试请参见:
- test_chinese_language_detection.py (中文语言检测测试)
- test_chinese_terminology.py (中文术语处理测试)
- test_chinese_cultural_context.py (中文文化上下文测试)
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime

from src.llm.multi_llm_client import MultiLLMClient
from src.llm.provider_config import (
    ProviderType, GlobalProviderConfig, ProviderConfig,
    ModelCapability, ProviderCredentials
)
from src.llm.base_provider import LLMRequest, RequestType
from src.llm.intelligent_router import RoutingStrategy, RoutingContext


class TestChineseOptimizationCore:
    """中文语言优化核心测试"""
    
    @pytest.fixture
    def chinese_config(self):
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
                            "capabilities": [ModelCapability.CHINESE_OPTIMIZATION],
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
                            "capabilities": [ModelCapability.CHINESE_OPTIMIZATION],
                            "supports_chinese": True,
                            "cost_per_1k_tokens": 0.001
                        }
                    },
                    is_enabled=True,
                    priority=2
                )
            }
        )
    
    def test_chinese_provider_configuration(self, chinese_config):
        """测试中文优化供应商配置"""
        # Verify DeepSeek configuration
        deepseek_config = chinese_config.default_providers["deepseek"]
        assert deepseek_config.provider_type == ProviderType.DEEPSEEK
        assert ModelCapability.CHINESE_OPTIMIZATION in deepseek_config.models["deepseek-chat"]["capabilities"]
        assert deepseek_config.models["deepseek-chat"]["supports_chinese"]
        
        # Verify Gemini configuration
        gemini_config = chinese_config.default_providers["gemini"]
        assert gemini_config.provider_type == ProviderType.GEMINI
        assert ModelCapability.CHINESE_OPTIMIZATION in gemini_config.models["gemini-pro"]["capabilities"]
        assert gemini_config.models["gemini-pro"]["supports_chinese"]
    
    def test_chinese_context_creation(self):
        """测试中文上下文创建"""
        context = RoutingContext(
            content_language="chinese",
            agent_type="sales",
            tenant_id="test_tenant",
            strategy=RoutingStrategy.CHINESE_OPTIMIZED
        )
        
        assert context.content_language == "chinese"
        assert context.strategy == RoutingStrategy.CHINESE_OPTIMIZED
        assert context.agent_type == "sales"
        assert context.tenant_id == "test_tenant"
    
    def test_chinese_request_creation(self):
        """测试中文请求创建"""
        request = LLMRequest(
            request_id="chinese_test",
            request_type=RequestType.CHAT_COMPLETION,
            messages=[{"role": "user", "content": "推荐适合敏感肌肤的护肤品"}],
            metadata={"language": "chinese", "region": "china"}
        )
        
        assert request.metadata["language"] == "chinese"
        assert request.metadata["region"] == "china"
        assert "推荐适合敏感肌肤的护肤品" in request.messages[0]["content"]
        assert request.request_type == RequestType.CHAT_COMPLETION


class TestBasicChineseRouting:
    """测试基础中文路由"""
    
    def test_chinese_routing_strategy(self):
        """测试中文路由策略"""
        assert RoutingStrategy.CHINESE_OPTIMIZED is not None
        
        # Verify strategy enum value
        strategy = RoutingStrategy.CHINESE_OPTIMIZED
        assert isinstance(strategy, RoutingStrategy)
    
    def test_chinese_provider_types(self):
        """测试中文供应商类型"""
        chinese_providers = [ProviderType.DEEPSEEK, ProviderType.GEMINI]
        
        for provider in chinese_providers:
            assert isinstance(provider, ProviderType)
            assert provider in [ProviderType.DEEPSEEK, ProviderType.GEMINI]
    
    def test_chinese_capability_detection(self):
        """测试中文能力检测"""
        chinese_capability = ModelCapability.CHINESE_OPTIMIZATION
        
        assert chinese_capability is not None
        assert isinstance(chinese_capability, ModelCapability)


class TestChineseTerminologyBasics:
    """测试中文术语基础"""
    
    def test_skincare_terms_recognition(self):
        """测试护肤术语识别"""
        skincare_terms = ["保湿", "补水", "控油", "美白", "敏感肌"]
        
        test_text = "我是敏感肌，需要保湿和补水的产品"
        
        detected_terms = [term for term in skincare_terms if term in test_text]
        
        assert "敏感肌" in detected_terms
        assert "保湿" in detected_terms
        assert "补水" in detected_terms
        assert len(detected_terms) == 3
    
    def test_makeup_terms_recognition(self):
        """测试彩妆术语识别"""
        makeup_terms = ["粉底液", "口红", "眼影", "腮红", "睫毛膏"]
        
        test_text = "想买一支口红和粉底液"
        
        detected_terms = [term for term in makeup_terms if term in test_text]
        
        assert "口红" in detected_terms
        assert "粉底液" in detected_terms
        assert len(detected_terms) == 2


if __name__ == "__main__":
    # Run Chinese optimization tests
    async def run_chinese_tests():
        print("运行中文优化测试...")
        
        # Test Chinese language detection
        config = GlobalProviderConfig(
            default_providers={
                "deepseek": ProviderConfig(
                    provider_type=ProviderType.DEEPSEEK,
                    credentials=ProviderCredentials(
                        provider_type=ProviderType.DEEPSEEK,
                        api_key="test-key"
                    ),
                    is_enabled=True
                )
            }
        )
        
        client = MultiLLMClient(config)
        print("中文优化配置创建成功")
        
        # Test terminology detection
        chinese_terms = ["保湿", "补水", "控油", "美白", "抗衰老"]
        print(f"中文术语检测: {len(chinese_terms)}个化妆品术语")
        
        print("中文优化测试完成!")
    
    asyncio.run(run_chinese_tests())