"""
文档数据访问存储库

该模块提供纯粹的文档数据访问操作，不包含业务逻辑。
遵循Repository模式，专注于数据持久化和查询操作。

核心功能:
- 文档数据库CRUD操作（PostgreSQL）
- 文档分块数据库CRUD操作（PostgreSQL）
- 纯数据访问，无业务逻辑
- 依赖注入，支持外部会话管理
"""

from collections.abc import Sequence
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update, func, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models import DocumentOrm, DocumentChunkOrm, DocumentStatus
from utils import get_component_logger

logger = get_component_logger(__name__, "DocumentRepository")


class DocumentRepository:
    """
    提供文档数据访问操作:
    1. 数据库操作 - PostgreSQL CRUD操作，依赖注入AsyncSession
    2. 无业务逻辑 - 仅处理数据持久化和检索
    3. 静态方法 - 无状态设计，支持依赖注入
    """

    # ==================== 文档操作 ====================

    @staticmethod
    async def get_document(document_id: UUID, session: AsyncSession) -> Optional[DocumentOrm]:
        """
        获取文档数据库模型

        参数:
            document_id: 文档ID
            session: 数据库会话

        返回:
            DocumentOrm: 文档数据库模型，不存在则返回None
        """
        try:
            stmt = select(DocumentOrm).where(DocumentOrm.document_id == document_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"获取文档数据库模型失败: {document_id}, 错误: {e}")
            raise

    @staticmethod
    async def get_documents_by_tenant(
        tenant_id: str,
        session: AsyncSession,
        limit: int = 100,
        offset: int = 0,
        status: Optional[DocumentStatus] = None
    ) -> Sequence[DocumentOrm]:
        """
        获取租户的文档列表

        参数:
            tenant_id: 租户ID
            session: 数据库会话
            limit: 返回数量限制
            offset: 偏移量
            status: 文档状态过滤（可选）

        返回:
            文档列表
        """
        try:
            stmt = select(DocumentOrm).where(DocumentOrm.tenant_id == tenant_id)

            if status:
                stmt = stmt.where(DocumentOrm.status == status)

            stmt = stmt.order_by(DocumentOrm.created_at.desc()).limit(limit).offset(offset)

            result = await session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"获取租户文档列表失败: {tenant_id}, 错误: {e}")
            raise

    @staticmethod
    async def insert_document(document: DocumentOrm, session: AsyncSession) -> DocumentOrm:
        """
        创建文档数据库模型

        参数:
            document: 文档ORM模型
            session: 数据库会话

        返回:
            创建的文档模型
        """
        try:
            session.add(document)
            await session.flush()
            await session.refresh(document)
            logger.info(f"创建文档: {document.document_id}, 标题: {document.title}")
            return document
        except Exception as e:
            logger.error(f"创建文档数据库模型失败: {document.title}, 错误: {e}")
            raise

    @staticmethod
    async def update_document(document: DocumentOrm, session: AsyncSession) -> DocumentOrm:
        """
        更新文档数据库模型

        参数:
            document: 文档ORM模型
            session: 数据库会话

        返回:
            更新后的文档模型
        """
        try:
            document.updated_at = func.now()
            merged_document = await session.merge(document)
            await session.flush()
            await session.refresh(merged_document)
            logger.debug(f"更新文档: {document.document_id}")
            return merged_document
        except Exception as e:
            logger.error(f"更新文档数据库模型失败: {document.document_id}, 错误: {e}")
            raise

    @staticmethod
    async def update_document_status(
        document_id: UUID,
        status: DocumentStatus,
        session: AsyncSession,
        error: Optional[str] = None
    ) -> Optional[DocumentOrm]:
        """
        更新文档状态

        参数:
            document_id: 文档ID
            status: 新状态
            session: 数据库会话
            error: 错误信息（可选）

        返回:
            更新后的文档模型
        """
        try:
            values = {
                "status": status,
                "updated_at": func.now()
            }
            if error:
                values["error"] = error

            stmt = (
                update(DocumentOrm)
                .where(DocumentOrm.document_id == document_id)
                .values(**values)
                .returning(DocumentOrm)
            )
            result = await session.execute(stmt)
            updated_doc = result.scalar_one_or_none()
            logger.info(f"更新文档状态: {document_id}, 状态: {status}")
            return updated_doc
        except Exception as e:
            logger.error(f"更新文档状态失败: {document_id}, 错误: {e}")
            raise

    @staticmethod
    async def update_document_chunk_count(
        document_id: UUID,
        chunk_count: int,
        session: AsyncSession
    ) -> Optional[DocumentOrm]:
        """
        更新文档分块数量

        参数:
            document_id: 文档ID
            chunk_count: 分块数量
            session: 数据库会话

        返回:
            更新后的文档模型
        """
        try:
            stmt = (
                update(DocumentOrm)
                .where(DocumentOrm.document_id == document_id)
                .values(chunk_count=chunk_count, updated_at=func.now())
                .returning(DocumentOrm)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"更新文档分块数量失败: {document_id}, 错误: {e}")
            raise

    @staticmethod
    async def delete_document(document_id: UUID, session: AsyncSession) -> bool:
        """
        删除文档（级联删除分块）

        参数:
            document_id: 文档ID
            session: 数据库会话

        返回:
            是否删除成功
        """
        try:
            stmt = delete(DocumentOrm).where(DocumentOrm.document_id == document_id)
            result = await session.execute(stmt)
            logger.info(f"删除文档: {document_id}")
            return result.rowcount > 0  # type: ignore
        except Exception as e:
            logger.error(f"删除文档失败: {document_id}, 错误: {e}")
            raise

    @staticmethod
    async def get_document_by_hash(
        tenant_id: str,
        file_hash: str,
        session: AsyncSession
    ) -> Optional[DocumentOrm]:
        """
        根据文件哈希查找文档（用于去重）

        参数:
            tenant_id: 租户ID
            file_hash: 文件SHA256哈希值
            session: 数据库会话

        返回:
            DocumentOrm: 文档数据库模型，不存在则返回None
        """
        try:
            stmt = select(DocumentOrm).where(
                and_(
                    DocumentOrm.tenant_id == tenant_id,
                    DocumentOrm.file_hash == file_hash
                )
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"根据哈希查找文档失败: {file_hash}, 错误: {e}")
            raise

    @staticmethod
    async def update_processing_stage(
        document_id: UUID,
        stage: str,
        session: AsyncSession,
        word_count: Optional[int] = None,
        token_count: Optional[int] = None
    ) -> Optional[DocumentOrm]:
        """
        更新文档处理阶段时间戳

        参数:
            document_id: 文档ID
            stage: 处理阶段 (started, parsing, cleaning, splitting, indexing)
            session: 数据库会话
            word_count: 文档字数（可选）
            token_count: 文档token数（可选）

        返回:
            更新后的文档模型
        """
        try:
            from datetime import datetime

            values = {"updated_at": func.now()}

            # 根据阶段设置对应的时间戳
            if stage == "started":
                values["processing_started_at"] = datetime.now()
            elif stage == "parsing":
                values["parsing_completed_at"] = datetime.now()
            elif stage == "cleaning":
                values["cleaning_completed_at"] = datetime.now()
            elif stage == "splitting":
                values["splitting_completed_at"] = datetime.now()
            elif stage == "indexing":
                values["indexing_completed_at"] = datetime.now()

            # 更新内容指标
            if word_count is not None:
                values["word_count"] = word_count
            if token_count is not None:
                values["token_count"] = token_count

            stmt = (
                update(DocumentOrm)
                .where(DocumentOrm.document_id == document_id)
                .values(**values)
                .returning(DocumentOrm)
            )
            result = await session.execute(stmt)
            updated_doc = result.scalar_one_or_none()
            logger.info(f"更新文档处理阶段: {document_id}, 阶段: {stage}")
            return updated_doc
        except Exception as e:
            logger.error(f"更新文档处理阶段失败: {document_id}, 错误: {e}")
            raise

    # ==================== 文档分块操作 ====================

    @staticmethod
    async def get_document_chunks(
        document_id: UUID,
        session: AsyncSession
    ) -> Sequence[DocumentChunkOrm]:
        """
        获取文档的所有分块

        参数:
            document_id: 文档ID
            session: 数据库会话

        返回:
            分块列表
        """
        try:
            stmt = (
                select(DocumentChunkOrm)
                .where(DocumentChunkOrm.document_id == document_id)
                .order_by(DocumentChunkOrm.chunk_index.asc())
            )
            result = await session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"获取文档分块失败: {document_id}, 错误: {e}")
            raise

    @staticmethod
    async def get_chunk(chunk_id: UUID, session: AsyncSession) -> Optional[DocumentChunkOrm]:
        """
        获取单个分块

        参数:
            chunk_id: 分块ID
            session: 数据库会话

        返回:
            分块模型
        """
        try:
            stmt = select(DocumentChunkOrm).where(DocumentChunkOrm.chunk_id == chunk_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"获取分块失败: {chunk_id}, 错误: {e}")
            raise

    @staticmethod
    async def insert_chunks(
        chunks: Sequence[DocumentChunkOrm],
        session: AsyncSession
    ) -> Sequence[DocumentChunkOrm]:
        """
        批量插入文档分块

        参数:
            chunks: 分块列表
            session: 数据库会话

        返回:
            插入的分块列表
        """
        try:
            session.add_all(chunks)
            await session.flush()
            for chunk in chunks:
                await session.refresh(chunk)
            logger.info(f"批量插入分块: {len(chunks)} 个")
            return chunks
        except Exception as e:
            logger.error(f"批量插入分块失败, 错误: {e}")
            raise

    @staticmethod
    async def update_chunk_embedding_id(
        chunk_id: UUID,
        embedding_id: str,
        session: AsyncSession
    ) -> Optional[DocumentChunkOrm]:
        """
        更新分块的embedding ID

        参数:
            chunk_id: 分块ID
            embedding_id: 向量数据库中的embedding ID
            session: 数据库会话

        返回:
            更新后的分块模型
        """
        try:
            stmt = (
                update(DocumentChunkOrm)
                .where(DocumentChunkOrm.chunk_id == chunk_id)
                .values(embedding_id=embedding_id)
                .returning(DocumentChunkOrm)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"更新分块embedding ID失败: {chunk_id}, 错误: {e}")
            raise

    @staticmethod
    async def delete_document_chunks(document_id: UUID, session: AsyncSession) -> int:
        """
        删除文档的所有分块

        参数:
            document_id: 文档ID
            session: 数据库会话

        返回:
            删除的分块数量
        """
        try:
            stmt = delete(DocumentChunkOrm).where(DocumentChunkOrm.document_id == document_id)
            result = await session.execute(stmt)
            logger.info(f"删除文档分块: {document_id}, 数量: {result.rowcount}")
            return result.rowcount  # type: ignore
        except Exception as e:
            logger.error(f"删除文档分块失败: {document_id}, 错误: {e}")
            raise

    @staticmethod
    async def get_chunks_by_tenant(
        tenant_id: str,
        session: AsyncSession,
        limit: int = 100
    ) -> Sequence[DocumentChunkOrm]:
        """
        获取租户的所有分块（用于检索）

        参数:
            tenant_id: 租户ID
            session: 数据库会话
            limit: 返回数量限制

        返回:
            分块列表
        """
        try:
            stmt = (
                select(DocumentChunkOrm)
                .where(DocumentChunkOrm.tenant_id == tenant_id)
                .order_by(DocumentChunkOrm.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"获取租户分块失败: {tenant_id}, 错误: {e}")
            raise
