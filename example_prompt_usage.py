#!/usr/bin/env python3
"""
销售智能体提示词使用示例

展示如何在具体智能体中实现和使用提示词方法。
这是推荐的最佳实践模式。
"""

import asyncio
import sys
import os
from typing import Dict, Any

# 确保可以导入项目模块
sys.path.insert(0, os.path.dirname(__file__))

from src.agents.sales.agent import SalesAgent

async def demo_sales_agent_prompts():
    """演示销售智能体提示词的实际使用"""
    
    print("🛍️  销售智能体提示词使用示例")
    print("=" * 50)
    
    # 1. 创建销售智能体实例
    sales_agent = SalesAgent(tenant_id="demo_cosmetics_brand")
    
    # 预加载提示词以提高性能
    await sales_agent.preload_prompts()
    
    print(f"✅ 创建销售智能体: {sales_agent.agent_id}")
    print(f"   租户: {sales_agent.tenant_id}")
    print(f"   智能体类型: {sales_agent.agent_type}")
    
    # 2. 个性化问候消息示例
    print("\n📝 1. 个性化问候消息")
    print("-" * 30)
    
    # 场景1: 新客户，早上访问
    greeting_context_1 = {
        'agent_name': '小美',
        'customer_name': '张女士',
        'time_of_day': '早上',
        'previous_visit': False,
        'store_location': '北京王府井店'
    }
    
    greeting_1 = await sales_agent.get_greeting_message(greeting_context_1)
    print(f"新客户早晨问候: {greeting_1}")
    
    # 场景2: 老客户，下午访问
    greeting_context_2 = {
        'agent_name': '小雅',
        'customer_name': '李小姐',
        'time_of_day': '下午',
        'previous_visit': True,
        'last_purchase': '兰蔻小黑瓶',
        'store_location': '上海南京路店'
    }
    
    greeting_2 = await sales_agent.get_greeting_message(greeting_context_2)
    print(f"老客户下午问候: {greeting_2}")
    
    # 3. 产品推荐提示词示例
    print("\n🎯 2. 产品推荐提示词")
    print("-" * 30)
    
    # 场景1: 年轻客户，控油需求
    recommendation_context_1 = {
        'skin_type': '油性肌肤',
        'skin_concerns': '毛孔粗大、黑头',
        'budget_range': '200-400元',
        'lifestyle': '学生',
        'preferred_brands': '资生堂、兰蔻',
        'customer_age': '22岁'
    }
    
    recommendation_1 = await sales_agent.get_product_recommendation_prompt(recommendation_context_1)
    print(f"年轻客户控油推荐:\\n{recommendation_1}")
    
    # 场景2: 成熟客户，抗老需求  
    recommendation_context_2 = {
        'skin_type': '干性肌肤',
        'skin_concerns': '细纹、松弛、暗沉',
        'budget_range': '800-1500元',
        'lifestyle': '职场精英',
        'preferred_brands': 'SK-II、雅诗兰黛',
        'customer_age': '35岁'
    }
    
    recommendation_2 = await sales_agent.get_product_recommendation_prompt(recommendation_context_2)
    print(f"\\n成熟客户抗老推荐:\\n{recommendation_2}")
    
    # 4. 异议处理提示词示例
    print("\\n💬 3. 异议处理提示词")
    print("-" * 30)
    
    # 场景1: 价格异议
    price_objection_context = {
        'customer_budget': '300元以下',
        'product_price': '599元',
        'customer_concern': '这个产品太贵了',
        'product_name': 'SK-II神仙水'
    }
    
    price_response = await sales_agent.get_objection_handling_prompt('price', price_objection_context)
    print(f"价格异议处理:\\n{price_response}")
    
    # 场景2: 质量疑虑
    quality_objection_context = {
        'customer_concern': '这个品牌我没听过，质量靠谱吗？',
        'product_brand': '某新兴品牌',
        'product_certifications': ['FDA认证', 'GMP认证']
    }
    
    quality_response = await sales_agent.get_objection_handling_prompt('quality', quality_objection_context)
    print(f"\\n质量异议处理:\\n{quality_response}")
    
    # 5. 在实际业务流程中使用
    print("\\n🔄 4. 业务流程集成示例")
    print("-" * 30)
    
    # 模拟完整的销售对话流程
    print("模拟客户进店流程:")
    
    # 步骤1: 问候
    customer_context = {
        'agent_name': '小丽',
        'customer_name': '王小姐',
        'time_of_day': '下午',
        'previous_visit': False
    }
    
    greeting = await sales_agent.get_greeting_message(customer_context)
    print(f"  销售顾问: {greeting}")
    
    # 步骤2: 了解需求后，产品推荐
    customer_needs = {
        'skin_type': '混合性肌肤',
        'skin_concerns': 'T区油腻，两颊干燥',
        'budget_range': '500-800元',
        'lifestyle': '上班族，化妆频繁'
    }
    
    recommendation = await sales_agent.get_product_recommendation_prompt(customer_needs)
    print(f"  产品推荐: {recommendation[:100]}...")
    
    # 步骤3: 处理客户异议
    objection_context = {
        'customer_concern': '我担心用了会过敏',
        'product_type': '精华液',
        'skin_sensitivity': '轻度敏感'
    }
    
    objection_response = await sales_agent.get_objection_handling_prompt('quality', objection_context)
    print(f"  异议处理: {objection_response[:100]}...")
    
    print("\\n" + "=" * 50)
    print("🎉 销售智能体提示词集成演示完成！")
    print("\\n💡 关键要点:")
    print("  1. 每个智能体实现自己特定的提示词方法")
    print("  2. BaseAgent只提供通用的preload_prompts()方法") 
    print("  3. 通过LLMMixin继承动态提示词构建能力")
    print("  4. 具体方法根据智能体业务需求定制")
    print("  5. 完整的降级处理和错误恢复机制")

async def demo_product_agent_prompts():
    """演示如何为产品专家智能体实现提示词方法"""
    
    print("\\n🔬 产品专家智能体提示词实现示例")
    print("=" * 50)
    
    print("# 产品专家智能体的提示词方法示例代码:")
    print('''
class ProductExpertAgent(BaseAgent):
    
    async def get_ingredient_analysis_prompt(self, context: Dict[str, Any]) -> Optional[str]:
        """获取成分分析提示词"""
        try:
            if hasattr(self, '_prompt_manager') and self._prompt_manager:
                return await self._prompt_manager.get_custom_prompt(
                    prompt_type='ingredient_analysis',
                    agent_id=self.agent_id,
                    agent_type=self.agent_type,
                    tenant_id=self.tenant_id or "default",
                    context=context
                )
            else:
                # 降级处理
                product_name = context.get('product_name', '该产品')
                return f"让我为您详细分析{product_name}的核心成分和功效..."
        except Exception as e:
            self.logger.warning(f"获取成分分析提示词失败: {e}")
            return "我来为您分析产品的主要成分和适用肌肤类型..."
    
    async def get_usage_instruction_prompt(self, context: Dict[str, Any]) -> Optional[str]:
        """获取使用指导提示词"""
        # 类似的实现模式...
        pass
    ''')

if __name__ == "__main__":
    asyncio.run(demo_sales_agent_prompts())
    asyncio.run(demo_product_agent_prompts())