"""
销售对话模板管理模块

该模块包含化妆品销售智能体的对话模板。
专注于模板数据管理，保持语调一致性。

核心功能:
- 化妆品销售对话模板
- 多场景模板管理
- 个性化语调支持
- 租户特定模板
"""

from typing import Dict, Any


def get_conversation_templates() -> Dict[str, Dict[str, str]]:
    """
    获取销售对话模板集合
    
    返回:
        Dict[str, Dict[str, str]]: 按场景分组的模板字典
    """
    return {
        "greeting": {
            "new_customer": "Hi there! Welcome! I'm so excited to help you find the perfect beauty products today. What brings you in? Are you looking for something specific, or would you like me to help you discover some amazing new favorites?",
            "returning_customer": "Hi {customer_name}! So wonderful to see you again! I remember you loved that {previous_product} we picked out last time. How did that work out for you? What can I help you find today?",
            "premium_greeting": "Good day! I'm delighted you've chosen to explore our premium collection today. I'm here to provide you with personalized recommendations that will perfectly complement your unique beauty style. How may I assist you?",
            "youth_greeting": "Hey! Welcome to our amazing world of beauty! I'm super excited to help you find some incredible products that are totally trending right now. What kind of look are you going for?"
        },
        
        "need_assessment": {
            "skin_concerns": "I'd love to learn more about your skin so I can give you the best recommendations. What's your main skin concern right now? Are you dealing with dryness, oiliness, sensitivity, or maybe looking to address some specific areas?",
            "skin_type": "Let's talk about your skin type - would you describe it as more on the oily, dry, combination, or sensitive side? This will help me suggest products that work perfectly with your natural skin.",
            "routine_inquiry": "Tell me about your current routine - are you someone who loves a full skincare ritual, or do you prefer something quick and simple? I want to make sure we find products that fit your lifestyle.",
            "color_matching": "For makeup, I'd love to help you find your perfect shades. Are you looking for everyday natural looks, or do you like to experiment with bolder colors? And what's your undertone preference?"
        },
        
        "consultation": {
            "skin_analysis": "Based on what you've told me about your {skin_type} skin and {concerns}, I have some fantastic options that would work beautifully for you. Let me walk you through a few products that I think you'll absolutely love.",
            "product_education": "Let me tell you about this amazing {product_name} - it's one of my personal favorites! What makes it special is {key_benefits}. It's perfect for {skin_type} like yours, and I've seen incredible results with customers who have similar concerns.",
            "shade_consultation": "For your {undertone} undertones and {skin_tone} complexion, I'm thinking this {shade_name} would be absolutely stunning on you. Want to try it and see how it looks?"
        },
        
        "objection_handling": {
            "price_concern": "I totally understand wanting to make sure you're getting great value! What I love about this product is that a little goes a really long way, so it's actually quite economical. Plus, investing in quality products that work well for your skin saves you money in the long run because you're not constantly trying new things that don't work.",
            "skepticism": "I completely get being cautious about trying new products - it shows you really care about your skin! That's exactly why I love recommending this brand. They offer a satisfaction guarantee, so if it doesn't work out, you can return it. But honestly, I'm confident you're going to love the results!",
            "overwhelming_choice": "I know it can feel overwhelming with so many options! That's exactly why I'm here - to help narrow it down to what will work best for YOU specifically. Let's start with just one or two key products that address your main concerns, and we can always build from there."
        },
        
        "closing": {
            "confident_close": "I'm so excited for you to try these! Based on everything we've talked about, I really think these products are going to work beautifully for you. Should we get you started with these today?",
            "gentle_close": "What do you think? Do any of these feel like they might be a good fit for what you're looking for?",
            "benefit_summary": "So just to recap - this routine will help with {main_concern}, give you that {desired_result} you mentioned, and fit perfectly into your {lifestyle} lifestyle. Ready to give it a try?"
        }
    }


def get_conversation_responses() -> Dict[str, str]:
    """
    获取常用对话响应模板
    
    返回:
        Dict[str, str]: 响应模板字典
    """
    return {
        "benefits_focus": "What I love about this product is how it delivers {specific_benefit}. Customers with {skin_type} skin like yours consistently tell me they see {expected_result} within {timeframe}. It's become one of our bestsellers for that exact reason!",
        
        "ingredient_highlight": "The key ingredient that makes this so effective is {key_ingredient}. It's known for {ingredient_benefit}, which is exactly what you need for {customer_concern}. The formula is also {formulation_benefit}, so it works well even with sensitive skin.",
        
        "usage_guidance": "For best results, I recommend using this {frequency} as part of your {routine_time} routine. Just {application_method}, and you should start seeing {timeline} results. It pairs beautifully with {complementary_product} if you want to maximize the benefits!",
        
        "social_proof": "This is actually one of our most popular products - so many customers come back specifically for this! Just last week, a customer with similar skin concerns told me it completely transformed her routine. The reviews speak for themselves!",
        
        "personalization": "What makes this perfect for you specifically is {personal_factor}. Given that you mentioned {customer_need}, this addresses exactly that while also {additional_benefit}. It's like it was made for your skin type!"
    }


def get_tone_variations() -> Dict[str, Dict[str, str]]:
    """
    获取不同语调的模板变体
    
    返回:
        Dict[str, Dict[str, str]]: 按语调分组的模板变体
    """
    return {
        "sophisticated": {
            "greeting": "Good day! I'm delighted to assist you in finding the perfect beauty solutions today.",
            "recommendation": "I would highly recommend this exceptional {product} for your particular needs.",
            "closing": "I believe these selections will serve you exceptionally well."
        },
        
        "energetic": {
            "greeting": "Hey! I'm so excited to help you find some amazing products today!",
            "recommendation": "Oh my gosh, you're going to LOVE this {product}! It's absolutely perfect for you!",
            "closing": "I'm honestly so excited for you to try these - they're going to be incredible!"
        },
        
        "professional": {
            "greeting": "Hello! I'm here to help you find the right products for your beauty needs.",
            "recommendation": "Based on your requirements, this {product} would be an excellent choice.",
            "closing": "These products should effectively address your concerns."
        },
        
        "warm": {
            "greeting": "Hi there! I'm so happy to help you today - what brings you in?",
            "recommendation": "I think you're really going to love this {product} - it's been wonderful for customers like you!",
            "closing": "I'm confident these will work beautifully for you!"
        }
    } 