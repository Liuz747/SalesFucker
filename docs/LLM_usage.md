# 多 LLM 运行时使用指南

MAS 当前采用的多 LLM 运行时，位于 `api/infra/runtimes/`。该实现专注于快速启动与测试：读取 `api/data/models.yaml` 配置，依据 `.env` 中的 API Key 启用供应商，并通过统一的 `LLMClient` 暴露 Completions 与 Responses 能力。

---

## 1. 目录结构
```text
api/infra/runtimes/
├── client.py          # LLMClient 实现（OpenAI/Anthropic/OpenRouter）
├── config.py          # 读取 YAML 模型清单
├── entities.py        # 请求 / 响应 / 枚举类型
├── routing.py         # 简单路由器（保留扩展位）
└── providers/         # 具体供应商实现（OpenAIProvider、AnthropicProvider）
```

`api/data/models.yaml` 用于声明可用模型，只要 `.env` 中存在对应 API Key，模型就会被 `LLMConfig` 加载。

---

## 2. 环境配置
在 `api/.env` 中设定所需的密钥：
```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
OPENROUTER_API_KEY=sk-or-...
```
> 未配置密钥的供应商会被自动跳过。

如需调整模型列表，编辑 `api/data/models.yaml`，示例结构：
```yaml
- id: "openai"
  type: "openai"
  base_url: "https://api.openai.com/v1"
  enabled: true
  models:
    - id: "gpt-4o-mini"
      name: "GPT-4 Omni Mini"
      type: "text"
      enabled: true
```

---

## 3. 快速调用示例
```python
import asyncio
from uuid import uuid4

from infra.runtimes import LLMClient, CompletionsRequest
from libs.types import Message

async def main():
    client = LLMClient()

    request = CompletionsRequest(
        id=uuid4(),
        provider="openai",      # 对应 models.yaml 中的 provider id
        model="gpt-4o-mini",    # 对应模型 id
        messages=[
            Message(role="system", content="你是专业美妆顾问"),
            Message(role="user", content="推荐一款适合干皮的面霜")
        ],
        temperature=0.7,
        max_tokens=512,
    )

    response = await client.completions(request)
    print(response.content)

asyncio.run(main())
```

### Responses API / 结构化输出
```python
from infra.runtimes import LLMClient, ResponseMessageRequest
from pydantic import BaseModel

class CalendarEvent(BaseModel):
    name: str
    date: str

client = LLMClient()
request = ResponseMessageRequest(
    id=uuid4(),
    provider="openai",
    model="gpt-4o",
    input="安排一次面部护理预约在下周三下午三点",
    system_prompt="请提取预约信息并返回 JSON",
    output_model=CalendarEvent,
)
response = await client.responses(request)
print(response.content)  # 已解析为 CalendarEvent 实例
```

---

## 4. 扩展要点
- **新增供应商**：实现 `providers/BaseProvider` 子类，并在 `config.py` 中加入映射
- **模型筛选**：`data/models.yaml` 中将 `enabled` 设为 `false` 即可临时禁用
- **成本/统计**：当前版本未集成成本追踪，可在 `LLMResponse` 中的 `usage` 字段上层处理
- **路由策略**：`routing.SimpleRouter` 预留了根据 agent 或租户自定义策略的接口

---

## 5. 常见问题
| 现象 | 可能原因 | 排查方式 |
| --- | --- | --- |
| `ValueError: 指定的供应商不可用` | `.env` 未配置对应 API Key 或 provider id 拼写错误 | 确认 `models.yaml` 与请求 `provider` 字段一致，并设置 API Key |
| `HTTP 401` | API Key 失效或未授权对应模型 | 在供应商平台确认 key 权限，或更换模型 ID |
| `No API key found for provider` 日志垃圾 | `config.py` 会对缺失密钥的 provider 打印提示 | 视为提示即可，若想静默可在加载逻辑中移除 print |

该指南覆盖了当前仓库中的轻量多 LLM 模式，若未来切换回完整的成本路由框架，可在 `docs` 中追加迁移说明。
