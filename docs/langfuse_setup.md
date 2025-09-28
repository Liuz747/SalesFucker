# Langfuse 集成设置指南

本指南说明如何设置您的 MAS-v0.2 多智能体系统与 Langfuse 的集成，以实现工作流可视化和追踪。

## 前置条件

1. **已完成的集成**: Langfuse SDK 已集成到您的 API 代码中
2. **Langfuse 实例**: 您在 `web/` 文件夹中有 Langfuse v3.103.0 实例
3. **环境配置**: Python 环境已配置

## 设置步骤

### 1. 启动 Langfuse Web 服务

```bash
cd web/
pnpm i
pnpm run dx  # 完整设置：安装依赖、重置数据库、种子数据、启动开发服务器
```

或者，如果已经设置过：

```bash
cd web/
pnpm run dev:frontend  # 仅启动 Web 应用 (localhost:3000)
```

### 2. 设置 Langfuse 项目

1. 打开浏览器访问 `http://localhost:3000`
2. 使用开发凭据登录：
   - Username: `demo@langfuse.com`
   - Password: `password`
3. 创建新项目或使用现有项目
4. 进入项目设置，创建新的 API 凭据
5. 复制生成的公钥和私钥

### 3. 配置 API 环境

1. 在 `api/` 目录中复制环境文件：
   ```bash
   cd api/
   cp .env.example .env
   ```

2. 在 `.env` 文件中添加 Langfuse 配置：
   ```env
   # === Langfuse Configuration ===
   LANGFUSE_SECRET_KEY=sk-lf-your-secret-key-here
   LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key-here
   LANGFUSE_HOST=http://localhost:3000
   ```

   将 `your-secret-key-here` 和 `your-public-key-here` 替换为步骤2中获取的实际密钥。

### 4. 启动 API 服务

```bash
cd api/
uv run main.py
```

或者如果使用 Python 直接运行：

```bash
cd api/
python main.py
```

API 将在 `http://localhost:8000` 启动。

## 测试集成

### 1. 验证 Langfuse 连接

发送测试请求到 API：

```bash
curl -X POST "http://localhost:8000/v1/chat/message" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "input": {
      "content": "你好，我想了解护肤产品"
    },
    "assistant_id": "assistant-1"
  }'
```

### 2. 在 Langfuse 中查看追踪

1. 返回 Langfuse Web 界面 (`http://localhost:3000`)
2. 导航到您的项目
3. 查看 "Traces" 页面
4. 您应该能看到名为 "多智能体对话处理" 的追踪记录

### 3. 预期的追踪结构

追踪层次结构应如下所示：

```
📊 多智能体对话处理 (Trace)
├── 🔄 工作流执行 (Span)
│   ├── 🛡️ compliance_review_execution (Span)
│   ├── 😊 sentiment_analysis_execution (Span)  
│   ├── 🎯 intent_analysis_execution (Span)
│   ├── 💼 sales_agent_execution (Span)
│   ├── 📦 product_expert_execution (Span)
│   └── 🧠 memory_agent_execution (Span)
```

每个智能体执行都包含：
- 输入数据（客户消息、智能体类型）
- 输出数据（响应内容、处理时间）
- 元数据（租户ID、智能体ID）
- 执行状态（成功/失败）

## 配置选项

您可以在 `.env` 文件中调整以下 Langfuse 配置：

```env
# 启用/禁用追踪
LANGFUSE_ENABLED=true

# 调试模式
LANGFUSE_DEBUG=false

# 批量发送大小
LANGFUSE_FLUSH_AT=15

# 发送间隔（秒）
LANGFUSE_FLUSH_INTERVAL=0.5
```

## 故障排除

### 常见问题

1. **连接错误**: 确保 Langfuse web 服务正在运行并可在 `http://localhost:3000` 访问

2. **认证失败**: 验证 `.env` 文件中的公钥和私钥是否正确

3. **没有追踪数据**: 检查：
   - `LANGFUSE_ENABLED=true` 已设置
   - 密钥配置正确
   - API 请求包含有效的 JWT token

4. **智能体执行错误**: 确保所有智能体已正确初始化和注册

### 调试技巧

1. **启用调试日志**:
   ```env
   LANGFUSE_DEBUG=true
   DEBUG=true
   LOG_LEVEL=DEBUG
   ```

2. **检查 API 日志**: 在启动 API 服务时查看控制台输出，寻找 Langfuse 相关消息

3. **验证追踪数据**: 在 Langfuse Web 界面中检查原始追踪数据

## 高级功能

### 自定义元数据

追踪会自动包含：
- 租户ID
- 智能体类型和ID
- 处理时间统计
- 错误信息（如果有）
- 用户会话信息

### 性能监控

Langfuse 界面提供：
- 执行时间分析
- 错误率统计
- 智能体性能对比
- 用户会话分析

### 数据导出

您可以通过 Langfuse API 导出追踪数据进行进一步分析：
- 使用 REST API 导出 JSON 格式
- 集成业务分析工具
- 创建自定义仪表板

## 注意事项

1. **数据隐私**: 确保敏感的客户数据不被包含在追踪记录中
2. **性能影响**: 追踪会增加轻微的处理延迟，在生产环境中考虑批量设置
3. **存储空间**: 定期清理旧的追踪数据以管理存储空间
4. **网络访问**: 确保 API 服务器可以访问 Langfuse 服务器

## 生产部署

对于生产环境：

1. **使用外部 Langfuse 实例**: 考虑使用 Langfuse Cloud 或自建生产实例
2. **配置 HTTPS**: 确保所有连接使用 HTTPS
3. **设置监控**: 监控追踪数据发送状态
4. **备份配置**: 备份 Langfuse 配置和数据

---

集成完成后，您就可以在 Langfuse 界面中实时可视化您的多智能体工作流执行情况了！