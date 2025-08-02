"""
多LLM供应商系统配置示例

该模块提供多LLM供应商系统的配置示例和初始化脚本。
演示如何配置和使用新的多供应商LLM系统。

使用方法:
1. 设置环境变量中的API密钥
2. 运行此脚本初始化系统
3. 在BaseAgent中使用MultiLLMBaseAgent或MultiLLMAgentMixin
"""

import os
import asyncio
from typing import Dict, Any

from .config_manager import ConfigManager
from .multi_llm_client import get_multi_llm_client
from .provider_config import (
    ProviderType,
    ProviderCredentials,
    ProviderConfig,
    GlobalProviderConfig,
    TenantProviderConfig,
    AgentProviderMapping,
    CostConfig,
    ModelCapability
)
from .intelligent_router import RoutingStrategy


async def create_example_config() -> GlobalProviderConfig:
    """
    创建示例配置
    
    返回:
        GlobalProviderConfig: 示例全局配置
    """
    config_manager = ConfigManager()
    
    # 创建默认供应商配置
    default_providers = {}
    
    # OpenAI配置
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        openai_config = await config_manager.create_provider_config(
            provider_type=ProviderType.OPENAI,
            api_key=openai_api_key,
            priority=1,
            rate_limit_rpm=3500,
            rate_limit_tpm=90000
        )
        default_providers[ProviderType.OPENAI.value] = openai_config
    
    # Anthropic配置
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_api_key:
        anthropic_config = await config_manager.create_provider_config(
            provider_type=ProviderType.ANTHROPIC,
            api_key=anthropic_api_key,
            priority=2,
            rate_limit_rpm=4000,
            rate_limit_tpm=400000
        )
        default_providers[ProviderType.ANTHROPIC.value] = anthropic_config
    
    # Gemini配置
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if gemini_api_key:
        gemini_config = await config_manager.create_provider_config(
            provider_type=ProviderType.GEMINI,
            api_key=gemini_api_key,
            priority=3,
            rate_limit_rpm=1500,
            rate_limit_tpm=32000
        )
        default_providers[ProviderType.GEMINI.value] = gemini_config
    
    # DeepSeek配置
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    if deepseek_api_key:
        deepseek_config = await config_manager.create_provider_config(
            provider_type=ProviderType.DEEPSEEK,
            api_key=deepseek_api_key,
            api_base="https://api.deepseek.com",
            priority=4,
            rate_limit_rpm=10000,
            rate_limit_tpm=1000000
        )
        default_providers[ProviderType.DEEPSEEK.value] = deepseek_config
    
    # 创建全局配置
    global_config = GlobalProviderConfig(
        default_providers=default_providers,
        tenant_configs={},
        global_settings={
            "default_routing_strategy": RoutingStrategy.BALANCED.value,
            "enable_cost_optimization": True,
            "enable_failover": True,
            "enable_analytics": True
        }
    )
    
    return global_config


async def create_example_tenant_config(tenant_id: str) -> TenantProviderConfig:
    """
    创建示例租户配置
    
    参数:
        tenant_id: 租户ID
        
    返回:
        TenantProviderConfig: 租户配置
    """
    # 智能体映射配置
    agent_mappings = {
        "compliance": AgentProviderMapping(
            agent_type="compliance",
            primary_provider=ProviderType.ANTHROPIC,  # Claude擅长合规分析
            fallback_providers=[ProviderType.OPENAI, ProviderType.GEMINI],
            quality_threshold=0.9
        ),
        "sentiment": AgentProviderMapping(
            agent_type="sentiment",
            primary_provider=ProviderType.GEMINI,  # Gemini中文情感分析较好
            fallback_providers=[ProviderType.DEEPSEEK, ProviderType.OPENAI],
            quality_threshold=0.85
        ),
        "intent": AgentProviderMapping(
            agent_type="intent",
            primary_provider=ProviderType.OPENAI,  # GPT意图识别准确
            fallback_providers=[ProviderType.ANTHROPIC, ProviderType.GEMINI],
            quality_threshold=0.8
        ),
        "sales": AgentProviderMapping(
            agent_type="sales",
            primary_provider=ProviderType.ANTHROPIC,  # Claude更适合销售对话
            fallback_providers=[ProviderType.OPENAI, ProviderType.GEMINI],
            quality_threshold=0.85
        ),
        "product": AgentProviderMapping(
            agent_type="product",
            primary_provider=ProviderType.OPENAI,  # GPT产品推荐效果好
            fallback_providers=[ProviderType.ANTHROPIC, ProviderType.GEMINI],
            quality_threshold=0.9
        ),
        "memory": AgentProviderMapping(
            agent_type="memory",
            primary_provider=ProviderType.DEEPSEEK,  # DeepSeek成本低适合记忆任务
            fallback_providers=[ProviderType.GEMINI, ProviderType.OPENAI],
            quality_threshold=0.7
        ),
        "suggestion": AgentProviderMapping(
            agent_type="suggestion",
            primary_provider=ProviderType.ANTHROPIC,  # Claude擅长分析建议
            fallback_providers=[ProviderType.OPENAI, ProviderType.GEMINI],
            quality_threshold=0.85
        )
    }
    
    # 成本配置
    cost_config = CostConfig(
        daily_budget=50.0,  # 日预算50美元
        monthly_budget=1000.0,  # 月预算1000美元
        cost_threshold_warning=0.8,
        cost_threshold_critical=0.95,
        enable_cost_optimization=True
    )
    
    # 创建租户配置
    tenant_config = TenantProviderConfig(
        tenant_id=tenant_id,
        provider_configs={},  # 使用默认供应商配置
        agent_mappings=agent_mappings,
        routing_rules=[],  # 可以添加自定义路由规则
        cost_config=cost_config
    )
    
    return tenant_config


async def initialize_multi_llm_system(
    config: GlobalProviderConfig,
    tenant_configs: Dict[str, TenantProviderConfig] = None
) -> None:
    """
    初始化多LLM供应商系统
    
    参数:
        config: 全局配置
        tenant_configs: 租户配置字典
    """
    # 添加租户配置
    if tenant_configs:
        for tenant_id, tenant_config in tenant_configs.items():
            config.tenant_configs[tenant_id] = tenant_config
    
    # 获取并初始化多LLM客户端
    client = await get_multi_llm_client(config)
    
    # 验证系统健康状态
    health_status = await client.health_check()
    
    if health_status["status"] == "healthy":
        print(f"✅ 多LLM供应商系统初始化成功")
        print(f"📊 可用供应商数量: {health_status['available_providers']}")
        print(f"📋 总供应商数量: {health_status['total_providers']}")
    else:
        print(f"❌ 多LLM供应商系统初始化失败: {health_status.get('error', '未知错误')}")
        raise Exception(f"系统初始化失败: {health_status}")


async def demo_multi_llm_usage():
    """演示多LLM系统的使用"""
    print("🚀 开始多LLM供应商系统演示")
    
    # 创建配置
    print("📝 创建配置...")
    global_config = await create_example_config()
    
    # 创建示例租户配置
    tenant_config = await create_example_tenant_config("demo_tenant")
    
    # 初始化系统
    print("🔧 初始化系统...")
    await initialize_multi_llm_system(
        global_config, 
        {"demo_tenant": tenant_config}
    )
    
    # 获取客户端
    client = await get_multi_llm_client()
    
    # 演示不同智能体类型的请求
    test_cases = [
        {
            "agent_type": "sentiment",
            "message": "这个产品真的很棒，我非常满意！",
            "description": "情感分析测试"
        },
        {
            "agent_type": "intent", 
            "message": "我想了解一下你们的护肤产品",
            "description": "意图分类测试"
        },
        {
            "agent_type": "sales",
            "message": "能推荐一些适合干性皮肤的产品吗？",
            "description": "销售对话测试"
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🧪 {test_case['description']}")
        try:
            response = await client.chat_completion(
                messages=[{
                    "role": "user", 
                    "content": test_case["message"]
                }],
                agent_type=test_case["agent_type"],
                tenant_id="demo_tenant",
                strategy=RoutingStrategy.AGENT_OPTIMIZED
            )
            print(f"✅ 响应: {response[:100]}...")
        except Exception as e:
            print(f"❌ 错误: {str(e)}")
    
    # 显示统计信息
    print("\n📊 系统统计信息:")
    stats = await client.get_global_stats()
    print(f"总请求数: {stats['client_stats']['total_requests']}")
    print(f"成功请求数: {stats['client_stats']['successful_requests']}")
    
    # 显示成本分析
    print("\n💰 成本分析:")
    cost_analysis = await client.get_cost_analysis(tenant_id="demo_tenant")
    print(f"总成本: ${cost_analysis['total_cost']:.6f}")
    print(f"平均每请求成本: ${cost_analysis['avg_cost_per_request']:.6f}")
    
    print("\n✨ 演示完成！")


async def save_example_config():
    """保存示例配置到文件"""
    config_manager = ConfigManager()
    
    # 创建并保存全局配置
    global_config = await create_example_config()
    await config_manager.save_global_config(global_config)
    
    # 创建并保存租户配置
    tenant_config = await create_example_tenant_config("example_tenant")
    await config_manager.save_tenant_config(tenant_config)
    
    print("📁 示例配置已保存到 config/ 目录")


if __name__ == "__main__":
    # 运行演示
    asyncio.run(demo_multi_llm_usage())
    
    # 或者仅保存配置文件
    # asyncio.run(save_example_config())