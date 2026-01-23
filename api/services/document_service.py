"""
文档业务服务层

该模块实现文档管理相关的业务逻辑和协调功能。
遵循Service模式，协调文件存储和数据库操作，提供文档上传、管理和检索服务。

核心功能:
- 文档上传和文件存储管理
- 文档元数据管理（数据库）
- 文档状态跟踪和更新
- 文档查询和列表获取
"""

import os
from pathlib import Path
from typing import Optional, Sequence
from uuid import UUID, uuid4

from libs.exceptions import DocumentNotFoundException
from libs.factory import infra_registry
from models import Document, DocumentOrm, DocumentStatus, DocumentType
from repositories import DocumentRepository
from utils import get_component_logger

logger = get_component_logger(__name__, "DocumentService")

# 文档存储根目录
DOCUMENT_STORAGE_ROOT = Path("storage/documents")

# 支持的文件类型和扩展名映射
FILE_TYPE_EXTENSIONS = {
    DocumentType.TXT: [".txt"],
    DocumentType.MD: [".md", ".markdown"],
    DocumentType.PDF: [".pdf"],
    DocumentType.DOCX: [".docx", ".doc"],
}

# 文件大小限制（字节）
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class DocumentService:
    """
    实现文档管理的业务逻辑:
    1. 文件存储 - 本地文件系统存储
    2. 元数据管理 - PostgreSQL 数据库
    3. 业务协调 - 文件和数据库操作的统一协调
    """

    @staticmethod
    def _get_file_type(filename: str) -> DocumentType:
        """
        根据文件名获取文档类型

        参数:
            filename: 文件名

        返回:
            DocumentType: 文档类型
        """
        ext = Path(filename).suffix.lower()
        for doc_type, extensions in FILE_TYPE_EXTENSIONS.items():
            if ext in extensions:
                return doc_type
        return DocumentType.OTHER

    @staticmethod
    def _calculate_file_hash(file_content: bytes) -> str:
        """
        计算文件SHA256哈希值

        参数:
            file_content: 文件内容（字节）

        返回:
            str: SHA256哈希值（十六进制字符串）
        """
        import hashlib
        return hashlib.sha256(file_content).hexdigest()

    @staticmethod
    def _get_storage_path(tenant_id: str, document_id: UUID, filename: str) -> Path:
        """
        生成文档存储路径

        参数:
            tenant_id: 租户ID
            document_id: 文档ID
            filename: 原始文件名

        返回:
            Path: 存储路径
        """
        # 按租户组织目录结构: storage/documents/{tenant_id}/{document_id}_{filename}
        tenant_dir = DOCUMENT_STORAGE_ROOT / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)
        return tenant_dir / f"{document_id}_{filename}"

    @staticmethod
    async def upload_document(
        tenant_id: str,
        filename: str,
        file_content: bytes,
        title: Optional[str] = None
    ) -> UUID:
        """
        上传文档

        参数:
            tenant_id: 租户ID
            filename: 文件名
            file_content: 文件内容（字节）
            title: 文档标题（可选，默认使用文件名）

        返回:
            UUID: 文档ID

        异常:
            ValueError: 文件大小超过限制或文件类型不支持
        """
        try:
            # 验证文件大小
            file_size = len(file_content)
            if file_size > MAX_FILE_SIZE:
                raise ValueError(f"文件大小超过限制: {file_size} > {MAX_FILE_SIZE}")

            # 计算文件哈希
            file_hash = DocumentService._calculate_file_hash(file_content)

            # 检查是否已存在相同文件（去重）
            existing = await DocumentService.get_document_by_hash(tenant_id, file_hash)
            if existing:
                logger.info(f"文档已存在（去重）: {existing.document_id}, 哈希: {file_hash}")
                return existing.document_id

            # 确定文件类型
            file_type = DocumentService._get_file_type(filename)

            # 生成文档ID和存储路径
            document_id = uuid4()
            storage_path = DocumentService._get_storage_path(tenant_id, document_id, filename)

            # 保存文件到本地存储
            storage_path.write_bytes(file_content)
            logger.info(f"文件保存成功: {storage_path}")

            # 创建文档元数据
            document = Document(
                document_id=document_id,
                tenant_id=tenant_id,
                title=title or filename,
                file_path=str(storage_path),
                original_filename=filename,
                file_type=file_type,
                file_size=file_size,
                file_hash=file_hash,
                status=DocumentStatus.PENDING
            )

            # 保存到数据库
            async with infra_registry.get_db_session() as session:
                document_orm = await DocumentRepository.insert_document(
                    document.to_orm(),
                    session
                )

            logger.info(f"文档上传成功: {document_id}, 标题: {document.title}")
            return document_orm.document_id

        except Exception as e:
            logger.error(f"文档上传失败: {filename}, 错误: {e}")
            # 清理已保存的文件（如果存在）
            if 'storage_path' in locals() and storage_path.exists():
                storage_path.unlink()
            raise

    @staticmethod
    async def get_document(document_id: UUID) -> Optional[Document]:
        """
        获取文档元数据

        参数:
            document_id: 文档ID

        返回:
            Document: 文档模型，不存在则返回None
        """
        try:
            async with infra_registry.get_db_session() as session:
                document_orm = await DocumentRepository.get_document(document_id, session)

            if document_orm:
                return Document.to_model(document_orm)
            return None

        except Exception as e:
            logger.error(f"获取文档失败: {document_id}, 错误: {e}")
            return None

    @staticmethod
    async def get_documents_by_tenant(
        tenant_id: str,
        limit: int = 100,
        offset: int = 0,
        status: Optional[DocumentStatus] = None
    ) -> Sequence[Document]:
        """
        获取租户的文档列表

        参数:
            tenant_id: 租户ID
            limit: 返回数量限制
            offset: 偏移量
            status: 文档状态过滤（可选）

        返回:
            文档列表
        """
        try:
            async with infra_registry.get_db_session() as session:
                documents_orm = await DocumentRepository.get_documents_by_tenant(
                    tenant_id, session, limit, offset, status
                )

            return [Document.to_model(doc) for doc in documents_orm]

        except Exception as e:
            logger.error(f"获取租户文档列表失败: {tenant_id}, 错误: {e}")
            return []

    @staticmethod
    async def update_document_status(
        document_id: UUID,
        status: DocumentStatus,
        error: Optional[str] = None
    ) -> Document:
        """
        更新文档状态

        参数:
            document_id: 文档ID
            status: 新状态
            error: 错误信息（可选）

        返回:
            Document: 更新后的文档模型

        异常:
            DocumentNotFoundException: 文档不存在
        """
        try:
            async with infra_registry.get_db_session() as session:
                document_orm = await DocumentRepository.update_document_status(
                    document_id, status, session, error
                )

            if not document_orm:
                raise DocumentNotFoundException(document_id)

            logger.info(f"文档状态更新成功: {document_id}, 状态: {status}")
            return Document.to_model(document_orm)

        except Exception as e:
            logger.error(f"更新文档状态失败: {document_id}, 错误: {e}")
            raise

    @staticmethod
    async def update_document_metadata(
        document_id: UUID,
        title: Optional[str] = None
    ) -> Document:
        """
        更新文档元数据

        参数:
            document_id: 文档ID
            title: 新标题（可选）

        返回:
            Document: 更新后的文档模型

        异常:
            DocumentNotFoundException: 文档不存在
        """
        try:
            async with infra_registry.get_db_session() as session:
                document_orm = await DocumentRepository.get_document(document_id, session)

                if not document_orm:
                    raise DocumentNotFoundException(document_id)

                # 更新字段
                if title is not None:
                    document_orm.title = title

                # 保存更新
                document_orm = await DocumentRepository.update_document(document_orm, session)

            logger.info(f"文档元数据更新成功: {document_id}")
            return Document.to_model(document_orm)

        except Exception as e:
            logger.error(f"更新文档元数据失败: {document_id}, 错误: {e}")
            raise

    @staticmethod
    async def delete_document(document_id: UUID) -> bool:
        """
        删除文档（包括文件和数据库记录）

        参数:
            document_id: 文档ID

        返回:
            bool: 是否删除成功
        """
        try:
            # 获取文档信息
            async with infra_registry.get_db_session() as session:
                document_orm = await DocumentRepository.get_document(document_id, session)

                if not document_orm:
                    logger.warning(f"文档不存在: {document_id}")
                    return False

                # 删除文件
                file_path = Path(document_orm.file_path)
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"文件删除成功: {file_path}")

                # 删除数据库记录（级联删除分块）
                success = await DocumentRepository.delete_document(document_id, session)

            logger.info(f"文档删除成功: {document_id}")
            return success

        except Exception as e:
            logger.error(f"删除文档失败: {document_id}, 错误: {e}")
            raise

    @staticmethod
    async def get_document_content(document_id: UUID) -> Optional[bytes]:
        """
        获取文档文件内容

        参数:
            document_id: 文档ID

        返回:
            bytes: 文件内容，文档不存在则返回None
        """
        try:
            async with infra_registry.get_db_session() as session:
                document_orm = await DocumentRepository.get_document(document_id, session)

            if not document_orm:
                return None

            file_path = Path(document_orm.file_path)
            if not file_path.exists():
                logger.error(f"文件不存在: {file_path}")
                return None

            return file_path.read_bytes()

        except Exception as e:
            logger.error(f"获取文档内容失败: {document_id}, 错误: {e}")
            return None

    @staticmethod
    async def create_document_metadata(
        tenant_id: str,
        file_url: str,
        original_filename: str,
        file_size: int,
        file_hash: Optional[str] = None,
        mime_type: Optional[str] = None,
        title: Optional[str] = None
    ) -> UUID:
        """
        创建文档元数据（用于外部存储场景）

        参数:
            tenant_id: 租户ID
            file_url: 文件存储URL（外部系统）
            original_filename: 原始文件名
            file_size: 文件大小（字节）
            file_hash: 文件SHA256哈希值（可选，用于去重）
            mime_type: MIME类型（可选）
            title: 文档标题（可选，默认使用文件名）

        返回:
            UUID: 文档ID

        异常:
            ValueError: 参数验证失败
        """
        try:
            # 检查是否已存在相同文件（去重）
            if file_hash:
                existing = await DocumentService.get_document_by_hash(tenant_id, file_hash)
                if existing:
                    logger.info(f"文档已存在（去重）: {existing.document_id}, 哈希: {file_hash}")
                    return existing.document_id

            # 确定文件类型
            file_type = DocumentService._get_file_type(original_filename)

            # 生成文档ID
            document_id = uuid4()

            # 创建文档元数据
            document = Document(
                document_id=document_id,
                tenant_id=tenant_id,
                title=title or original_filename,
                file_path=file_url,  # 存储URL而非本地路径
                original_filename=original_filename,
                file_type=file_type,
                file_size=file_size,
                file_hash=file_hash,
                mime_type=mime_type,
                status=DocumentStatus.PENDING
            )

            # 保存到数据库
            async with infra_registry.get_db_session() as session:
                document_orm = await DocumentRepository.insert_document(
                    document.to_orm(),
                    session
                )

            logger.info(f"文档元数据创建成功: {document_id}, URL: {file_url}")
            return document_orm.document_id

        except Exception as e:
            logger.error(f"创建文档元数据失败: {original_filename}, 错误: {e}")
            raise

    @staticmethod
    async def get_document_by_hash(
        tenant_id: str,
        file_hash: str
    ) -> Optional[Document]:
        """
        根据文件哈希查找文档（去重）

        参数:
            tenant_id: 租户ID
            file_hash: 文件SHA256哈希值

        返回:
            Document: 文档模型，不存在则返回None
        """
        try:
            async with infra_registry.get_db_session() as session:
                document_orm = await DocumentRepository.get_document_by_hash(
                    tenant_id, file_hash, session
                )

            if document_orm:
                return Document.to_model(document_orm)
            return None

        except Exception as e:
            logger.error(f"根据哈希查找文档失败: {file_hash}, 错误: {e}")
            return None

    @staticmethod
    async def update_chunk_count(document_id: UUID, chunk_count: int) -> Document:
        """
        更新文档分块数量

        参数:
            document_id: 文档ID
            chunk_count: 分块数量

        返回:
            Document: 更新后的文档模型

        异常:
            DocumentNotFoundException: 文档不存在
        """
        try:
            async with infra_registry.get_db_session() as session:
                document_orm = await DocumentRepository.update_document_chunk_count(
                    document_id, chunk_count, session
                )

            if not document_orm:
                raise DocumentNotFoundException(document_id)

            logger.info(f"文档分块数量更新成功: {document_id}, 数量: {chunk_count}")
            return Document.to_model(document_orm)

        except Exception as e:
            logger.error(f"更新文档分块数量失败: {document_id}, 错误: {e}")
            raise

    @staticmethod
    async def update_processing_stage(
        document_id: UUID,
        stage: str,
        word_count: Optional[int] = None,
        token_count: Optional[int] = None
    ) -> Document:
        """
        更新文档处理阶段时间戳

        参数:
            document_id: 文档ID
            stage: 处理阶段 (started, parsing, cleaning, splitting, indexing)
            word_count: 文档字数（可选）
            token_count: 文档token数（可选）

        返回:
            Document: 更新后的文档模型

        异常:
            DocumentNotFoundException: 文档不存在
        """
        try:
            async with infra_registry.get_db_session() as session:
                document_orm = await DocumentRepository.update_processing_stage(
                    document_id, stage, session, word_count, token_count
                )

            if not document_orm:
                raise DocumentNotFoundException(document_id)

            logger.info(f"文档处理阶段更新成功: {document_id}, 阶段: {stage}")
            return Document.to_model(document_orm)

        except Exception as e:
            logger.error(f"更新文档处理阶段失败: {document_id}, 错误: {e}")
            raise
