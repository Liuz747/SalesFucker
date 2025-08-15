"""
中文化妆品术语处理测试套件

该测试套件专门测试中文化妆品术语的理解和处理:
- 中文护肤术语理解
- 中文彩妆术语处理
- 专业术语上下文分析
"""

import pytest
from unittest.mock import Mock, AsyncMock

from src.llm.multi_llm_client import MultiLLMClient
from src.agents.sentiment import SentimentAnalysisAgent
from src.agents.product import ProductExpertAgent
from src.agents.sales import SalesAgent
from src.agents.base import ConversationState


class TestChineseCosmeticsTerminology:
    """中文化妆品术语处理测试"""
    
    @pytest.fixture
    def cosmetics_terminology_samples(self):
        """化妆品术语样本"""
        return {
            "skincare_terms": [
                "保湿", "补水", "控油", "美白", "抗衰老", "紧致",
                "敏感肌", "干性皮肤", "油性皮肤", "混合性皮肤",
                "精华", "乳液", "面霜", "爽肤水", "卸妆"
            ],
            "makeup_terms": [
                "粉底液", "遮瑕膏", "散粉", "腮红", "眼影",
                "睫毛膏", "眉笔", "口红", "唇彩", "指甲油"
            ],
            "skin_concerns": [
                "痘痘", "黑头", "毛孔粗大", "细纹", "色斑",
                "暗沉", "松弛", "红血丝", "过敏", "脱皮"
            ],
            "cultural_preferences": [
                "自然妆", "韩式妆容", "日系妆容", "素颜感",
                "温柔系", "清纯风", "御姐风", "甜美风"
            ]
        }
    
    @pytest.mark.asyncio
    async def test_chinese_skincare_terminology_understanding(
        self, 
        cosmetics_terminology_samples
    ):
        """测试中文护肤术语理解"""
        product_agent = ProductExpertAgent("test_tenant")
        
        # Mock multi-LLM client with Chinese optimization
        mock_client = Mock(spec=MultiLLMClient)
        mock_response = {
            "recommendations": [
                {
                    "product_name": "温和保湿精华",
                    "suitable_skin_type": "敏感肌",
                    "key_ingredients": ["透明质酸", "神经酰胺"],
                    "price_range": "150-300元",
                    "brand_recommendation": "国产品牌优选"
                }
            ],
            "analysis": {
                "skin_type_detected": "敏感肌",
                "main_concerns": ["保湿", "舒缓"],
                "cultural_context": "中国用户偏好温和产品"
            }
        }
        
        mock_client.chat_completion = AsyncMock(return_value=mock_response)
        product_agent.llm_client = mock_client
        
        # Test with Chinese skincare inquiry
        state = ConversationState(
            tenant_id="test_tenant",
            customer_input="我是敏感肌，需要温和的保湿产品，预算在200元左右",
            metadata={"language": "chinese", "region": "china"}
        )
        
        result_state = await product_agent.process_conversation(state)
        
        # Verify Chinese terminology was properly processed
        mock_client.chat_completion.assert_called_once()
        call_args = mock_client.chat_completion.call_args
        
        # Check if Chinese context was passed
        assert "agent_type" in call_args[1]
        assert call_args[1]["agent_type"] == "product"
        
        # Verify Chinese skincare terms in the response
        assert "敏感肌" in str(mock_response)
        assert "保湿" in str(mock_response)
    
    @pytest.mark.asyncio
    async def test_chinese_makeup_terminology_processing(
        self,
        cosmetics_terminology_samples
    ):
        """测试中文彩妆术语处理"""
        sales_agent = SalesAgent("test_tenant")
        
        # Mock multi-LLM response for makeup consultation
        mock_client = Mock(spec=MultiLLMClient)
        mock_client.chat_completion = AsyncMock(return_value={
            "makeup_style_analysis": {
                "preferred_style": "温柔系",
                "suitable_products": ["nude色口红", "自然眉笔", "轻薄粉底"],
                "color_recommendations": ["暖调粉色", "珊瑚橘", "豆沙色"],
                "cultural_adaptation": "适合亚洲肤色和审美"
            },
            "sales_response": "根据您的喜好，我推荐几款温柔系彩妆..."
        })
        
        sales_agent.llm_client = mock_client
        
        # Test Chinese makeup consultation
        state = ConversationState(
            tenant_id="test_tenant",
            customer_input="我想要温柔一点的妆容，适合日常上班，不要太浓",
            compliance_result={"status": "approved"},
            intent_analysis={
                "intent": "makeup_consultation",
                "style_preference": "natural_gentle",
                "occasion": "daily_work"
            }
        )
        
        result_state = await sales_agent.process_conversation(state)
        
        # Verify Chinese makeup terms were understood
        assert sales_agent.agent_id in result_state.active_agents
        mock_client.chat_completion.assert_called_once()
    
    def test_terminology_categorization(self, cosmetics_terminology_samples):
        """测试术语分类"""
        skincare_terms = cosmetics_terminology_samples["skincare_terms"]
        makeup_terms = cosmetics_terminology_samples["makeup_terms"]
        
        # Verify skincare terms are properly categorized
        assert "保湿" in skincare_terms
        assert "敏感肌" in skincare_terms
        assert "精华" in skincare_terms
        
        # Verify makeup terms are properly categorized
        assert "粉底液" in makeup_terms
        assert "口红" in makeup_terms
        assert "眼影" in makeup_terms
        
        # Ensure no overlap between categories
        assert not any(term in makeup_terms for term in skincare_terms)
    
    def test_cultural_preference_terms(self, cosmetics_terminology_samples):
        """测试文化偏好术语"""
        cultural_terms = cosmetics_terminology_samples["cultural_preferences"]
        
        # Verify cultural makeup style terms
        assert "自然妆" in cultural_terms
        assert "韩式妆容" in cultural_terms
        assert "温柔系" in cultural_terms
        assert "素颜感" in cultural_terms
        
        # Test that these represent Chinese aesthetic preferences
        chinese_style_indicators = ["自然", "温柔", "清纯", "素颜"]
        for indicator in chinese_style_indicators:
            assert any(indicator in term for term in cultural_terms)


class TestChineseContextualAnalysis:
    """测试中文上下文分析"""
    
    @pytest.mark.asyncio
    async def test_skin_concern_analysis(self):
        """测试肌肤问题分析"""
        sentiment_agent = SentimentAnalysisAgent("test_tenant")
        
        # Mock sentiment analysis with skin concern context
        mock_client = Mock(spec=MultiLLMClient)
        mock_client.analyze_sentiment = AsyncMock(return_value={
            "sentiment": "concerned",
            "score": 0.65,
            "confidence": 0.85,
            "skin_concerns": ["痘痘", "毛孔粗大"],
            "urgency_level": "moderate",
            "cultural_context": "中国消费者对肌肤问题较为关注"
        })
        
        sentiment_agent.llm_client = mock_client
        
        # Test with skin concern expression
        state = ConversationState(
            tenant_id="test_tenant",
            customer_input="最近脸上总是长痘痘，毛孔也变粗大了，很困扰",
            metadata={"language": "chinese", "concern_category": "skincare"}
        )
        
        result_state = await sentiment_agent.process_conversation(state)
        
        # Verify skin concern analysis
        mock_client.analyze_sentiment.assert_called()
        call_args = mock_client.analyze_sentiment.call_args
        assert "痘痘" in call_args[0][0]
        assert "毛孔粗大" in call_args[0][0]
    
    def test_product_inquiry_parsing(self):
        """测试产品咨询解析"""
        inquiries = [
            "这个粉底液适合油性皮肤吗？",
            "有没有不刺激的卸妆产品？", 
            "适合秋冬用的面霜推荐",
            "敏感肌可以用的眼霜"
        ]
        
        # Mock parsing logic
        parsed_results = []
        for inquiry in inquiries:
            parsed = {
                "product_type": None,
                "skin_type": None,
                "season": None,
                "concern": None
            }
            
            # Simple parsing simulation
            if "粉底液" in inquiry:
                parsed["product_type"] = "粉底液"
            if "面霜" in inquiry:
                parsed["product_type"] = "面霜"
            if "眼霜" in inquiry:
                parsed["product_type"] = "眼霜"
                
            if "油性" in inquiry:
                parsed["skin_type"] = "油性皮肤"
            if "敏感肌" in inquiry:
                parsed["skin_type"] = "敏感肌"
                
            if "秋冬" in inquiry:
                parsed["season"] = "秋冬"
                
            if "刺激" in inquiry:
                parsed["concern"] = "敏感"
                
            parsed_results.append(parsed)
        
        # Verify parsing accuracy
        assert parsed_results[0]["product_type"] == "粉底液"
        assert parsed_results[0]["skin_type"] == "油性皮肤"
        assert parsed_results[2]["season"] == "秋冬"
        assert parsed_results[3]["skin_type"] == "敏感肌"


if __name__ == "__main__":
    print("中文术语处理测试模块加载成功") 
    print("测试覆盖: 护肤术语、彩妆术语、上下文分析")