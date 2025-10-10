"""
URL附件下载服务模块

该模块提供从URL下载附件文件的功能，支持图片、音频等多种文件类型。
包含URL验证、文件下载、临时存储和清理功能。

核心功能:
- URL格式验证和安全检查
- 多种文件类型下载（图片、音频、文档）
- 临时文件管理和自动清理
- 下载超时和重试机制
- 文件大小和类型验证
"""

import asyncio
import aiohttp
import aiofiles
import tempfile
import os
import mimetypes
from typing import Dict, Any, List, Optional
from pathlib import Path
from urllib.parse import urlparse, unquote
import hashlib

from utils import (
    LoggerMixin,
    MultiModalConstants,
    get_current_datetime
)


class URLDownloader(LoggerMixin):
    """
    URL附件下载器

    负责从URL下载附件文件到本地临时存储。
    支持多种文件类型和智能格式检测。

    属性:
        temp_dir: 临时文件存储目录
        timeout: 下载超时时间（秒）
        max_retries: 最大重试次数
        session: aiohttp客户端会话
    """

    def __init__(
        self,
        temp_dir: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        初始化URL下载器

        Args:
            temp_dir: 临时文件目录，默认使用系统临时目录
            timeout: 下载超时时间（秒）
            max_retries: 最大重试次数
        """
        super().__init__()

        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.timeout = timeout
        self.max_retries = max_retries
        self.session: Optional[aiohttp.ClientSession] = None

        # 支持的MIME类型映射
        self.mime_type_map = {
            'image': MultiModalConstants.SUPPORTED_IMAGE_FORMATS,
            'audio': MultiModalConstants.SUPPORTED_AUDIO_FORMATS
        }

        self.logger.info(f"URL下载器已初始化，临时目录: {self.temp_dir}")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self.session:
            await self.session.close()

    async def download_attachments(
        self,
        attachment_inputs: List[Dict[str, str]],
        tenant_id: str
    ) -> List[dict]:
        """
        下载所有附件URL到本地临时存储

        Args:
            attachment_inputs: 附件输入列表 [{"url": "...", "type": "image"}, ...]
            tenant_id: 租户ID（用于隔离存储）

        Returns:
            List[dict]: 下载结果列表，包含本地路径和元数据
        """
        self.logger.info(f"开始下载 {len(attachment_inputs)} 个附件")

        # 创建会话（如果不存在）
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )

        try:
            # 并发下载所有附件
            tasks = [
                self._download_single(attachment, tenant_id)
                for attachment in attachment_inputs
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            downloaded = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(
                        f"附件下载失败 {attachment_inputs[i]['url']}: {result}"
                    )
                    # 添加错误结果
                    downloaded.append({
                        "url": attachment_inputs[i]['url'],
                        "type": attachment_inputs[i].get('type', 'unknown'),
                        "error": str(result),
                        "status": "failed"
                    })
                else:
                    downloaded.append(result)

            success_count = len([r for r in downloaded if r.get('status') != 'failed'])
            self.logger.info(
                f"附件下载完成: 成功 {success_count}/{len(attachment_inputs)}"
            )

            return downloaded

        finally:
            # 关闭会话
            if self.session:
                await self.session.close()
                self.session = None

    async def _download_single(
        self,
        attachment: Dict[str, str],
        tenant_id: str
    ) -> dict:
        """
        下载单个附件

        Args:
            attachment: 附件信息 {"url": "...", "type": "image"}
            tenant_id: 租户ID

        Returns:
            dict: 下载结果元数据
        """
        url = attachment['url']
        attachment_type = attachment.get('type', 'unknown')

        self.logger.debug(f"开始下载附件: {url}")

        # 验证URL
        if not self._validate_url(url):
            raise ValueError(f"无效的URL: {url}")

        # 下载文件
        for attempt in range(self.max_retries):
            try:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        raise Exception(
                            f"下载失败，HTTP状态码: {response.status}"
                        )

                    # 检测内容类型
                    content_type = response.headers.get('Content-Type', '')
                    detected_type = self._detect_attachment_type(
                        content_type,
                        url,
                        attachment_type
                    )

                    # 检查文件大小
                    content_length = response.headers.get('Content-Length')
                    if content_length:
                        file_size = int(content_length)
                        self._validate_file_size(file_size, detected_type)

                    # 读取文件内容
                    file_content = await response.read()

                    # 生成本地文件路径
                    local_path = self._generate_local_path(
                        url,
                        tenant_id,
                        detected_type,
                        content_type
                    )

                    # 保存到本地
                    async with aiofiles.open(local_path, 'wb') as f:
                        await f.write(file_content)

                    self.logger.info(f"附件下载成功: {url} -> {local_path}")

                    return {
                        "url": url,
                        "type": detected_type,
                        "local_path": local_path,
                        "content_type": content_type,
                        "file_size": len(file_content),
                        "filename": Path(local_path).name,
                        "status": "success"
                    }

            except Exception as e:
                self.logger.warning(
                    f"下载失败 (尝试 {attempt + 1}/{self.max_retries}): {url}, 错误: {e}"
                )
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(1 * (attempt + 1))  # 指数退避

    def _validate_url(self, url: str) -> bool:
        """
        验证URL格式和安全性

        Args:
            url: 待验证的URL

        Returns:
            bool: 是否有效
        """
        try:
            parsed = urlparse(url)

            # 检查协议
            if parsed.scheme not in ['http', 'https']:
                self.logger.warning(f"不支持的URL协议: {parsed.scheme}")
                return False

            # 检查主机名
            if not parsed.netloc:
                self.logger.warning("URL缺少主机名")
                return False

            # 安全检查：阻止本地文件访问
            if parsed.netloc.lower() in ['localhost', '127.0.0.1', '0.0.0.0']:
                self.logger.warning(f"禁止访问本地URL: {url}")
                return False

            return True

        except Exception as e:
            self.logger.error(f"URL验证失败: {url}, 错误: {e}")
            return False

    def _detect_attachment_type(
        self,
        content_type: str,
        url: str,
        hint_type: str
    ) -> str:
        """
        检测附件类型

        优先级: Content-Type > URL扩展名 > 用户提示

        Args:
            content_type: HTTP Content-Type头
            url: 文件URL
            hint_type: 用户提供的类型提示

        Returns:
            str: 检测到的类型（image/audio/file）
        """
        # 1. 从Content-Type检测
        if content_type:
            if content_type.startswith('image/'):
                return 'image'
            elif content_type.startswith('audio/'):
                return 'audio'

        # 2. 从URL扩展名检测
        parsed_url = urlparse(url)
        path = unquote(parsed_url.path)
        extension = Path(path).suffix.lower().lstrip('.')

        if extension in MultiModalConstants.SUPPORTED_IMAGE_FORMATS:
            return 'image'
        elif extension in MultiModalConstants.SUPPORTED_AUDIO_FORMATS:
            return 'audio'

        # 3. 使用用户提示
        if hint_type in ['image', 'audio']:
            return hint_type

        # 4. 默认为文件
        return 'file'

    def _validate_file_size(self, file_size: int, file_type: str):
        """
        验证文件大小

        Args:
            file_size: 文件大小（字节）
            file_type: 文件类型

        Raises:
            ValueError: 文件大小超过限制
        """
        max_size = None

        if file_type == 'image':
            max_size = MultiModalConstants.MAX_IMAGE_SIZE
        elif file_type == 'audio':
            max_size = MultiModalConstants.MAX_AUDIO_SIZE

        if max_size and file_size > max_size:
            raise ValueError(
                f"{file_type}文件大小 {file_size} bytes 超过限制 {max_size} bytes"
            )

    def _generate_local_path(
        self,
        url: str,
        tenant_id: str,
        file_type: str,
        content_type: str
    ) -> str:
        """
        生成本地文件路径

        使用URL哈希值确保唯一性，使用租户ID进行隔离

        Args:
            url: 原始URL
            tenant_id: 租户ID
            file_type: 文件类型
            content_type: MIME类型

        Returns:
            str: 本地文件路径
        """
        # 生成URL哈希值作为文件名
        url_hash = hashlib.md5(url.encode()).hexdigest()[:16]

        # 获取扩展名
        extension = self._get_extension_from_content_type(content_type)
        if not extension:
            # 尝试从URL获取
            parsed_url = urlparse(url)
            url_extension = Path(parsed_url.path).suffix.lower().lstrip('.')
            extension = url_extension if url_extension else 'bin'

        # 创建租户目录
        tenant_dir = os.path.join(self.temp_dir, f"tenant_{tenant_id}")
        os.makedirs(tenant_dir, exist_ok=True)

        # 生成完整路径
        filename = f"{file_type}_{url_hash}.{extension}"
        local_path = os.path.join(tenant_dir, filename)

        return local_path

    def _get_extension_from_content_type(self, content_type: str) -> Optional[str]:
        """从MIME类型获取文件扩展名"""
        if not content_type:
            return None

        # 移除参数部分（如 charset）
        mime_type = content_type.split(';')[0].strip()

        # 使用mimetypes模块反查扩展名
        extension = mimetypes.guess_extension(mime_type)
        if extension:
            return extension.lstrip('.')

        # 手动映射常见类型
        mime_map = {
            'image/jpeg': 'jpg',
            'image/png': 'png',
            'image/gif': 'gif',
            'image/webp': 'webp',
            'audio/mpeg': 'mp3',
            'audio/wav': 'wav',
            'audio/ogg': 'ogg',
            'audio/x-m4a': 'm4a'
        }

        return mime_map.get(mime_type)

    async def cleanup_files(self, file_paths: List[str]):
        """
        清理临时文件

        Args:
            file_paths: 文件路径列表
        """
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.logger.debug(f"已删除临时文件: {file_path}")
            except Exception as e:
                self.logger.warning(f"清理临时文件失败: {file_path}, 错误: {e}")

    async def cleanup_tenant_files(self, tenant_id: str):
        """
        清理租户的所有临时文件

        Args:
            tenant_id: 租户ID
        """
        tenant_dir = os.path.join(self.temp_dir, f"tenant_{tenant_id}")

        if os.path.exists(tenant_dir):
            try:
                import shutil
                shutil.rmtree(tenant_dir)
                self.logger.info(f"已清理租户临时目录: {tenant_dir}")
            except Exception as e:
                self.logger.error(f"清理租户目录失败: {tenant_dir}, 错误: {e}")
