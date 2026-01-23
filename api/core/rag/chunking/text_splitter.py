"""
文本分块器

该模块提供文本分块功能，将长文档分割成适合检索的小块。
支持多种分块策略，包括语义分块、固定大小分块和Markdown感知分块。

核心功能:
- 语义分块（句子边界感知）
- 固定大小分块（带重叠）
- Markdown结构保留
- 中文文本支持
- Token计数
"""

import re
from typing import Optional

import tiktoken

from config.rag_config import rag_config
from utils import get_component_logger

logger = get_component_logger(__name__, "TextSplitter")


class TextSplitter:
    """
    文本分块器

    将长文本分割成适合检索和embedding的小块。
    支持多种分块策略和中文文本处理。
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[float] = None,
        encoding_name: str = "cl100k_base"
    ):
        """
        初始化TextSplitter

        参数:
            chunk_size: 分块大小（tokens），默认使用配置值
            chunk_overlap: 分块重叠比例（0-1），默认使用配置值
            encoding_name: tiktoken编码名称
        """
        self.chunk_size = chunk_size or rag_config.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or rag_config.CHUNK_OVERLAP
        self.min_chunk_size = rag_config.MIN_CHUNK_SIZE
        self.max_chunk_size = rag_config.MAX_CHUNK_SIZE

        # 初始化tokenizer
        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
        except Exception as e:
            logger.warning(f"无法加载tiktoken编码 {encoding_name}: {e}，使用默认编码")
            self.encoding = tiktoken.get_encoding("cl100k_base")

        # 句子分隔符（中英文）
        self.sentence_separators = [
            "\n\n",  # 段落分隔
            "\n",    # 换行
            "。",    # 中文句号
            "！",    # 中文感叹号
            "？",    # 中文问号
            ".",     # 英文句号
            "!",     # 英文感叹号
            "?",     # 英文问号
        ]

    def count_tokens(self, text: str) -> int:
        """
        计算文本的token数量

        参数:
            text: 文本内容

        返回:
            int: token数量
        """
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.error(f"计算token数量失败: {e}")
            # 降级方案：按字符数估算（中文约1.5 tokens/字符，英文约0.25 tokens/字符）
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
            english_chars = len(text) - chinese_chars
            return int(chinese_chars * 1.5 + english_chars * 0.25)

    def split_text(
        self,
        text: str,
        metadata: Optional[dict] = None
    ) -> list[dict]:
        """
        分割文本为多个块

        参数:
            text: 要分割的文本
            metadata: 元数据（会附加到每个块）

        返回:
            list[dict]: 分块列表，每个块包含content、token_count、metadata
        """
        if not text or not text.strip():
            return []

        # 使用语义分块策略
        chunks = self._semantic_split(text)

        # 构建结果
        result = []
        for i, chunk_text in enumerate(chunks):
            token_count = self.count_tokens(chunk_text)

            # 跳过太小的块
            if token_count < self.min_chunk_size:
                logger.debug(f"跳过过小的块: {token_count} tokens")
                continue

            chunk_metadata = {
                "chunk_index": i,
                "token_count": token_count,
                **(metadata or {})
            }

            result.append({
                "content": chunk_text,
                "token_count": token_count,
                "metadata": chunk_metadata
            })

        logger.info(f"文本分块完成: {len(result)} 个块")
        return result

    def _semantic_split(self, text: str) -> list[str]:
        """
        语义分块：按句子边界分割，保持语义完整性

        参数:
            text: 文本内容

        返回:
            list[str]: 分块列表
        """
        # 按句子分隔符分割
        sentences = self._split_by_separators(text)

        # 合并句子到块
        chunks = []
        current_chunk = []
        current_tokens = 0

        overlap_tokens = int(self.chunk_size * self.chunk_overlap)

        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)

            # 如果单个句子超过最大块大小，强制分割
            if sentence_tokens > self.max_chunk_size:
                # 保存当前块
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_tokens = 0

                # 强制分割长句子
                sub_chunks = self._force_split(sentence, self.chunk_size)
                chunks.extend(sub_chunks)
                continue

            # 如果添加这个句子会超过块大小
            if current_tokens + sentence_tokens > self.chunk_size:
                # 保存当前块
                if current_chunk:
                    chunks.append(" ".join(current_chunk))

                # 计算重叠部分
                overlap_sentences = []
                overlap_token_count = 0
                for sent in reversed(current_chunk):
                    sent_tokens = self.count_tokens(sent)
                    if overlap_token_count + sent_tokens <= overlap_tokens:
                        overlap_sentences.insert(0, sent)
                        overlap_token_count += sent_tokens
                    else:
                        break

                # 开始新块（包含重叠部分）
                current_chunk = overlap_sentences + [sentence]
                current_tokens = overlap_token_count + sentence_tokens
            else:
                # 添加到当前块
                current_chunk.append(sentence)
                current_tokens += sentence_tokens

        # 添加最后一个块
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def _split_by_separators(self, text: str) -> list[str]:
        """
        按分隔符分割文本

        参数:
            text: 文本内容

        返回:
            list[str]: 句子列表
        """
        # 使用正则表达式按多个分隔符分割
        pattern = "|".join(map(re.escape, self.sentence_separators))
        sentences = re.split(f"({pattern})", text)

        # 合并分隔符和句子
        result = []
        for i in range(0, len(sentences), 2):
            if i < len(sentences):
                sentence = sentences[i]
                if i + 1 < len(sentences):
                    sentence += sentences[i + 1]
                sentence = sentence.strip()
                if sentence:
                    result.append(sentence)

        return result

    def _force_split(self, text: str, max_tokens: int) -> list[str]:
        """
        强制分割超长文本

        参数:
            text: 文本内容
            max_tokens: 最大token数

        返回:
            list[str]: 分块列表
        """
        chunks = []
        tokens = self.encoding.encode(text)

        for i in range(0, len(tokens), max_tokens):
            chunk_tokens = tokens[i:i + max_tokens]
            chunk_text = self.encoding.decode(chunk_tokens)
            chunks.append(chunk_text)

        logger.debug(f"强制分割: {len(chunks)} 个块")
        return chunks

    def split_markdown(
        self,
        text: str,
        metadata: Optional[dict] = None
    ) -> list[dict]:
        """
        Markdown感知分块：保留Markdown结构

        参数:
            text: Markdown文本
            metadata: 元数据

        返回:
            list[dict]: 分块列表
        """
        # 按Markdown标题分割
        sections = self._split_by_markdown_headers(text)

        # 对每个section进行常规分块
        all_chunks = []
        for section_title, section_content in sections:
            section_metadata = {
                "section_title": section_title,
                **(metadata or {})
            }

            chunks = self.split_text(section_content, section_metadata)
            all_chunks.extend(chunks)

        logger.info(f"Markdown分块完成: {len(all_chunks)} 个块")
        return all_chunks

    def _split_by_markdown_headers(self, text: str) -> list[tuple[str, str]]:
        """
        按Markdown标题分割文本

        参数:
            text: Markdown文本

        返回:
            list[tuple[str, str]]: (标题, 内容) 列表
        """
        # 匹配Markdown标题（# 到 ######）
        header_pattern = r'^(#{1,6})\s+(.+)$'
        lines = text.split('\n')

        sections = []
        current_title = "Introduction"
        current_content = []

        for line in lines:
            match = re.match(header_pattern, line)
            if match:
                # 保存前一个section
                if current_content:
                    sections.append((current_title, '\n'.join(current_content)))

                # 开始新section
                current_title = match.group(2)
                current_content = []
            else:
                current_content.append(line)

        # 添加最后一个section
        if current_content:
            sections.append((current_title, '\n'.join(current_content)))

        return sections


# 全局TextSplitter实例
text_splitter = TextSplitter()
