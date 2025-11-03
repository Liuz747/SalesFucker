# Message & Memory Storage Strategy

The current MAS implementation stores conversation data through a layered memory stack that matches the code in `api/core/memory/` and `api/core/agents/memory/`. This document summarises how each component works and how to enable optional backends.

---

## 1. Components at a Glance

| Layer | Module | Purpose |
| --- | --- | --- |
| Short-term memory | `core/memory/conversation_store.py` | Keeps the last N messages per thread in Redis for LangGraph context windows |
| Long-term index (optional) | `core/memory/index_manager.py` | Manages the `memory_v1` index in Elasticsearch for search & analytics |
| Vector store (optional) | `core/memory/vector_store.py` | Stores semantic embeddings in Milvus for similarity recall |
| Multimodal cache | `core/agents/memory/multimodal_memory.py` | In-process cache for voice/image artefacts and user profiles |
| Infrastructure bootstrap | `libs/factory.py` (`infra_registry`) | Creates and shares DB / Redis / Elasticsearch / Milvus clients |

---

## 2. Short-Term Conversation Store (Redis)

`ConversationStore` is used by LangGraph agents to persist recent exchanges:
```python
from uuid import uuid4
from infra.runtimes import CompletionsRequest
from core.memory import ConversationStore

store = ConversationStore()
thread_id = uuid4()
request = await store.prepare_request(
    run_id=uuid4(),
    provider="openai",
    model="gpt-4o-mini",
    messages=[...],
    thread_id=thread_id,
)
response = await agent.invoke_llm(request)
await store.save_assistant_reply(thread_id, response.content)
```
Key behaviour:
- Messages are serialised with `msgpack` and pushed into Redis lists (`conversation:<thread_id>`)
- List length is trimmed to `max_messages` (default 20)
- Keys expire after 1 hour unless refreshed
- Works even when Redis credentials are injected at runtime (`REDIS_URL` or host/port/password trio)

---

## 3. Optional Long-Term Memory

### 3.1 Elasticsearch Index Manager
`IndexManager` creates and maintains the `memory_v1` index when Elasticsearch is available. It requires:
```env
ELASTICSEARCH_URL=http://localhost:9200
ELASTIC_PASSWORD=changeme  # optional if auth enabled
ES_MEMORY_INDEX=memory_v1
ES_VECTOR_DIMENSION=1024
```
Usage pattern:
```python
from core.memory import IndexManager

manager = IndexManager()
await infra_registry.create_clients()        # ensures ES client exists
await manager.create_memory_index()
await manager.client.index(
    index=manager.index_name,
    id="memory-1",
    document={
        "tenant_id": "tenant-1",
        "content": "用户下单了修复面霜",
        "created_at": to_isoformat(),
        "embedding": embedding_vector,
    },
)
```
The index schema supports multi-tenant filtering, dense vectors (`dense_vector`), and TTL-style timestamps (`expires_at`).

### 3.2 Milvus Vector Store
`VectorStore` relies on Milvus via the same `infra_registry` bootstrap:
```env
MILVUS_HOST=localhost
MILVUS_PORT=19530
```
Example:
```python
from core.memory import VectorStore

store = VectorStore(embedding_dim=3072)
await infra_registry.create_clients()
await store.insert_memories(
    tenant_id="tenant-1",
    memories=[{"id": "m1", "content": "客户喜欢轻薄底妆"}],
    embeddings=[embedding_vector],
)
results = await store.search_similar_memories("tenant-1", embedding_vector, top_k=5)
```
Each tenant gets a dedicated collection (`memories_<tenant_id>`). If Milvus is not available, the factory logs a warning and downstream calls should catch the resulting exceptions.

---

## 4. Multimodal Memory Manager

`MultimodalMemoryManager` retains additional artefacts (transcriptions, image analysis, voice patterns) in an in-process dictionary. It is primarily used by the memory agent to build lightweight user profiles.

Important notes:
- Data is scoped to the manager instance; for persistence, plug in Elasticsearch/Milvus layers or write to your own storage inside the async tasks
- `_update_user_profile` runs asynchronously via `asyncio.create_task` to avoid blocking the main workflow
- The manager exposes helper methods to retrieve recent conversations and summarise image results

---

## 5. End-to-End Flow
1. `ThreadService` orchestrates a LangGraph workflow via `orchestrator.process_conversation`
2. Agents call `ConversationStore.prepare_request` → Redis stores the sliding window
3. After generating a reply, agents call `save_assistant_reply` to keep context fresh
4. Depending on feature toggles, services may push data to Elasticsearch (structured memories) and Milvus (embeddings)
5. Multimodal artefacts are cached in memory for quick profile enrichment

This design keeps the minimal Redis-backed loop always available, while optional services can be enabled by providing credentials in `.env` and starting the corresponding containers from `docker/docker-compose.dev.yml`.

---

## 6. Monitoring & Troubleshooting

| 现象 | 说明 | 排查建议 |
| --- | --- | --- |
| Redis 列表长度未增长 | 消息中只有 system role 或 Redis 未连接 | 检查 Redis 日志，确认 `REDIS_URL` 正确，或在调试时添加 user/assistant 消息 |
| `RuntimeError: Elasticsearch客户端未初始化` | 未调用 `infra_registry.create_clients()` 或未提供 ES 配置 | 在应用启动（FastAPI lifespan）阶段确保 `create_clients()` 成功，或禁用相关功能 |
| Milvus 插入失败 | 未创建集合或嵌入维度不匹配 | 确认 `embedding_dim` 与模型输出一致，并在 Docker 中启动 `milvus-standalone` |
| 内存占用持续升高 | 多模态管理器为进程内缓存 | 定期调用清理函数或落地到持久化存储 |

---

## 7. 下一步
- 根据业务需要扩展 `ConversationStore` 的 TTL、窗口大小或多租户隔离策略
- 实现自动化任务，将 Redis buffer 周期性刷写到 Elasticsearch/Milvus
- 在 LangGraph workflow 中引入召回节点，结合向量检索结果增强回复

按照以上策略，您可以依据现实部署情况自由组合 Redis、Elasticsearch、Milvus 与进程内缓存，实现 MAS 的会话与记忆体系。
