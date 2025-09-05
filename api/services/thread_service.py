"""
线程数据库操作层

该模块提供纯粹的线程数据库CRUD操作，不包含业务逻辑。
遵循Repository模式，专注于数据持久化和查询操作。

核心功能:
- 线程配置的数据库CRUD操作
- 数据库健康检查
"""

from typing import Optional, List

from sqlalchemy import select, update

from models import ThreadOrm
from infra.db.connection import database_session
from utils import get_component_logger, get_current_datetime

logger = get_component_logger(__name__, "ThreadService")


class ThreadService:
    """
    线程数据库操作仓库
    
    提供纯粹的数据库操作
    所有方法都是静态的，不维护状态。
    """
    
    @staticmethod
    async def _get_thread_by_id(session, thread_id: str) -> Optional[ThreadOrm]:
        """
        获取线程数据库模型
        
        参数:
            session: 数据库会话
            thread_id: 线程ID
            
        返回:
            ThreadOrm: 线程数据库模型，不存在则返回None
        """
        stmt = select(ThreadOrm).where(ThreadOrm.thread_id == thread_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def query(thread_id: str) -> Optional[ThreadOrm]:
        """
        根据ID获取线程ORM对象
        
        参数:
            thread_id: 线程ID
            
        返回:
            Optional[ThreadOrm]: 线程ORM对象，不存在则返回None
        """
        try:
            async with database_session() as session:
                return await ThreadService._get_thread_by_id(session, thread_id)

        except Exception as e:
            logger.error(f"获取线程配置失败: {thread_id}, 错误: {e}")
            raise
    
    @staticmethod
    async def save(config):
        """
        创建新线程配置
        
        参数:
            config: 线程配置
            
        返回:
            bool: 是否保存成功
        """
        try:
            async with database_session() as session:
                # 创建新线程
                # TODO: 需要添加thread_id的唯一性校验，upsert语句
                new_thread = ThreadOrm(
                    thread_id=config.thread_id,
                    assistant_id=config.assistant_id,
                    tenant_id=config.metadata.tenant_id,
                    status=config.status,
                    created_at=config.created_at,
                    updated_at=config.updated_at
                )
                session.add(new_thread)
                logger.debug(f"创建线程: {config.thread_id}")
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"创建线程配置失败: {config.thread_id}, 错误: {e}")
            raise
    
    
    @staticmethod
    async def upsert(
        thread_id: str,
        assistant_id: Optional[str] = None,
        tenant_id: str = None
    ) -> bool:
        """
        创建或更新线程配置
        
        参数:
            thread_id: 线程ID
            assistant_id: 助理ID
            tenant_id: 租户ID
            
        返回:
            bool: 是否保存成功
        """
        try:
            async with database_session() as session:
                # 查找现有线程
                existing_thread = await ThreadService._get_thread_by_id(session, thread_id)
                
                if existing_thread:
                    # 更新现有线程
                    if assistant_id is not None:
                        existing_thread.assistant_id = assistant_id
                    if tenant_id is not None:
                        existing_thread.tenant_id = tenant_id
                    existing_thread.updated_at = get_current_datetime()
                    logger.debug(f"更新线程: {thread_id}")
                else:
                    # 创建新线程
                    new_thread = ThreadOrm(
                        thread_id=thread_id,
                        assistant_id=assistant_id,
                        tenant_id=tenant_id,
                        status="active",
                        created_at=get_current_datetime(),
                        updated_at=get_current_datetime()
                    )
                    session.add(new_thread)
                    logger.debug(f"创建线程: {thread_id}")
                
                await session.commit()
                return True
                
        except Exception as e:
            logger.error(f"保存线程配置失败: {thread_id}, 错误: {e}")
            raise
    
    @staticmethod
    async def update(config) -> bool:
        """
        更新线程配置
        
        参数:
            config: 线程配置
            
        返回:
            bool: 是否更新成功
        """
        try:
            async with database_session() as session:
                stmt = (
                    update(ThreadOrm)
                    .where(ThreadOrm.thread_id == config.thread_id)
                    .values(
                        assistant_id=config.assistant_id,
                        tenant_id=config.metadata.tenant_id,
                        status=config.status,
                        updated_at=config.updated_at
                    )
                )
                result = await session.execute(stmt)
                await session.commit()
                
                flag = result.rowcount > 0
                if flag:
                    logger.debug(f"更新线程: {config.thread_id}")
                else:
                    logger.warning(f"线程不存在，无法更新: {config.thread_id}")
                    
                return flag
                
        except Exception as e:
            logger.error(f"更新线程配置失败: {config.thread_id}, 错误: {e}")
            raise
    
    @staticmethod
    async def delete(thread_id: str) -> bool:
        """
        删除线程（软删除）
        
        参数:
            thread_id: 线程ID
            
        返回:
            bool: 是否删除成功
        """
        try:
            async with database_session() as session:
                # 软删除：设置为失败状态
                stmt = (
                    update(ThreadOrm)
                    .where(ThreadOrm.thread_id == thread_id)
                    .values(status="failed")
                )
                result = await session.execute(stmt)
                await session.commit()
                
                flag = result.rowcount > 0
                if flag:
                    logger.info(f"软删除线程: {thread_id}")
                else:
                    logger.warning(f"线程不存在，无法删除: {thread_id}")
                    
                return flag

        except Exception as e:
            logger.error(f"删除线程失败: {thread_id}, 错误: {e}")
            raise
    
    @staticmethod
    async def get_all_threads() -> List[str]:
        """
        获取所有激活状态的线程ID列表
        
        返回:
            List[str]: 激活的线程ID列表
        """
        try:
            async with database_session() as session:
                stmt = select(ThreadOrm.thread_id).where(ThreadOrm.status == "active")
                result = await session.execute(stmt)
                thread_ids = [row[0] for row in result.fetchall()]
                
                logger.debug(f"查询到 {len(thread_ids)} 个活跃线程")
                return thread_ids

        except Exception as e:
            logger.error(f"获取线程列表失败: {e}")
            raise
