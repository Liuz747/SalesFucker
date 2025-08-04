"""
上下文保持器(Context Preserver)组件测试套件

该测试模块专注于上下文保持器的核心功能测试:
- 对话上下文存储和检索
- 供应商间上下文转移
- 上下文连续性保持
- 上下文过期处理
- 长对话上下文压缩
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from src.llm.failover_system.context_preserver import ContextPreserver, ConversationContext
from src.llm.provider_config import ProviderType


class TestContextPreserver:
    """测试上下文保持器组件"""
    
    @pytest.fixture
    def context_preserver(self):
        """上下文保持器fixture"""
        return ContextPreserver(max_context_age=timedelta(hours=1))
    
    def test_conversation_context_storage(self, context_preserver):
        """测试对话上下文存储"""
        conversation_id = "conv_123"
        
        # Create conversation context
        context = ConversationContext(
            conversation_id=conversation_id,
            customer_id="customer_456",
            agent_type="sales",
            conversation_history=[
                {"role": "user", "content": "我想要护肤品推荐"},
                {"role": "assistant", "content": "当然，请告诉我您的肌肤类型"}
            ],
            customer_profile={
                "skin_type": "oily",
                "age_range": "25-35",
                "preferences": ["natural_ingredients"]
            },
            current_state="product_inquiry",
            metadata={"language": "chinese", "urgency": "normal"}
        )
        
        # Store context
        context_preserver.store_context(conversation_id, context)
        
        # Retrieve context
        retrieved_context = context_preserver.get_context(conversation_id)
        
        assert retrieved_context is not None
        assert retrieved_context.conversation_id == conversation_id
        assert retrieved_context.customer_id == "customer_456"
        assert retrieved_context.agent_type == "sales"
        assert len(retrieved_context.conversation_history) == 2
        assert retrieved_context.customer_profile["skin_type"] == "oily"
    
    def test_context_transfer_between_providers(self, context_preserver):
        """测试供应商间上下文转移"""
        conversation_id = "conv_transfer_test"
        
        # Create original context with OpenAI
        original_context = ConversationContext(
            conversation_id=conversation_id,
            customer_id="customer_789",
            agent_type="sentiment",
            conversation_history=[
                {"role": "user", "content": "产品质量有问题"},
                {"role": "assistant", "content": "我理解您的担忧，能详细说明一下问题吗？"}
            ],
            current_provider=ProviderType.OPENAI,
            provider_context={
                "model": "gpt-4",
                "temperature": 0.7,
                "system_prompt": "You are a helpful customer service agent"
            }
        )
        
        context_preserver.store_context(conversation_id, original_context)
        
        # Transfer to Anthropic
        transferred_context = context_preserver.transfer_context(
            conversation_id=conversation_id,
            from_provider=ProviderType.OPENAI,
            to_provider=ProviderType.ANTHROPIC
        )
        
        assert transferred_context is not None
        assert transferred_context.current_provider == ProviderType.ANTHROPIC
        assert transferred_context.conversation_history == original_context.conversation_history
        assert transferred_context.customer_profile == original_context.customer_profile
        
        # Provider-specific context should be adapted
        assert "claude" in transferred_context.provider_context.get("model", "").lower() or \
               transferred_context.provider_context.get("model") == "auto"
    
    def test_context_continuity_preservation(self, context_preserver):
        """测试上下文连续性保持"""
        conversation_id = "conv_continuity_test"
        
        # Create context with conversation state
        context = ConversationContext(
            conversation_id=conversation_id,
            customer_id="customer_continuity",
            agent_type="product",
            conversation_history=[
                {"role": "user", "content": "我在寻找抗衰老产品"},
                {"role": "assistant", "content": "我推荐以下几种成分..."},
                {"role": "user", "content": "这些成分安全吗？"}
            ],
            current_state="safety_inquiry",
            pending_actions=["ingredient_safety_check", "provide_certifications"],
            customer_profile={
                "age_range": "45-55",
                "skin_concerns": ["aging", "wrinkles"],
                "safety_conscious": True
            }
        )
        
        context_preserver.store_context(conversation_id, context)
        
        # Ensure continuity data preserved
        continuity_data = context_preserver.extract_continuity_data(conversation_id)
        
        assert continuity_data["current_state"] == "safety_inquiry"
        assert "ingredient_safety_check" in continuity_data["pending_actions"]
        assert continuity_data["customer_profile"]["safety_conscious"] is True
        assert len(continuity_data["conversation_summary"]) > 0
    
    def test_context_expiration(self, context_preserver):
        """测试上下文过期处理"""
        conversation_id = "conv_expiry_test"
        
        # Create context
        context = ConversationContext(
            conversation_id=conversation_id,
            customer_id="customer_expiry",
            agent_type="memory"
        )
        
        # Mock old timestamp
        context.created_at = datetime.now() - timedelta(hours=2)
        context.last_updated = datetime.now() - timedelta(hours=2)
        
        context_preserver.store_context(conversation_id, context)
        
        # Try to retrieve expired context
        retrieved_context = context_preserver.get_context(conversation_id)
        
        # Should return None for expired context
        assert retrieved_context is None
        
        # Should be cleaned up
        assert conversation_id not in context_preserver.contexts
    
    def test_context_compression_for_long_conversations(self, context_preserver):
        """测试长对话上下文压缩"""
        conversation_id = "conv_long_test"
        
        # Create context with very long conversation history
        long_history = []
        for i in range(100):
            long_history.extend([
                {"role": "user", "content": f"用户消息 {i}"},
                {"role": "assistant", "content": f"助手回复 {i}"}
            ])
        
        context = ConversationContext(
            conversation_id=conversation_id,
            customer_id="customer_long",
            agent_type="sales",
            conversation_history=long_history
        )
        
        # Store and compress
        compressed_context = context_preserver.compress_context(context)
        
        # Should retain essential information but reduce size
        assert len(compressed_context.conversation_history) < len(long_history)
        assert compressed_context.conversation_summary is not None
        assert len(compressed_context.conversation_summary) > 0
        
        # Should preserve recent messages
        recent_messages = compressed_context.conversation_history[-10:]
        assert len(recent_messages) == 10


if __name__ == "__main__":
    # 运行上下文保持器测试
    def run_context_preserver_tests():
        print("运行上下文保持器测试...")
        
        # 测试上下文保持器初始化
        context_preserver = ContextPreserver()
        print("上下文保持器初始化成功")
        
        # 测试上下文存储
        context = ConversationContext(
            conversation_id="test_conv",
            customer_id="test_customer",
            agent_type="test_agent"
        )
        context_preserver.store_context("test_conv", context)
        retrieved = context_preserver.get_context("test_conv")
        assert retrieved is not None
        print(f"上下文存储和检索成功: {retrieved.conversation_id}")
        
        print("上下文保持器测试完成!")
    
    run_context_preserver_tests()