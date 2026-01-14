"""
MAS 数据库迁移脚本
"""

import asyncio
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from alembic import command
from alembic.config import Config

from infra.db import create_db_engine
from utils import get_component_logger

logger = get_component_logger(__name__, "Database")

def run_upgrade(connection, cfg, revision):
    """在给定连接上运行数据库迁移"""
    cfg.attributes["connection"] = connection
    command.upgrade(cfg, revision)

async def upgrade():
    """运行数据库迁移"""
    try:
        logger.info("开始数据库迁移...")

        # 使用异步引擎和连接共享模式
        engine = await create_db_engine()
        cfg = Config("migrations/alembic.ini")
        
        async with engine.begin() as conn:
            await conn.run_sync(run_upgrade, cfg, "head")

        return True

    except Exception as e:
        logger.error(f"❌ 数据库迁移失败: {e}")
        return False


def run_revision(connection, cfg, message):
    """在给定连接上运行迁移文件生成"""
    cfg.attributes["connection"] = connection
    command.revision(cfg, autogenerate=True, message=message)

async def revision(message: str):
    """生成新的迁移文件"""
    try:
        logger.info(f"生成迁移文件: {message}")

        # 使用异步引擎和连接共享模式
        engine = await create_db_engine()
        cfg = Config("migrations/alembic.ini")
        
        async with engine.begin() as conn:
            await conn.run_sync(run_revision, cfg, message)
        
        return True

    except Exception as e:
        logger.error(f"❌ 迁移文件生成失败: {e}")
        return False

def run_downgrade(connection, cfg, revision):
    """在给定连接上运行数据库回滚"""
    cfg.attributes["connection"] = connection
    command.downgrade(cfg, revision)

async def downgrade(revision: str = "-1"):
    """回滚数据库迁移"""
    try:
        logger.info(f"回滚数据库迁移到版本: {revision}")

        engine = await create_db_engine()
        cfg = Config("migrations/alembic.ini")
        
        async with engine.begin() as conn:
            await conn.run_sync(run_downgrade, cfg, revision)

        return True

    except Exception as e:
        logger.error(f"❌ 数据库回滚失败: {e}")
        return False

async def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "revision":
            message = sys.argv[2] if len(sys.argv) > 2 else "Auto-generated migration"
            flag = await revision(message)
        elif sys.argv[1] == "downgrade":
            message = sys.argv[2] if len(sys.argv) > 2 else "-1"
            flag = await downgrade(message)
        else:
            logger.error("未知命令，支持: revision <message>, downgrade [revision]")
            flag = False
    else:
        # 默认运行迁移
        flag = await upgrade()

    sys.exit(0 if flag else 1)

if __name__ == "__main__":
    asyncio.run(main())
