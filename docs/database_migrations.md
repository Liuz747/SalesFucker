# 数据库迁移指南

本指南基于当前的 MAS 仓库结构：FastAPI 后端位于 `api/`，迁移脚本放在 `api/scripts/database.py`，Alembic 配置位于 `api/migrations/`。请始终在 `api/` 目录下执行命令。

---

## 1. Alembic 结构
```text
api/
├── scripts/database.py        # 统一入口：upgrade / revision / downgrade
├── migrations/
│   ├── alembic.ini
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 6ee06edc35dd_modify_data_model.py
└── models/
    └── *.py                   # SQLAlchemy 基础模型
```
`env.py` 已配置异步 SQLAlchemy 引擎，自动加载 `models/` 中的元数据。`scripts/database.py` 会在执行迁移前测试数据库连接并复用全局异步引擎。

---

## 2. 常用命令
确保处于 `api/` 目录，并已配置好 `.env`（至少包含 PostgreSQL 连接信息）。

```bash
# 升级到最新版本
uv run python scripts/database.py

# 生成新迁移（自动检测模型变化）
uv run python scripts/database.py revision "add tenant webhook"

# 回滚到上一版本
uv run python scripts/database.py downgrade -1
```

命令说明：
- **无额外指令**：同步数据库
- **revision**：开启 `autogenerate=True` 并写入自定义信息
- **downgrade**：默认回退 1 个版本，可指定目标，如 `downgrade base`

---

## 3. 团队协作流程

### 3.1 新增模型 / 字段
1. 修改或新增 `api/models/*.py`
2. 在 `api/` 目录执行 `uv run python scripts/database.py revision "description"`
3. 检查 `migrations/versions/` 下的自动生成文件，必要时手动调整
4. 将模型与迁移一并提交 PR：
   ```bash
   git add models/*.py migrations/versions/<new_revision>.py
   git commit -m "feat: add tenant webhook"
   ```

### 3.2 同步他人更新
1. 拉取最新代码
   ```bash
   git pull
   ```
2. 在 `api/` 目录执行升级
   ```bash
   uv run python scripts/database.py
   ```
3. 如需要回滚到旧版本用于调试
   ```bash
   uv run python scripts/database.py downgrade -1
   ```

---

## 4. 常见问题

| 问题 | 原因 | 解决方式 |
| --- | --- | --- |
| 数据库连接失败 | `.env` 中的 `DB_HOST/DB_PORT/POSTGRES_*` 配置错误或服务未启动 | 确认 `docker/docker-compose.dev.yml` 中 PostgreSQL 已运行，检查端口映射 |
| 生成的迁移为空 | 模型未导入、自动检测不到差异 | 确保模型继承自 `models.base.Base` 并在 `env.py` 中正确导入；如确需空迁移，可保留作为标记 |
| 字段顺序或默认值不符合预期 | 自动生成的迁移需要人工校验 | 打开生成文件，按需求手动调整 `op.add_column` / `op.alter_column` 逻辑 |

---

## 5. 最佳实践
- 每次修改模型后，**先运行测试**再生成迁移，确保 ORM 定义可用
- 避免在同一 PR 中生成多个迁移；若发生冲突，保留较新的 revision，并在本地重新生成
- 生产部署前，先在 staging 环境执行 `upgrade` 进行验证，必要时准备 `downgrade` 回滚方案
- 对大表或重度索引操作，建议手动拆分迁移步骤，并添加相应注释

遵循以上流程即可保持 MAS 数据库 schema 的可追溯性与团队协同效率。
