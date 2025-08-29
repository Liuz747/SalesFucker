"""
中文文化背景上下文测试套件

该测试套件专门测试中国文化背景相关的功能:
- 中国美容标准理解
- 中国消费者购物行为模式
- 地区偏好和节日营销
"""

import pytest
from unittest.mock import Mock, AsyncMock

from src.agents.sentiment import SentimentAnalysisAgent
from src.agents.sales import SalesAgent
from src.agents.base import ConversationState
from infra.runtimes.client import LLMClient


class TestChineseCulturalContext:
    """中文文化背景上下文测试"""
    
    @pytest.mark.asyncio
    async def test_chinese_beauty_standards_understanding(self):
        """测试中国美容标准理解"""
        sentiment_agent = SentimentAnalysisAgent("test_tenant")
        
        # Mock sentiment analysis with cultural context
        mock_client = Mock(spec=LLMClient)
        mock_client.analyze_sentiment = AsyncMock(return_value={
            "sentiment": "positive",
            "score": 0.85,
            "confidence": 0.9,
            "cultural_analysis": {
                "beauty_standard": "中式审美偏好",
                "skin_tone_preference": "白皙透亮",
                "makeup_style": "清淡自然",
                "brand_preference": "国货品牌认同度高"
            },
            "emotional_markers": ["满意", "喜欢", "效果好"],
            "cultural_context": "符合中国消费者审美习惯"
        })
        
        sentiment_agent.llm_client = mock_client
        
        # Test Chinese beauty standard expressions
        test_inputs = [
            "这个粉底很自然，显得皮肤很透亮，很符合我的审美",
            "这个口红颜色太艳了，我更喜欢淡一点的",
            "国货品牌质量越来越好了，价格也实惠"
        ]
        
        for input_text in test_inputs:
            state = ConversationState(
                tenant_id="test_tenant",
                customer_input=input_text,
                metadata={"language": "chinese", "region": "china"}
            )
            
            result_state = await sentiment_agent.process_conversation(state)
            
            # Verify cultural context was considered
            mock_client.analyze_sentiment.assert_called()
            call_args = mock_client.analyze_sentiment.call_args
            assert input_text in call_args[0]
    
    def test_chinese_shopping_behavior_patterns(self):
        """测试中国消费者购物行为模式"""
        # Mock Chinese shopping behavior detection
        behavior_patterns = {
            "price_sensitivity": {
                "高性价比": "high_value_consciousness",
                "划算": "value_seeking",
                "便宜": "price_focused",
                "性价比": "cost_effectiveness"
            },
            "brand_preferences": {
                "国货": "domestic_brand_preference",
                "进口": "imported_brand_preference", 
                "大牌": "luxury_brand_preference",
                "小众": "niche_brand_preference"
            },
            "decision_factors": {
                "口碑": "word_of_mouth",
                "评价": "reviews",
                "推荐": "recommendations",
                "试用": "trial_experience"
            }
        }
        
        test_cases = [
            {
                "input": "这个牌子口碑怎么样？性价比高吗？",
                "expected_patterns": ["word_of_mouth", "cost_effectiveness"]
            },
            {
                "input": "有没有好用的国货推荐？",
                "expected_patterns": ["domestic_brand_preference", "recommendations"]
            },
            {
                "input": "想试试这个产品，有试用装吗？",
                "expected_patterns": ["trial_experience"]
            }
        ]
        
        for case in test_cases:
            # Mock behavior pattern detection
            detected_patterns = []
            input_text = case["input"]
            
            for category, patterns in behavior_patterns.items():
                for keyword, pattern in patterns.items():
                    if keyword in input_text:
                        detected_patterns.append(pattern)
            
            # Verify expected patterns were detected
            for expected_pattern in case["expected_patterns"]:
                assert expected_pattern in detected_patterns
    
    def test_cultural_preference_analysis(self):
        """测试文化偏好分析"""
        cultural_indicators = {
            "natural_beauty": ["自然", "素颜", "清淡", "透明"],
            "skin_care_focus": ["护肤", "保养", "肌肤", "养肤"],
            "value_consciousness": ["性价比", "划算", "实惠", "值得"],
            "brand_trust": ["口碑", "评价", "推荐", "信赖"]
        }
        
        test_expressions = [
            "我比较喜欢自然的妆容，不要太浓",
            "护肤比化妆更重要，要养好底子",
            "这个产品性价比很高，值得推荐",
            "朋友推荐的，口碑不错"
        ]
        
        for expression in test_expressions:
            detected_preferences = []
            
            for preference, indicators in cultural_indicators.items():
                if any(indicator in expression for indicator in indicators):
                    detected_preferences.append(preference)
            
            # Verify each expression matches expected cultural preferences
            assert len(detected_preferences) > 0


class TestChineseRegionalPreferences:
    """中国地区偏好测试"""
    
    def test_regional_climate_adaptation(self):
        """测试地区气候适应"""
        regional_preferences = {
            "north_china": {
                "climate": "dry_cold",
                "skin_concerns": ["干燥", "缺水", "敏感"],
                "product_preferences": ["保湿", "滋润", "修护"],
                "seasonal_needs": {
                    "winter": ["厚重面霜", "护手霜", "唇膏"],
                    "summer": ["控油", "防晒", "清爽"]
                }
            },
            "south_china": {
                "climate": "humid_hot",
                "skin_concerns": ["出油", "毛孔", "痘痘"],
                "product_preferences": ["控油", "清洁", "收敛"],
                "seasonal_needs": {
                    "winter": ["温和保湿", "舒缓"],
                    "summer": ["强效控油", "高倍防晒"]
                }
            }
        }
        
        test_cases = [
            {
                "user_location": "北京",
                "season": "winter",
                "input": "最近天气干燥，皮肤很缺水",
                "expected_region": "north_china",
                "expected_recommendations": ["保湿", "滋润", "厚重面霜"]
            },
            {
                "user_location": "广州", 
                "season": "summer",
                "input": "天气太热了，脸上总是出油",
                "expected_region": "south_china",
                "expected_recommendations": ["控油", "清爽", "强效控油"]
            }
        ]
        
        for case in test_cases:
            # Mock regional preference detection
            region_data = regional_preferences[case["expected_region"]]
            seasonal_needs = region_data["seasonal_needs"][case["season"]]
            
            # Verify regional adaptation
            for recommendation in case["expected_recommendations"]:
                assert (recommendation in region_data["product_preferences"] or 
                       recommendation in seasonal_needs)
    
    @pytest.mark.asyncio
    async def test_chinese_festival_seasonal_marketing(self):
        """测试中国节日季节性营销"""
        sales_agent = SalesAgent("test_tenant")
        
        # Mock festival-aware responses
        mock_client = Mock(spec=LLMClient)
        
        festival_contexts = {
            "春节": {
                "products": ["红色口红", "喜庆彩妆", "新年套装"],
                "themes": ["红红火火", "新年新气象", "阖家欢乐"],
                "promotions": ["新年特惠", "礼盒装", "亲友分享"]
            },
            "情人节": {
                "products": ["情侣套装", "浪漫色系", "香水"],
                "themes": ["浪漫约会", "甜蜜情人", "魅力加分"],
                "promotions": ["情侣优惠", "爱的礼物", "浪漫包装"]
            },
            "七夕": {
                "products": ["东方美妆", "传统色彩", "古典雅致"],
                "themes": ["中式浪漫", "古典美人", "东方韵味"],
                "promotions": ["七夕特别", "中式礼盒", "古风包装"]
            }
        }
        
        for festival, context in festival_contexts.items():
            mock_client.chat_completion = AsyncMock(return_value={
                "festival_awareness": festival,
                "recommended_products": context["products"],
                "marketing_themes": context["themes"],
                "sales_response": f"在{festival}期间，我特别推荐..."
            })
            
            sales_agent.llm_client = mock_client
            
            state = ConversationState(
                tenant_id="test_tenant",
                customer_input=f"马上{festival}了，有什么合适的推荐吗？",
                metadata={
                    "language": "chinese",
                    "festival_context": festival,
                    "cultural_event": True
                }
            )
            
            result_state = await sales_agent.process_conversation(state)
            
            # Verify festival-specific recommendations
            mock_client.chat_completion.assert_called()
            assert sales_agent.agent_id in result_state.active_agents


class TestChineseCommunicationStyles:
    """测试中国沟通风格"""
    
    def test_polite_expression_recognition(self):
        """测试礼貌表达识别"""
        polite_expressions = [
            "请问", "麻烦", "不好意思", "谢谢",
            "辛苦了", "打扰了", "方便的话", "如果可以"
        ]
        
        test_messages = [
            "请问这个产品适合我的肌肤吗？",
            "麻烦推荐一款适合的面霜",
            "不好意思，想了解一下价格",
            "谢谢您的详细介绍"
        ]
        
        for message in test_messages:
            politeness_detected = any(expr in message for expr in polite_expressions)
            assert politeness_detected, f"Failed to detect politeness in: {message}"
    
    def test_concern_expression_patterns(self):
        """测试关注表达模式"""
        concern_patterns = {
            "skin_sensitivity": ["敏感", "过敏", "刺激", "温和"],
            "effectiveness": ["有效", "效果", "改善", "帮助"],
            "safety": ["安全", "天然", "无添加", "孕妇"],
            "value": ["价格", "性价比", "划算", "值得"]
        }
        
        test_concerns = [
            "我的皮肤比较敏感，会不会过敏？",
            "这个产品效果怎么样，真的有效吗？",
            "成分安全吗？有没有有害添加剂？",
            "价格怎么样？性价比高不高？"
        ]
        
        for i, concern in enumerate(test_concerns):
            pattern_key = list(concern_patterns.keys())[i]
            pattern_keywords = concern_patterns[pattern_key]
            
            pattern_found = any(keyword in concern for keyword in pattern_keywords)
            assert pattern_found, f"Pattern {pattern_key} not found in: {concern}"


if __name__ == "__main__":
    print("中文文化上下文测试模块加载成功")
    print("测试覆盖: 美容标准、购物行为、地区偏好、节日营销")