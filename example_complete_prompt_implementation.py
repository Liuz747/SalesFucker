#!/usr/bin/env python3
"""
完整提示词实现示例

展示修复后的提示词架构的最佳实践：
- ✅ 无外部客户端依赖
- ✅ 使用内部PromptHandler（当可用时）
- ✅ 优雅降级到默认模板
- ✅ 智能体特定的提示词方法
- ✅ 上下文变量集成
"""

import asyncio
import sys
import os
from typing import Dict, Any, Optional

# 确保可以导入项目模块
sys.path.insert(0, os.path.dirname(__file__))

from src.prompts import get_prompt_manager
from src.agents.base.agent import BaseAgent
from src.agents.base.message import AgentMessage, ThreadState

class ExampleSalesAgent(BaseAgent):
    """
    示例销售智能体 - 展示正确的提示词实现模式
    """
    
    def __init__(self, tenant_id: str):
        super().__init__(
            agent_id=f"sales_demo_{tenant_id}",
            tenant_id=tenant_id
        )
        
        # 预加载提示词以提高性能
        asyncio.create_task(self.preload_prompts())
        
        self.logger.info(f"示例销售智能体创建完成: {self.agent_id}")
    
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """处理消息（必须实现的抽象方法）"""
        return await self.send_message(
            recipient=message.sender,
            message_type="response",
            payload={"response": "处理完成"},
            context=message.context
        )
    
    async def process_conversation(self, state: ThreadState) -> ThreadState:
        """处理对话状态（必须实现的抽象方法）"""
        return state
    
    # ===== 销售智能体特定提示词方法 =====
    
    async def get_greeting_message(self, context: Optional[Dict[str, Any]] = None) -> str:
        """
        获取个性化问候消息
        
        实现要点:
        1. 使用继承的_prompt_manager
        2. 提供有意义的降级处理
        3. 上下文变量集成
        4. 错误处理和日志记录
        """
        try:
            if hasattr(self, '_prompt_manager') and self._prompt_manager:
                greeting = await self._prompt_manager.get_greeting_prompt(
                    agent_id=self.agent_id,
                    agent_type=self.agent_type,
                    tenant_id=self.tenant_id or "default",
                    context=context or {}
                )
                if greeting:
                    self.logger.debug(f"使用系统问候模板: {len(greeting)}字符")
                    return greeting
            
            # 优雅降级：基于上下文的问候语
            agent_name = context.get('agent_name', '美妆顾问') if context else '美妆顾问'
            customer_name = context.get('customer_name', '') if context else ''
            time_greeting = self._get_time_greeting(context)
            
            if customer_name:
                return f"{time_greeting}{customer_name}！我是您的专属{agent_name}，很高兴为您服务！请问今天想了解什么产品呢？"
            else:
                return f"{time_greeting}我是您的专属{agent_name}，很高兴为您服务！请问有什么可以帮助您的吗？"
                
        except Exception as e:
            self.logger.warning(f"获取问候消息失败: {e}")
            return "您好！欢迎来到我们的美妆专柜，有什么可以帮助您的吗？"
    
    async def get_product_recommendation_template(self, context: Dict[str, Any]) -> str:
        """
        获取产品推荐模板
        
        展示更复杂的上下文处理和降级策略
        """
        try:
            if hasattr(self, '_prompt_manager') and self._prompt_manager:
                recommendation = await self._prompt_manager.get_product_recommendation_prompt(
                    agent_id=self.agent_id,
                    agent_type=self.agent_type,
                    tenant_id=self.tenant_id or "default",
                    context=context
                )
                if recommendation:
                    self.logger.debug(f"使用系统推荐模板: {len(recommendation)}字符")
                    return recommendation
            
            # 智能降级：基于客户需求的个性化推荐
            return self._build_intelligent_recommendation(context)
            
        except Exception as e:
            self.logger.warning(f"获取推荐模板失败: {e}")
            return self._build_basic_recommendation(context)
    
    async def handle_customer_objection(self, objection_type: str, context: Dict[str, Any]) -> str:
        """
        处理客户异议 - 展示自定义提示词类型的使用
        """
        try:
            if hasattr(self, '_prompt_manager') and self._prompt_manager:
                # 使用新增的get_custom_prompt方法
                objection_prompt = await self._prompt_manager.get_custom_prompt(
                    prompt_type='objection_handling',
                    agent_id=self.agent_id,
                    agent_type=self.agent_type,
                    tenant_id=self.tenant_id or "default",
                    context={'objection_type': objection_type, **context}
                )
                
                if objection_prompt:
                    self.logger.debug(f"使用系统异议处理模板: {objection_type}")
                    return objection_prompt
            
            # 降级到内置异议处理策略
            return self._handle_objection_fallback(objection_type, context)
            
        except Exception as e:
            self.logger.warning(f"处理异议失败 {objection_type}: {e}")
            return "我理解您的顾虑，让我们一起来讨论一下，看看如何更好地满足您的需求。"
    
    # ===== 私有辅助方法 =====
    
    def _get_time_greeting(self, context: Optional[Dict[str, Any]]) -> str:
        """根据时间生成合适的问候语"""
        if not context or 'time_of_day' not in context:
            return "您好！"
        
        time_of_day = context['time_of_day'].lower()
        if time_of_day in ['早上', 'morning']:
            return "早上好！"
        elif time_of_day in ['下午', 'afternoon']:
            return "下午好！"
        elif time_of_day in ['晚上', 'evening']:
            return "晚上好！"
        else:
            return "您好！"
    
    def _build_intelligent_recommendation(self, context: Dict[str, Any]) -> str:
        """构建智能推荐模板"""
        skin_type = context.get('skin_type', '您的肌肤')
        concerns = context.get('skin_concerns', '肌肤问题')
        budget = context.get('budget_range', '您的预算')
        
        return f"""基于您{skin_type}的特点和{concerns}的需求，我为您精心挑选了以下产品：

{{product_recommendations}}

推荐理由：
• 这些产品特别适合{skin_type}
• 能够有效改善{concerns}
• 符合{budget}的预算考虑
• 经过客户验证效果显著

让我为您详细介绍每个产品的特点和使用方法..."""
    
    def _build_basic_recommendation(self, context: Dict[str, Any]) -> str:
        """构建基础推荐模板"""
        return "根据您的需求，我为您推荐以下产品，它们都是我们的明星产品，效果非常好..."
    
    def _handle_objection_fallback(self, objection_type: str, context: Dict[str, Any]) -> str:
        """处理异议的降级策略"""
        objection_responses = {
            'price': '我理解您对价格的考虑。让我为您解释一下这个产品的超高性价比...',
            'quality': '您的担心很有道理。让我为您详细介绍产品的品质保证和客户反馈...',
            'need': '我明白您可能觉得不太需要。让我们一起分析一下您的具体情况...',
            'trust': '建立信任确实需要时间。让我为您展示一些真实的客户使用效果...',
            'timing': '时机确实很重要。让我们看看什么时候开始使用效果最佳...'
        }
        
        return objection_responses.get(objection_type, '我理解您的顾虑，让我们一起来找到最适合您的解决方案。')

async def demonstrate_complete_implementation():
    """完整实现演示"""
    print("🏗️  完整提示词实现演示")
    print("=" * 60)
    
    # 1. 创建智能体实例
    agent = ExampleSalesAgent(tenant_id="demo_brand")
    print(f"✅ 智能体创建: {agent.agent_id}")
    print(f"   类型: {agent.agent_type}")
    print(f"   租户: {agent.tenant_id}")
    
    # 2. 演示问候消息
    print("\\n📝 1. 问候消息演示")
    print("-" * 30)
    
    contexts = [
        {'agent_name': '小美', 'time_of_day': '早上'},
        {'agent_name': '小雅', 'customer_name': '张小姐', 'time_of_day': '下午'},
        {'agent_name': '小丽'}  # 无时间信息
    ]
    
    for i, context in enumerate(contexts, 1):
        greeting = await agent.get_greeting_message(context)
        print(f"   场景{i}: {greeting}")
    
    # 3. 演示产品推荐
    print("\\n🎯 2. 产品推荐演示")
    print("-" * 30)
    
    recommendation_contexts = [
        {
            'skin_type': '油性肌肤',
            'skin_concerns': '毛孔粗大',
            'budget_range': '300-500元',
            'lifestyle': '上班族'
        },
        {
            'skin_type': '干性肌肤',
            'skin_concerns': '细纹和暗沉',
            'budget_range': '800-1200元',
            'lifestyle': '家庭主妇'
        }
    ]
    
    for i, context in enumerate(recommendation_contexts, 1):
        recommendation = await agent.get_product_recommendation_template(context)
        print(f"   推荐{i}: {recommendation[:150]}...")
    
    # 4. 演示异议处理
    print("\\n💬 3. 异议处理演示")
    print("-" * 30)
    
    objection_scenarios = [
        ('price', {'customer_concern': '太贵了', 'product_price': '699元'}),
        ('quality', {'customer_concern': '效果真的有那么好吗？'}),
        ('trust', {'customer_concern': '这个品牌我没听过'})
    ]
    
    for objection_type, context in objection_scenarios:
        response = await agent.handle_customer_objection(objection_type, context)
        print(f"   {objection_type}异议: {response}")
    
    print("\\n" + "=" * 60)
    print("🎉 完整提示词架构实现成功！")
    print("\\n💡 关键实现原则:")
    print("  1️⃣  BaseAgent只提供通用preload_prompts()方法")
    print("  2️⃣  具体智能体实现自己的提示词方法")
    print("  3️⃣  优先使用系统提示词，优雅降级到智能逻辑")
    print("  4️⃣  充分利用上下文变量进行个性化")
    print("  5️⃣  完整的错误处理和日志记录")
    print("  6️⃣  支持租户自定义与默认模板的无缝集成")
    print("\\n🏆 系统现在已准备好用于生产环境！")

if __name__ == "__main__":
    asyncio.run(demonstrate_complete_implementation())