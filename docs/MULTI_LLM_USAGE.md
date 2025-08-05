# 多LLM供应商系统使用指南

## 概述

MAS Cosmetic Agent System 现已支持多LLM供应商，包括 OpenAI、Anthropic、Google Gemini 和 DeepSeek。系统提供智能路由、自动故障转移、成本优化和性能监控等功能。

## 核心特性

### 🎯 智能路由
- **动态供应商选择**: 根据智能体类型、查询复杂度、历史性能自动选择最优供应商
- **成本优化路由**: 在保证质量的前提下选择成本最低的供应商
- **中文内容优化**: 针对中文查询优选支持中文的模型

### 🔄 自动故障转移
- **无缝切换**: 供应商失败时自动切换到备用供应商
- **上下文保持**: 故障转移过程中保持对话上下文完整性
- **断路器模式**: 自动隔离故障供应商，防止级联失败

### 💰 成本追踪与优化
- **实时成本监控**: 按供应商、智能体、租户维度追踪成本
- **预算管理**: 支持日预算、月预算和成本告警
- **优化建议**: 自动分析使用模式，提供成本优化建议

### 📊 性能监控
- **全链路监控**: 从请求到响应的完整性能追踪
- **健康检查**: 实时监控供应商健康状态
- **使用分析**: 详细的使用统计和趋势分析

## 快速开始

### 1. 环境配置

```bash
# 设置API密钥
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GEMINI_API_KEY="..."
export DEEPSEEK_API_KEY="..."
export LLM_CONFIG_ENCRYPTION_KEY="your-encryption-key"
```

### 2. 基础使用

```python
import asyncio
from src.llm import get_multi_llm_client, RoutingStrategy

async def basic_usage():
    # 获取多LLM客户端
    client = await get_multi_llm_client()
    
    # 发送聊天请求
    response = await client.chat_completion(
        messages=[{
            "role": "user",
            "content": "推荐一些适合敏感肌的护肤品"
        }],
        agent_type="product",
        tenant_id="my_tenant",
        strategy=RoutingStrategy.BALANCED
    )
    
    print(response)

# 运行示例
asyncio.run(basic_usage())
```

### 3. 增强版智能体

使用 `MultiLLMBaseAgent` 替换原有的 `BaseAgent`：

```python
from src.llm import MultiLLMBaseAgent, RoutingStrategy

class ProductAgent(MultiLLMBaseAgent):
    def __init__(self, agent_id: str, tenant_id: str):
        super().__init__(agent_id, tenant_id)
        # 设置产品智能体的路由策略
        self.set_routing_strategy(RoutingStrategy.AGENT_OPTIMIZED)
    
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        # 使用多LLM功能
        response = await self.llm_chat_completion(
            messages=[{
                "role": "user",
                "content": message.payload["content"]
            }],
            temperature=0.7
        )
        
        return self.send_message(
            recipient=message.sender,
            message_type="response",
            payload={"response": response}
        )
```

### 4. 现有智能体升级

为现有智能体添加多LLM支持：

```python
from src.llm import MultiLLMAgentMixin

class ExistingSalesAgent(MultiLLMAgentMixin, BaseAgent):
    def __init__(self, agent_id: str, tenant_id: str):
        super().__init__(agent_id, tenant_id)
    
    async def generate_sales_response(self, query: str) -> str:
        # 使用混入提供的LLM功能
        return await self.llm_completion(
            messages=[{
                "role": "system", 
                "content": "你是专业的美妆销售顾问"
            }, {
                "role": "user",
                "content": query
            }]
        )
```

## 配置管理

### 全局配置

```python
from src.llm import ConfigManager, ProviderType

async def setup_config():
    config_manager = ConfigManager()
    
    # 创建OpenAI供应商配置
    openai_config = await config_manager.create_provider_config(
        provider_type=ProviderType.OPENAI,
        api_key=os.getenv("OPENAI_API_KEY"),
        priority=1,
        rate_limit_rpm=3500
    )
    
    # 保存配置
    global_config = GlobalProviderConfig(
        default_providers={
            ProviderType.OPENAI.value: openai_config
        }
    )
    
    await config_manager.save_global_config(global_config)
```

### 租户配置

```python
from src.llm import TenantProviderConfig, AgentProviderMapping, CostConfig

# 创建租户特定配置
tenant_config = TenantProviderConfig(
    tenant_id="beauty_brand_a",
    agent_mappings={
        "sales": AgentProviderMapping(
            agent_type="sales",
            primary_provider=ProviderType.ANTHROPIC,
            fallback_providers=[ProviderType.OPENAI],
            quality_threshold=0.85
        )
    },
    cost_config=CostConfig(
        daily_budget=100.0,
        monthly_budget=2000.0
    )
)
```

## 智能体类型优化配置

系统为不同智能体类型提供了优化配置：

| 智能体类型 | 推荐供应商 | 特点 |
|------------|------------|------|
| compliance | Anthropic | Claude擅长合规分析和内容审核 |
| sentiment | Gemini | 对中文情感分析效果好 |
| intent | OpenAI | GPT在意图识别方面准确性高 |
| sales | Anthropic | Claude更适合销售对话和推理 |
| product | OpenAI | GPT在产品推荐方面表现优异 |
| memory | DeepSeek | 成本低廉，适合记忆存储任务 |
| suggestion | Anthropic | Claude擅长分析和建议生成 |

## 路由策略

### PERFORMANCE_FIRST
优先选择响应时间最快、成功率最高的供应商
```python
strategy = RoutingStrategy.PERFORMANCE_FIRST
```

### COST_FIRST  
优先选择成本最低的供应商
```python
strategy = RoutingStrategy.COST_FIRST
```

### BALANCED
平衡性能和成本
```python
strategy = RoutingStrategy.BALANCED
```

### AGENT_OPTIMIZED
根据智能体类型选择最适合的供应商
```python
strategy = RoutingStrategy.AGENT_OPTIMIZED
```

### CHINESE_OPTIMIZED
优化中文内容处理
```python
strategy = RoutingStrategy.CHINESE_OPTIMIZED
```

## 监控和分析

### 获取系统状态

```python
# 供应商状态
provider_status = await client.get_provider_status(tenant_id="my_tenant")

# 成本分析
cost_analysis = await client.get_cost_analysis(tenant_id="my_tenant")

# 路由统计
routing_stats = await client.get_routing_stats()

# 故障转移统计
failover_stats = await client.get_failover_stats()
```

### 优化建议

```python
# 获取成本优化建议
suggestions = await client.get_optimization_suggestions(
    tenant_id="my_tenant",
    min_savings=0.1  # 最小节省10%
)

for suggestion in suggestions:
    print(f"优化类型: {suggestion['optimization_type']}")
    print(f"潜在节省: ${suggestion['potential_savings']:.4f}")
    print(f"建议: {suggestion['description']}")
```

## 故障处理

### 断路器管理

```python
from src.llm import FailoverSystem

# 手动重置断路器
await failover_system.reset_circuit_breaker(
    provider_type=ProviderType.OPENAI,
    tenant_id="my_tenant"
)
```

### 健康检查

```python
# 系统健康检查
health_status = await client.health_check()

if health_status["status"] != "healthy":
    print(f"系统状态异常: {health_status['error']}")
```

## 最佳实践

### 1. 智能体设计

- 为不同智能体类型选择合适的路由策略
- 设置合理的质量阈值和成本优先级
- 利用智能体特定的LLM偏好设置

### 2. 成本控制

- 设置合理的日预算和月预算
- 启用成本优化功能
- 定期检查优化建议

### 3. 性能优化

- 监控供应商健康状态
- 根据性能数据调整路由配置
- 利用缓存策略减少重复请求

### 4. 故障预防

- 配置多个备用供应商
- 设置合理的重试和超时参数
- 定期检查断路器状态

## 迁移指南

### 从单供应商迁移

1. 保持现有代码兼容性：
```python
# 现有代码继续有效
from src.llm import get_llm_client
client = get_llm_client()  # 返回原有OpenAI客户端
```

2. 逐步迁移到多供应商：
```python
# 新代码使用多供应商
from src.llm import get_multi_llm_client
client = await get_multi_llm_client()
```

3. 升级智能体基类：
```python
# 从 BaseAgent 升级到 MultiLLMBaseAgent
from src.llm import MultiLLMBaseAgent
```

## 常见问题

### Q: 如何确保API密钥安全？
A: 系统使用加密存储API密钥，支持环境变量和加密配置文件。

### Q: 如何处理供应商配额用完的情况？
A: 系统会自动检测配额限制并切换到备用供应商。

### Q: 如何优化成本？
A: 启用成本优化功能，系统会自动选择成本效益最高的供应商。

### Q: 如何确保中文内容质量？
A: 使用 CHINESE_OPTIMIZED 路由策略，系统会优选支持中文的模型。

## 技术支持

如有问题，请查看：
- 系统日志: 包含详细的错误信息和性能数据
- 健康检查接口: 实时系统状态
- 统计信息接口: 使用情况和性能指标

更多详细信息请参考源码注释和单元测试。