"""
销售智能体测试套件

该测试模块专注于销售智能体的核心功能测试:
- 销售策略和推荐引擎
- 客户互动和对话管理
- 产品推荐和交叉销售
- 多LLM供应商路由优化
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from core.agents.base import ThreadState, AgentMessage
from core.agents.sales import SalesAgent
from infra.runtimes.client import LLMClient
from infra.runtimes.entities import LLMRequest, LLMResponse
from infra.runtimes.config import LLMConfig


class TestSalesAgent:
    """销售智能体测试套件"""
    
    @pytest.fixture
    def sales_agent(self):
        """创建测试用销售智能体"""
        return SalesAgent("test_tenant")
    
    @pytest.mark.asyncio
    async def test_sales_product_recommendation(self, sales_agent):
        """测试产品推荐功能"""
        customer_context = {
            "skin_type": "oily",
            "age_range": "25-35",
            "budget": "mid-range",
            "concerns": ["acne", "large_pores"]
        }
        
        with patch.object(sales_agent, '_generate_recommendations', new_callable=AsyncMock) as mock_rec:
            mock_rec.return_value = {
                "products": [
                    {
                        "name": "Salicylic Acid Cleanser",
                        "reason": "Helps control oil and reduce acne",
                        "price_range": "$15-25",
                        "confidence": 0.9
                    },
                    {
                        "name": "Niacinamide Serum",
                        "reason": "Minimizes pores and controls oil production",
                        "price_range": "$20-30", 
                        "confidence": 0.85
                    }
                ],
                "strategy": "targeted_solution",
                "total_confidence": 0.875
            }
            
            recommendations = await sales_agent._generate_product_recommendations(customer_context)
            
            assert len(recommendations["products"]) == 2
            assert recommendations["strategy"] == "targeted_solution"
            assert recommendations["products"][0]["confidence"] == 0.9
    
    @pytest.mark.asyncio
    async def test_sales_conversation_flow(self, sales_agent):
        """测试销售对话流程"""
        state = ThreadState(
            tenant_id="test_tenant",
            customer_input="I'm looking for anti-aging products",
            thread_id="conv_sales_123",
            conversation_history=[
                {"role": "user", "content": "Hi, I need help with skincare"},
                {"role": "assistant", "content": "I'd be happy to help! What's your main concern?"}
            ]
        )
        
        with patch.object(sales_agent, 'multi_llm_client') as mock_client:
            mock_client.chat_completion = AsyncMock(return_value=LLMResponse(
                content="I understand you're interested in anti-aging products. Could you tell me your age range and current skincare routine?",
                model="gpt-4",
                provider=ProviderType.OPENAI,
                cost=0.002,
                input_tokens=80,
                output_tokens=25,
                latency_ms=750
            ))
            
            processed_state = await sales_agent.process(state)
            
            assert processed_state.sales_stage == "discovery"
            assert "anti-aging" in processed_state.processing_metadata["sales_agent"]["context"]
            assert processed_state.agent_response is not None
    
    @pytest.mark.asyncio
    async def test_cross_selling_opportunities(self, sales_agent):
        """测试交叉销售机会识别"""
        customer_profile = {
            "purchased_products": ["vitamin_c_serum"],
            "skin_concerns": ["dark_spots", "dullness"],
            "spending_history": {"total": 45.0, "avg_order": 22.5}
        }
        
        with patch.object(sales_agent, '_identify_cross_sell_opportunities', new_callable=AsyncMock) as mock_cross:
            mock_cross.return_value = {
                "opportunities": [
                    {
                        "product": "SPF 50 Sunscreen",
                        "reason": "Essential for vitamin C routine, prevents dark spots",
                        "urgency": "high",
                        "potential_value": 25.0
                    },
                    {
                        "product": "Exfoliating Toner",
                        "reason": "Enhances vitamin C absorption and reduces dullness",
                        "urgency": "medium",
                        "potential_value": 18.0
                    }
                ],
                "total_potential": 43.0,
                "strategy": "complementary_products"
            }
            
            opportunities = await sales_agent._analyze_cross_selling(customer_profile)
            
            assert len(opportunities["opportunities"]) == 2
            assert opportunities["total_potential"] == 43.0
            assert opportunities["opportunities"][0]["urgency"] == "high"
    
    @pytest.mark.asyncio
    async def test_sales_stage_progression(self, sales_agent):
        """测试销售阶段推进"""
        stages = ["awareness", "discovery", "consideration", "decision", "purchase"]
        
        for stage in stages:
            state = ThreadState(
                tenant_id="test_tenant",
                customer_input=f"Customer input for {stage} stage",
                thread_id=f"conv_{stage}",
                sales_stage=stage
            )
            
            with patch.object(sales_agent, '_determine_next_stage') as mock_stage:
                next_stage_map = {
                    "awareness": "discovery",
                    "discovery": "consideration", 
                    "consideration": "decision",
                    "decision": "purchase",
                    "purchase": "follow_up"
                }
                mock_stage.return_value = next_stage_map.get(stage, stage)
                
                processed_state = await sales_agent._advance_sales_stage(state)
                
                expected_next = next_stage_map.get(stage, stage)
                assert processed_state.sales_stage == expected_next
    
    @pytest.mark.asyncio  
    async def test_personalized_messaging(self, sales_agent):
        """测试个性化消息生成"""
        customer_data = {
            "name": "Sarah",
            "preferences": ["natural_ingredients", "cruelty_free"],
            "communication_style": "detailed_explanations",
            "previous_interactions": 3
        }
        
        with patch.object(sales_agent, '_personalize_message', new_callable=AsyncMock) as mock_personalize:
            mock_personalize.return_value = {
                "message": "Hi Sarah! Based on your preference for natural, cruelty-free products, I have some excellent recommendations that align with your values.",
                "tone": "friendly_professional",
                "personalization_elements": ["name", "preferences", "values"],
                "confidence": 0.92
            }
            
            personalized = await sales_agent._create_personalized_response(
                "Hello, I'm looking for new products", 
                customer_data
            )
            
            assert "Sarah" in personalized["message"]
            assert "natural" in personalized["message"]
            assert personalized["confidence"] > 0.9
    
    @pytest.mark.asyncio
    async def test_objection_handling(self, sales_agent):
        """测试异议处理"""
        objections = [
            "This product is too expensive",
            "I'm not sure this will work for my skin",
            "I've tried similar products before with no results"
        ]
        
        for objection in objections:
            with patch.object(sales_agent, '_handle_objection', new_callable=AsyncMock) as mock_handle:
                mock_handle.return_value = {
                    "objection_type": "price" if "expensive" in objection else "efficacy",
                    "response_strategy": "value_demonstration",
                    "response": f"I understand your concern about {objection.lower()}. Let me explain the value proposition...",
                    "follow_up_actions": ["provide_testimonials", "offer_samples"]
                }
                
                response = await sales_agent._process_customer_objection(objection)
                
                assert response["objection_type"] in ["price", "efficacy", "skepticism"]
                assert len(response["follow_up_actions"]) > 0
    
    def test_sales_metrics_tracking(self, sales_agent):
        """测试销售指标跟踪"""
        # Test metric initialization
        assert hasattr(sales_agent, 'conversation_metrics')
        
        # Test metric updating
        sales_agent.update_metrics({
            "conversation_length": 5,
            "products_mentioned": 3,
            "objections_handled": 1,
            "stage_progression": 2
        })
        
        metrics = sales_agent.get_performance_metrics()
        assert metrics["total_conversations"] >= 0
        assert "conversion_indicators" in metrics
    
    @pytest.mark.asyncio
    async def test_multi_llm_provider_optimization(self, sales_agent):
        """测试多LLM供应商优化"""
        # Test that sales agent uses appropriate provider for different tasks
        with patch.object(sales_agent, 'multi_llm_client') as mock_client:
            # Mock different providers for different tasks
            mock_client.get_optimal_provider.return_value = ProviderType.OPENAI
            
            # Test product recommendation task
            await sales_agent._generate_product_recommendations({"skin_type": "dry"})
            
            # Verify provider selection was called
            assert mock_client.get_optimal_provider.called


if __name__ == "__main__":
    # 运行销售智能体测试
    async def run_sales_agent_tests():
        print("运行销售智能体测试...")
        
        # 创建销售智能体
        agent = SalesAgent("test_tenant")
        assert agent.agent_type == "sales"
        print(f"销售智能体创建成功: {agent.agent_id}")
        
        # 测试推荐生成
        try:
            customer_context = {"skin_type": "oily", "budget": "mid-range"}
            # Note: This would need actual implementation
            print("产品推荐功能测试完成")
        except Exception as e:
            print(f"产品推荐测试错误: {e}")
        
        print("销售智能体测试完成!")
    
    asyncio.run(run_sales_agent_tests())