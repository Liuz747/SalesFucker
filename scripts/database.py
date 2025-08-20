#!/usr/bin/env python3
"""
MAS 数据库迁移脚本
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from alembic import command
from alembic.config import Config
from infra.db.connection import test_db_connection
from utils import get_component_logger

logger = get_component_logger(__name__, "Database")

async def upgrade():
    """运行数据库迁移"""
    try:
        logger.info("开始数据库迁移...")

        # Test connection first
        if not await test_db_connection():
            raise Exception("数据库连接失败")

        # Run Alembic migrations
        cfg = Config("migrations/alembic.ini")
        command.upgrade(cfg, "head")

        logger.info("✅ 数据库迁移完成")
        return True

    except Exception as e:
        logger.error(f"❌ 数据库迁移失败: {e}")
        return False

def revision(message: str):
    """生成新的迁移文件"""
    try:
        logger.info(f"生成迁移文件: {message}")

        cfg = Config("migrations/alembic.ini")
        command.revision(cfg, autogenerate=True, message=message)

        logger.info("✅ 迁移文件生成完成")
        return True

    except Exception as e:
        logger.error(f"❌ 迁移文件生成失败: {e}")
        return False

async def main():
    """主函数"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "revision":
            message = sys.argv[2] if len(sys.argv) > 2 else "Auto-generated migration"
            flag = revision(message)
        else:
            logger.error("未知命令，支持: revision <message>")
            flag = False
    else:
        # 默认运行迁移
        flag = await upgrade()

    sys.exit(0 if flag else 1)

if __name__ == "__main__":
    asyncio.run(main())
