#!/usr/bin/env python3
"""
数据库设置脚本

该脚本用于初始化PostgreSQL数据库，创建表结构和默认数据。
适用于云端部署环境。
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from infra.db.connection import (
    get_database_engine, 
    test_database_connection,
    close_database_connections
)
from models.tenant import Base
from api.dependencies.tenant_manager import get_tenant_manager
from src.utils import get_component_logger
from config.settings import settings

logger = get_component_logger(__name__, "DatabaseSetup")


async def create_tables():
    """创建数据库表"""
    try:
        logger.info("开始创建数据库表...")
        engine = await get_database_engine()
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("数据库表创建成功")
        return True
        
    except Exception as e:
        logger.error(f"创建数据库表失败: {e}")
        return False


async def create_default_tenant():
    """创建默认租户"""
    try:
        logger.info("开始创建默认租户...")
        tenant_manager = await get_tenant_manager()
        
        # 获取默认租户配置（会自动创建）
        default_config = await tenant_manager.get_tenant_config("default")
        if default_config:
            logger.info(f"默认租户创建成功: {default_config.tenant_name}")
            return True
        else:
            logger.error("默认租户创建失败")
            return False
            
    except Exception as e:
        logger.error(f"创建默认租户失败: {e}")
        return False


async def verify_setup():
    """验证数据库设置"""
    try:
        logger.info("验证数据库设置...")
        
        # 测试连接
        if not await test_database_connection():
            logger.error("数据库连接测试失败")
            return False
        
        # 验证租户管理器
        tenant_manager = await get_tenant_manager()
        health_status = await tenant_manager.health_check()
        
        if health_status["status"] == "healthy":
            logger.info("数据库设置验证成功")
            logger.info(f"健康状态: {health_status}")
            return True
        else:
            logger.error(f"数据库设置验证失败: {health_status}")
            return False
            
    except Exception as e:
        logger.error(f"验证数据库设置失败: {e}")
        return False


async def main():
    """主函数"""
    logger.info("=== MAS 数据库初始化脚本 ===")
    logger.info(f"PostgreSQL Host: {settings.postgres_host}")
    logger.info(f"Database: {settings.postgres_db}")
    
    try:
        # Step 1: 测试数据库连接
        logger.info("步骤 1: 测试数据库连接...")
        if not await test_database_connection():
            logger.error("数据库连接失败，请检查配置")
            return False
        logger.info("✅ 数据库连接成功")
        
        # Step 2: 创建数据库表
        logger.info("步骤 2: 创建数据库表...")
        if not await create_tables():
            logger.error("创建数据库表失败")
            return False
        logger.info("✅ 数据库表创建成功")
        
        # Step 3: 创建默认租户
        logger.info("步骤 3: 创建默认租户...")
        if not await create_default_tenant():
            logger.error("创建默认租户失败")
            return False
        logger.info("✅ 默认租户创建成功")
        
        # Step 4: 验证设置
        logger.info("步骤 4: 验证设置...")
        if not await verify_setup():
            logger.error("验证设置失败")
            return False
        logger.info("✅ 设置验证成功")
        
        logger.info("=== 数据库初始化完成 ===")
        return True
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        return False
        
    finally:
        # 清理连接
        await close_database_connections()


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
