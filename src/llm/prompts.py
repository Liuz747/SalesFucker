"""
提示模板管理

多智能体系统中所有智能体的集中式提示模板。
为不同类型的智能体提供一致的提示工程。
"""

from typing import Dict, Any, List
from string import Template


class PromptManager:
    """
    集中式提示模板管理器
    
    管理不同智能体和对话上下文的所有提示模板。
    支持动态模板替换和多租户定制。
    """
    
    def __init__(self):
        """初始化提示模板"""
        self.templates = self._load_prompt_templates()
    
    def _load_prompt_templates(self) -> Dict[str, Dict[str, str]]:
        """加载按智能体类型组织的所有提示模板"""
        return {
            "compliance": {
                "content_analysis": """你是化妆品行业营销的合规专家。

                分析以下客户消息的合规问题：
                - 监管违规（健康声明、医学术语）
                - 安全隐患（有害产品使用）
                - 不当内容（冒犯性语言、垃圾信息）

                客户消息："${customer_input}"

                以JSON格式回复：
                {
                    "status": "approved|flagged|blocked",
                    "violations": ["具体违规行为列表"],
                    "severity": "low|medium|high",
                    "user_message": "如果被拦截时给客户的友好解释",
                    "recommended_action": "建议采取的具体行动"
                }

                要全面但不过度限制。专注于真正的安全和监管问题。"""
            },
            
            "sales": {
                "consultation": """你是${brand_name}的专业美容顾问。
                                
                客户档案：
                - 肌肤类型：${skin_type}
                - 关注问题：${concerns}
                - 预算范围：${budget_range}
                - 过往购买：${purchase_history}

                对话历史：
                ${conversation_history}

                当前客户消息："${customer_input}"

                生成自然、有帮助的回复，要求：
                1. 针对他们的具体关切
                2. 适当推荐相关产品
                3. 保持${tone}语调（${tone_description}）
                4. 使用${strategy}销售方法
                5. 提出后续问题以更好了解需求

                保持对话自然、专业，专注于客户价值。""",
                
                "product_recommendation": """作为美容专家，基于客户分析推荐产品。

                客户分析：
                - 肌肤类型：${skin_type}
                - 主要关切：${main_concerns}
                - 生活方式：${lifestyle}
                - 预算偏好：${budget_preference}

                可用产品信息：${product_context}

                提供2-3个具体产品推荐，包含：
                1. 产品名称和主要功效
                2. 为什么适合他们的肌肤类型/关切
                3. 如何有效使用
                4. 预期效果和时间线

                专注于真正解决他们问题的产品。"""
            },
            
            "sentiment": {
                "emotion_analysis": """在美容咨询上下文中分析这条客户消息的情感色调和情绪。

                客户消息："${customer_input}"
                对话背景：${conversation_context}

                提供详细的情感分析，包括：
                1. 整体情绪（积极/消极/中性）
                2. 情感强度（1-10级）
                3. 检测到的具体情绪（兴奋、沮丧、困惑等）
                4. 客户满意度水平
                5. 紧迫或担忧程度

                以结构化JSON格式回复，便于处理。"""
            },
            
            "intent": {
                "classification": """
                分析客户的输入和对话历史，识别其主要意图、对话阶段，并提取详细的客户档案信息。
                
                客户输入："{customer_input}"
                对话历史：
                {conversation_history}

                提取以下信息：

                1. **主要意图**（选择一个）：
                - "product_inquiry": 询问特定产品或产品类别
                - "skin_concern_consultation": 寻求皮肤问题建议
                - "makeup_advice": 询问化妆技巧、色彩搭配或应用方法
                - "order_status": 查询现有订单状态
                - "return_policy": 询问退换货政策
                - "general_inquiry": 不符合其他类别的一般性问题
                - "purchase_intent": 表达购买准备或强烈兴趣
                - "browsing": 只是随便看看，没有特定的即时需求

                2. **对话阶段**（选择一个）：
                - "greeting": 初始欢迎
                - "need_assessment": 收集客户需求信息
                - "consultation": 提供详细建议或推荐
                - "product_education": 解释产品特性/好处
                - "objection_handling": 处理担忧（价格、怀疑）
                - "closing": 尝试促成销售
                - "support": 处理非销售相关查询

                3. **客户档案提取**（从上下文中分析和推断）：
                
                **肌肤关切**（列出所有提到、推断或暗示的）：
                - acne（痘痘）, dryness（干燥）, oiliness（油腻）, sensitivity（敏感）, aging（老化）, dark_spots（黑斑）, large_pores（毛孔粗大）, dullness（暗沉）, redness（红肿）, uneven_texture（纹理不均）
                
                **产品兴趣**（他们想购买/了解的）：
                - skincare（护肤）, makeup（化妆品）, sunscreen（防晒霜）, anti_aging（抗衰老）, acne_treatment（痘痘治疗）, moisturizers（保湿霜）, cleansers（洁面乳）, serums（精华）, foundations（粉底）
                
                **肌肤类型指标**（提到或直接推断的）：
                - oily（油性）, dry（干性）, combination（混合性）, sensitive（敏感性）, normal（正常）, mature（成熟）
                
                **紧迫程度**：
                - low（浏览/研究），medium（计划购买），high（即时需求），critical（特殊事件/紧急）
                
                **预算信号**（提到或从语言推断的）：
                - budget_conscious（预算意识）, value_focused（注重性价比）, luxury_oriented（奢侈品倾向）, price_sensitive（价格敏感）, premium_seeking（追求高端）
                
                **经验水平**（美容产品使用经验）：
                - beginner（初学者）, intermediate（中级）, advanced（高级）, expert（专家）

                提供结构化JSON响应：
                {{
                  "intent": "主要意图",
                  "confidence": 0.85,
                  "conversation_stage": "对话阶段",
                  "customer_profile": {{
                    "skin_concerns": ["关切1", "关切2"],
                    "skin_concerns_confidence": [0.9, 0.7],
                    "product_interests": ["兴趣1", "兴趣2"],
                    "skin_type_indicators": ["类型1"],
                    "urgency": "medium",
                    "budget_signals": ["信号1"],
                    "experience_level": "intermediate"
                  }},
                  "extraction_confidence": 0.82,
                  "reasoning": "分析和发现的关键指标的简要解释"
                }}
                """
            }
        }
    
    def get_prompt(self, agent_type: str, prompt_type: str, **kwargs) -> str:
        """
        获取格式化的提示模板
        
        参数：
            agent_type: 智能体类型（compliance、sales、sentiment、intent）
            prompt_type: 智能体类型内的具体提示
            **kwargs: 模板替换变量
            
        返回：
            str: 格式化的提示模板
        """
        if agent_type not in self.templates:
            raise ValueError(f"未知的智能体类型: {agent_type}")
            
        agent_templates = self.templates[agent_type]
        if prompt_type not in agent_templates:
            raise ValueError(f"智能体'{agent_type}'的未知提示类型'{prompt_type}'")
        
        template = Template(agent_templates[prompt_type])
        
        # 为缺失变量提供安全默认值
        safe_kwargs = {
            "customer_input": "",
            "conversation_history": "没有先前对话",
            "brand_name": "我们的品牌",
            "skin_type": "未指定",
            "concerns": "未指定", 
            "budget_range": "未指定",
            "purchase_history": "无",
            "tone": "友好",
            "tone_description": "温暖且专业",
            "strategy": "咨询式",
            "conversation_context": "初始咨询",
            "previous_intent": "未知",
            **kwargs
        }
        
        return template.safe_substitute(**safe_kwargs)
    
    def format_conversation_history(self, history: List[str], max_entries: int = 5) -> str:
        """
        格式化对话历史以包含在提示中
        
        参数：
            history: 对话消息列表
            max_entries: 要包含的最近条目的最大数量
            
        返回：
            str: 格式化的对话历史
        """
        if not history:
            return "没有先前对话"
            
        recent_history = history[-max_entries:] if len(history) > max_entries else history
        return "\n".join(f"- {msg}" for msg in recent_history)


# 全局提示管理器实例
_prompt_manager: PromptManager = None


def get_prompt_manager() -> PromptManager:
    """获取或创建全局提示管理器实例"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager