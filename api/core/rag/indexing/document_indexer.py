"""
文档索引器

该模块提供文档索引功能，将处理后的文档分块存储到向量数据库和搜索引擎。
支持批量索引、增量索引和错误处理。

核心功能:
- 文档分块和embedding生成
- 向量数据库索引（Milvus）
- 搜索引擎索引（Elasticsearch）
- 批量处理和进度跟踪
- 错误处理和重试
"""

from typing import Optional
from uuid import UUID

from elasticsearch import AsyncElasticsearch
from langfuse.decorators import observe
from pymilvus import MilvusClient

from config.rag_config import rag_config
from core.rag.chunking import document_processor
from core.rag.embedding_service import embedding_service
from infra.ops.milvus_client import get_milvus_connection
from libs.factory import infra_registry
from models import Document, DocumentChunk, DocumentChunkOrm, DocumentStatus, DocumentType
from repositories import DocumentRepository
from services import DocumentService
from utils import get_component_logger

logger = get_component_logger(__name__, "DocumentIndexer")


class IndexingResult:
    """索引结果"""

    def __init__(
        self,
        document_id: UUID,
        success: bool,
        chunk_count: int = 0,
        error: Optional[str] = None
    ):
        self.document_id = document_id
        self.success = success
        self.chunk_count = chunk_count
        self.error = error


class DocumentIndexer:
    """
    文档索引器

    负责将文档处理、分块、生成embedding并索引到向量数据库和搜索引擎。
    """

    def __init__(self):
        """初始化DocumentIndexer"""
        self.embedding_dimension = rag_config.EMBEDDING_DIMENSION
        self._milvus_client: Optional[MilvusClient] = None
        self._es_client: Optional[AsyncElasticsearch] = None

    async def _get_milvus_client(self) -> MilvusClient:
        """获取Milvus客户端"""
        if self._milvus_client is None:
            self._milvus_client = await get_milvus_connection()
        return self._milvus_client

    def _get_es_client(self) -> AsyncElasticsearch:
        """获取Elasticsearch客户端"""
        if self._es_client is None:
            self._es_client = infra_registry.get_cached_clients().elasticsearch
        return self._es_client

    @observe(name="index_document")
    async def index_document(
        self,
        document_id: UUID,
        collection_name: str = "documents",
        index_name: str = "documents"
    ) -> IndexingResult:
        """
        索引单个文档

        参数:
            document_id: 文档ID
            collection_name: Milvus集合名称
            index_name: Elasticsearch索引名称

        返回:
            IndexingResult: 索引结果
        """
        try:
            logger.info(f"开始索引文档: {document_id}")

            # 获取文档信息
            document = await DocumentService.get_document(document_id)
            if not document:
                return IndexingResult(
                    document_id=document_id,
                    success=False,
                    error="文档不存在"
                )

            # 更新文档状态为处理中
            await DocumentService.update_document_status(
                document_id,
                DocumentStatus.PROCESSING
            )

            # 处理文档并生成分块
            chunks = document_processor.process_document(
                file_path=document.file_path,
                file_type=document.file_type,
                metadata={
                    "document_id": str(document.document_id),
                    "tenant_id": document.tenant_id,
                    "title": document.title
                }
            )

            if not chunks:
                await DocumentService.update_document_status(
                    document_id,
                    DocumentStatus.FAILED,
                    error="文档分块失败或内容为空"
                )
                return IndexingResult(
                    document_id=document_id,
                    success=False,
                    error="文档分块失败或内容为空"
                )

            logger.info(f"文档分块完成: {len(chunks)} 个分块")

            # 生成embeddings
            chunk_texts = [chunk["content"] for chunk in chunks]
            embeddings = await embedding_service.generate_embeddings_batch(chunk_texts)

            logger.info(f"Embedding生成完成: {len(embeddings)} 个向量")

            # 保存分块到数据库
            chunk_orms = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_orm = DocumentChunkOrm(
                    document_id=document.document_id,
                    tenant_id=document.tenant_id,
                    chunk_index=i,
                    content=chunk["content"],
                    token_count=chunk["token_count"],
                    metadata=chunk["metadata"]
                )
                chunk_orms.append(chunk_orm)

            async with infra_registry.get_db_session() as session:
                saved_chunks = await DocumentRepository.insert_chunks(chunk_orms, session)

            logger.info(f"分块保存到数据库: {len(saved_chunks)} 个")

            # 索引到Milvus
            await self._index_to_milvus(
                document=document,
                chunks=saved_chunks,
                embeddings=embeddings,
                collection_name=collection_name
            )

            # 索引到Elasticsearch
            await self._index_to_elasticsearch(
                document=document,
                chunks=saved_chunks,
                index_name=index_name
            )

            # 更新文档状态和分块数量
            await DocumentService.update_document_status(
                document_id,
                DocumentStatus.INDEXED
            )
            await DocumentService.update_chunk_count(document_id, len(chunks))

            logger.info(f"文档索引完成: {document_id}, {len(chunks)} 个分块")

            return IndexingResult(
                document_id=document_id,
                success=True,
                chunk_count=len(chunks)
            )

        except Exception as e:
            logger.error(f"文档索引失败: {document_id}, 错误: {e}")

            # 更新文档状态为失败
            try:
                await DocumentService.update_document_status(
                    document_id,
                    DocumentStatus.FAILED,
                    error=str(e)
                )
            except Exception as update_error:
                logger.error(f"更新文档状态失败: {update_error}")

            return IndexingResult(
                document_id=document_id,
                success=False,
                error=str(e)
            )

    async def _index_to_milvus(
        self,
        document: Document,
        chunks: list[DocumentChunkOrm],
        embeddings: list[list[float]],
        collection_name: str
    ):
        """
        索引到Milvus向量数据库

        参数:
            document: 文档对象
            chunks: 分块列表
            embeddings: embedding向量列表
            collection_name: 集合名称
        """
        try:
            milvus_client = await self._get_milvus_client()

            # 确保集合存在
            await self._ensure_milvus_collection(milvus_client, collection_name)

            # 准备数据
            data = []
            for chunk, embedding in zip(chunks, embeddings):
                data.append({
                    "id": str(chunk.chunk_id),
                    "document_id": str(chunk.document_id),
                    "tenant_id": chunk.tenant_id,
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                    "embedding": embedding
                })

            # 批量插入
            milvus_client.insert(
                collection_name=collection_name,
                data=data
            )

            # 更新数据库中的embedding_id
            async with infra_registry.get_db_session() as session:
                for chunk in chunks:
                    await DocumentRepository.update_chunk_embedding_id(
                        chunk.chunk_id,
                        str(chunk.chunk_id),
                        session
                    )

            logger.info(f"Milvus索引完成: {len(data)} 个向量")

        except Exception as e:
            logger.error(f"Milvus索引失败: {e}")
            raise

    async def _ensure_milvus_collection(
        self,
        client: MilvusClient,
        collection_name: str
    ):
        """
        确保Milvus集合存在

        参数:
            client: Milvus客户端
            collection_name: 集合名称
        """
        try:
            # 检查集合是否存在
            if client.has_collection(collection_name):
                logger.debug(f"Milvus集合已存在: {collection_name}")
                return

            # 创建集合
            schema = client.create_schema(
                auto_id=False,
                enable_dynamic_field=True
            )

            # 添加字段
            schema.add_field(field_name="id", datatype="VARCHAR", max_length=255, is_primary=True)
            schema.add_field(field_name="document_id", datatype="VARCHAR", max_length=255)
            schema.add_field(field_name="tenant_id", datatype="VARCHAR", max_length=64)
            schema.add_field(field_name="content", datatype="VARCHAR", max_length=65535)
            schema.add_field(field_name="embedding", datatype="FLOAT_VECTOR", dim=self.embedding_dimension)

            # 创建索引参数
            index_params = client.prepare_index_params()
            index_params.add_index(
                field_name="embedding",
                index_type="IVF_FLAT",
                metric_type="COSINE",
                params={"nlist": 128}
            )

            # 创建集合
            client.create_collection(
                collection_name=collection_name,
                schema=schema,
                index_params=index_params
            )

            logger.info(f"Milvus集合创建成功: {collection_name}")

        except Exception as e:
            logger.error(f"创建Milvus集合失败: {e}")
            raise

    async def _index_to_elasticsearch(
        self,
        document: Document,
        chunks: list[DocumentChunkOrm],
        index_name: str
    ):
        """
        索引到Elasticsearch搜索引擎

        参数:
            document: 文档对象
            chunks: 分块列表
            index_name: 索引名称
        """
        try:
            es_client = self._get_es_client()

            # 确保索引存在
            await self._ensure_es_index(es_client, index_name)

            # 批量索引
            for chunk in chunks:
                doc = {
                    "chunk_id": str(chunk.chunk_id),
                    "document_id": str(chunk.document_id),
                    "tenant_id": chunk.tenant_id,
                    "content": chunk.content,
                    "token_count": chunk.token_count,
                    "metadata": chunk.metadata,
                    "created_at": chunk.created_at.isoformat() if chunk.created_at else None
                }

                await es_client.index(
                    index=index_name,
                    id=str(chunk.chunk_id),
                    document=doc
                )

            logger.info(f"Elasticsearch索引完成: {len(chunks)} 个文档")

        except Exception as e:
            logger.error(f"Elasticsearch索引失败: {e}")
            raise

    async def _ensure_es_index(
        self,
        client: AsyncElasticsearch,
        index_name: str
    ):
        """
        确保Elasticsearch索引存在

        参数:
            client: Elasticsearch客户端
            index_name: 索引名称
        """
        try:
            # 检查索引是否存在
            if await client.indices.exists(index=index_name):
                logger.debug(f"Elasticsearch索引已存在: {index_name}")
                return

            # 创建索引映射
            mappings = {
                "properties": {
                    "chunk_id": {"type": "keyword"},
                    "document_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "content": {
                        "type": "text",
                        "analyzer": "ik_max_word",
                        "search_analyzer": "ik_smart"
                    },
                    "token_count": {"type": "integer"},
                    "metadata": {"type": "object", "enabled": True},
                    "created_at": {"type": "date"}
                }
            }

            # 创建索引
            await client.indices.create(
                index=index_name,
                mappings=mappings
            )

            logger.info(f"Elasticsearch索引创建成功: {index_name}")

        except Exception as e:
            logger.error(f"创建Elasticsearch索引失败: {e}")
            raise

    async def index_documents_batch(
        self,
        document_ids: list[UUID],
        collection_name: str = "documents",
        index_name: str = "documents"
    ) -> dict[str, IndexingResult]:
        """
        批量索引文档

        参数:
            document_ids: 文档ID列表
            collection_name: Milvus集合名称
            index_name: Elasticsearch索引名称

        返回:
            dict[str, IndexingResult]: {document_id: result} 映射
        """
        results = {}

        for document_id in document_ids:
            result = await self.index_document(
                document_id,
                collection_name,
                index_name
            )
            results[str(document_id)] = result

        # 统计结果
        success_count = sum(1 for r in results.values() if r.success)
        failed_count = len(results) - success_count

        logger.info(f"批量索引完成: 成功 {success_count}, 失败 {failed_count}")

        return results


# 全局DocumentIndexer实例
document_indexer = DocumentIndexer()
