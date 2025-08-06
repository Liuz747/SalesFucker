"""
合规智能体测试套件

该测试模块专注于合规智能体的核心功能测试:
- 合规规则验证和消息检查
- 内容过滤和危险内容阻止
- LLM增强的合规分析
- 多租户合规配置
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from src.agents.base import ThreadState, AgentMessage
from src.agents.compliance import ComplianceAgent, ComplianceRule
from src.llm.multi_llm_client import MultiLLMClient
from src.llm.provider_config import ProviderType, GlobalProviderConfig
from src.llm.base_provider import LLMRequest, LLMResponse, RequestType


class TestComplianceAgent:
    """合规智能体测试套件"""
    
    @pytest.fixture
    def compliance_agent(self):
        """创建测试用合规智能体"""
        return ComplianceAgent("test_tenant")
    
    @pytest.mark.asyncio
    async def test_compliance_approved_message(self, compliance_agent):
        """测试干净的消息会被增强的LLM+规则系统批准"""
        with patch.object(compliance_agent, '_llm_compliance_analysis', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "status": "approved",
                "violations": [],
                "severity": "low",
                "user_message": "",
                "recommended_action": "proceed"
            }
            
            result = await compliance_agent._enhanced_compliance_check(
                "I'm looking for a great moisturizer for dry skin."
            )
            
            assert result["status"] == "approved"
            assert len(result["violations"]) == 0
            assert result["agent_id"] == compliance_agent.agent_id
            assert result["analysis_method"] == "hybrid"
    
    @pytest.mark.asyncio
    async def test_compliance_flagged_message(self, compliance_agent):
        """测试包含可疑内容的消息被标记"""
        result = await compliance_agent._perform_compliance_check(
            "Do you have any miracle products that cure aging overnight?"
        )
        
        assert result["status"] == "flagged"
        assert len(result["violations"]) > 0
        assert any("miracle" in str(violation) for violation in result["violations"])
    
    @pytest.mark.asyncio
    async def test_compliance_blocked_message(self, compliance_agent):
        """测试危险内容被阻止"""
        result = await compliance_agent._perform_compliance_check(
            "I want products with mercury for skin whitening."
        )
        
        assert result["status"] == "blocked"
        assert len(result["violations"]) > 0
        assert any("mercury" in str(violation) for violation in result["violations"])
    
    @pytest.mark.asyncio
    async def test_conversation_state_processing(self, compliance_agent):
        """测试处理对话状态"""
        state = ThreadState(
            tenant_id="test_tenant",
            customer_input="Hello, I need help with skincare.",
            thread_id="conv_123"
        )
        
        with patch.object(compliance_agent, '_perform_compliance_check', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = {
                "status": "approved",
                "violations": [],
                "severity": "low",
                "confidence": 0.95
            }
            
            processed_state = await compliance_agent.process(state)
            
            assert processed_state.compliance_status == "approved"
            assert processed_state.processing_metadata["compliance_agent"]["status"] == "approved"
    
    @pytest.mark.asyncio
    async def test_multi_llm_compliance_analysis(self, compliance_agent):
        """测试多LLM合规分析"""
        with patch.object(compliance_agent, 'multi_llm_client') as mock_client:
            mock_client.chat_completion = AsyncMock(return_value=LLMResponse(
                content='{"status": "approved", "violations": [], "severity": "low"}',
                model="claude-3-sonnet",
                provider=ProviderType.ANTHROPIC,
                cost=0.001,
                input_tokens=50,
                output_tokens=30,
                latency_ms=500
            ))
            
            result = await compliance_agent._llm_compliance_analysis(
                "I'm interested in natural skincare products."
            )
            
            assert result["status"] == "approved"
            assert isinstance(result["violations"], list)
            assert result["severity"] == "low"
    
    def test_compliance_rule_creation(self, compliance_agent):
        """测试合规规则创建"""
        rule = ComplianceRule(
            rule_id="test_rule_001",
            rule_type="content_filter",
            pattern=r"\b(miracle|cure|overnight)\b",
            severity="high",
            action="flag",
            description="检测夸大宣传词汇"
        )
        
        assert rule.rule_id == "test_rule_001"
        assert rule.severity == "high"
        assert rule.action == "flag"
        
        # Test rule matching
        test_text = "This miracle cream cures all aging problems overnight."
        matches = rule.check_text(test_text)
        assert len(matches) > 0
    
    @pytest.mark.asyncio
    async def test_tenant_specific_compliance(self, compliance_agent):
        """测试租户特定合规配置"""
        # Test that different tenants can have different compliance rules
        tenant_a_agent = ComplianceAgent("tenant_a")
        tenant_b_agent = ComplianceAgent("tenant_b")
        
        assert tenant_a_agent.tenant_id == "tenant_a"
        assert tenant_b_agent.tenant_id == "tenant_b"
        assert tenant_a_agent.agent_id != tenant_b_agent.agent_id
    
    @pytest.mark.asyncio
    async def test_compliance_severity_levels(self, compliance_agent):
        """测试合规严重程度级别"""
        test_cases = [
            ("I love your natural products!", "low"),
            ("Do you have anti-aging creams?", "medium"),
            ("I need products with dangerous chemicals", "high")
        ]
        
        for message, expected_severity in test_cases:
            with patch.object(compliance_agent, '_calculate_severity') as mock_severity:
                mock_severity.return_value = expected_severity
                
                result = await compliance_agent._perform_compliance_check(message)
                assert result["severity"] == expected_severity
    
    def test_compliance_agent_metadata(self, compliance_agent):
        """测试合规智能体元数据"""
        assert compliance_agent.agent_type == "compliance"
        assert compliance_agent.tenant_id == "test_tenant"
        assert hasattr(compliance_agent, 'rules')
        assert hasattr(compliance_agent, 'multi_llm_client')


if __name__ == "__main__":
    # 运行合规智能体测试
    async def run_compliance_agent_tests():
        print("运行合规智能体测试...")
        
        # 创建合规智能体
        agent = ComplianceAgent("test_tenant")
        assert agent.agent_type == "compliance"
        print(f"合规智能体创建成功: {agent.agent_id}")
        
        # 测试基本合规检查
        try:
            result = await agent._perform_compliance_check("Hello, I need skincare advice.")
            print(f"合规检查完成: {result.get('status', 'unknown')}")
        except Exception as e:
            print(f"合规检查测试错误: {e}")
        
        print("合规智能体测试完成!")
    
    asyncio.run(run_compliance_agent_tests())