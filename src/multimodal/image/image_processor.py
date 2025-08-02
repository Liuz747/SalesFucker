"""
图像处理管道模块

该模块提供图像文件的预处理和后处理功能。
支持格式转换、质量优化、尺寸调整和图像验证。

核心功能:
- 图像格式转换和优化
- 图像质量增强和噪声过滤
- 图像元数据提取
- 图像质量验证
"""

import asyncio
import aiofiles
import tempfile
import os
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import base64

from src.utils import (
    get_current_datetime,
    get_processing_time_ms,
    LoggerMixin,
    ErrorHandler,
    MultiModalConstants
)


class ImageProcessor(LoggerMixin):
    """
    图像处理器类
    
    提供图像文件的预处理和后处理功能。
    支持多种图像格式和质量优化。
    
    属性:
        temp_dir: 临时文件目录
        max_dimension: 最大图像尺寸
        supported_formats: 支持的图像格式
    """
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        初始化图像处理器
        
        Args:
            temp_dir: 临时文件目录
        """
        super().__init__()
        
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.max_dimension = 2048  # 最大边长
        self.supported_formats = MultiModalConstants.SUPPORTED_IMAGE_FORMATS
        
        # 检查PIL可用性
        self.pil_available = self._check_pil_availability()
        
        if self.pil_available:
            self.logger.info("图像处理器已初始化，PIL可用")
        else:
            self.logger.warning("图像处理器已初始化，PIL不可用，功能受限")
    
    def _check_pil_availability(self) -> bool:
        """检查PIL是否可用"""
        try:
            from PIL import Image, ImageEnhance, ImageFilter
            return True
        except ImportError:
            return False
    
    @ErrorHandler.with_error_handling()
    async def process_image_file(
        self, 
        file_path: str,
        optimize_quality: bool = True,
        resize_if_needed: bool = True
    ) -> Dict[str, Any]:
        """
        处理图像文件
        
        Args:
            file_path: 图像文件路径
            optimize_quality: 是否优化质量
            resize_if_needed: 是否调整尺寸
            
        Returns:
            处理结果和元数据
        """
        start_time = asyncio.get_event_loop().time()
        
        self.logger.info(f"开始处理图像文件: {file_path}")
        
        try:
            # 验证文件
            await self._validate_image_file(file_path)
            
            # 提取图像元数据
            metadata = await self._extract_image_metadata(file_path)
            
            # 处理后的文件路径
            processed_path = file_path
            
            # 尺寸调整
            if resize_if_needed and self.pil_available:
                processed_path = await self._resize_image_if_needed(file_path, metadata)
            
            # 质量优化
            if optimize_quality and self.pil_available:
                processed_path = await self._optimize_image_quality(processed_path, metadata)
            
            # 更新元数据
            if processed_path != file_path:
                final_metadata = await self._extract_image_metadata(processed_path)
                metadata.update(final_metadata)
            
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            result = {
                'original_path': file_path,
                'processed_path': processed_path,
                'metadata': metadata,
                'processing_time_ms': processing_time,
                'optimized': optimize_quality and self.pil_available,
                'resized': resize_if_needed and processed_path != file_path
            }
            
            self.logger.info(
                f"图像文件处理完成: {file_path}, "
                f"耗时: {processing_time:.1f}ms, "
                f"尺寸: {metadata.get('width', 0)}x{metadata.get('height', 0)}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"图像文件处理失败: {file_path}, 错误: {e}")
            raise
    
    async def _validate_image_file(self, file_path: str):
        """验证图像文件"""
        path = Path(file_path)
        
        # 检查文件是否存在
        if not path.exists():
            raise FileNotFoundError(f"图像文件不存在: {file_path}")
        
        # 检查文件大小
        file_size = path.stat().st_size
        if file_size > MultiModalConstants.MAX_IMAGE_SIZE:
            raise ValueError(f"图像文件过大: {file_size} bytes")
        
        if file_size == 0:
            raise ValueError("图像文件为空")
        
        # 检查文件格式
        extension = path.suffix.lower().lstrip('.')
        if extension not in self.supported_formats:
            raise ValueError(f"不支持的图像格式: {extension}")
    
    async def _extract_image_metadata(self, file_path: str) -> Dict[str, Any]:
        """提取图像元数据"""
        try:
            if self.pil_available:
                return await self._extract_metadata_with_pil(file_path)
            else:
                return await self._extract_metadata_basic(file_path)
        except Exception as e:
            self.logger.warning(f"元数据提取失败: {e}")
            return await self._extract_metadata_basic(file_path)
    
    async def _extract_metadata_with_pil(self, file_path: str) -> Dict[str, Any]:
        """使用PIL提取图像元数据"""
        try:
            from PIL import Image
            
            def extract_sync():
                with Image.open(file_path) as img:
                    # 获取基本信息
                    width, height = img.size
                    format_name = img.format
                    mode = img.mode
                    
                    # 计算通道数
                    if mode == 'RGB':
                        channels = 3
                    elif mode == 'RGBA':
                        channels = 4
                    elif mode == 'L':
                        channels = 1
                    elif mode == 'P':
                        channels = 1
                    else:
                        channels = len(mode)
                    
                    # 获取EXIF信息（如果有）
                    exif_data = {}
                    if hasattr(img, '_getexif') and img._getexif() is not None:
                        exif_info = img._getexif()
                        if exif_info:
                            exif_data = {str(k): str(v) for k, v in exif_info.items()}
                    
                    return {
                        'width': width,
                        'height': height,
                        'channels': channels,
                        'format': format_name.lower() if format_name else 'unknown',
                        'mode': mode,
                        'size_bytes': Path(file_path).stat().st_size,
                        'aspect_ratio': width / height if height > 0 else 0,
                        'total_pixels': width * height,
                        'exif': exif_data
                    }
            
            # 在线程池中执行同步操作
            loop = asyncio.get_event_loop()
            metadata = await loop.run_in_executor(None, extract_sync)
            return metadata
            
        except Exception as e:
            self.logger.warning(f"PIL元数据提取失败: {e}")
            raise
    
    async def _extract_metadata_basic(self, file_path: str) -> Dict[str, Any]:
        """基础元数据提取"""
        path = Path(file_path)
        file_size = path.stat().st_size
        
        return {
            'size_bytes': file_size,
            'format': path.suffix.lower().lstrip('.'),
            'width': 0,  # 无法获取，设为0
            'height': 0,
            'channels': 0,
            'mode': 'unknown',
            'aspect_ratio': 0,
            'total_pixels': 0
        }
    
    async def _resize_image_if_needed(
        self, 
        file_path: str, 
        metadata: Dict[str, Any]
    ) -> str:
        """如果需要，调整图像尺寸"""
        try:
            width = metadata.get('width', 0)
            height = metadata.get('height', 0)
            
            # 检查是否需要调整尺寸
            if width <= self.max_dimension and height <= self.max_dimension:
                return file_path
            
            from PIL import Image
            
            def resize_sync():
                with Image.open(file_path) as img:
                    # 计算新尺寸
                    if width > height:
                        new_width = self.max_dimension
                        new_height = int(height * self.max_dimension / width)
                    else:
                        new_height = self.max_dimension
                        new_width = int(width * self.max_dimension / height)
                    
                    # 调整尺寸
                    resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # 生成输出文件路径
                    temp_file = self._generate_temp_filename(file_path, 'resized.jpg')
                    
                    # 保存调整后的图像
                    resized_img.save(temp_file, 'JPEG', quality=95)
                    
                    return temp_file
            
            # 在线程池中执行同步操作
            loop = asyncio.get_event_loop()
            temp_file = await loop.run_in_executor(None, resize_sync)
            
            self.logger.info(f"图像尺寸已调整: {file_path} -> {temp_file}")
            return temp_file
            
        except Exception as e:
            self.logger.error(f"图像尺寸调整失败: {e}")
            return file_path  # 返回原文件
    
    async def _optimize_image_quality(
        self, 
        file_path: str, 
        metadata: Dict[str, Any]
    ) -> str:
        """优化图像质量"""
        try:
            from PIL import Image, ImageEnhance, ImageFilter
            
            def optimize_sync():
                with Image.open(file_path) as img:
                    # 转换为RGB模式（如果需要）
                    if img.mode in ('RGBA', 'P'):
                        # 创建白色背景
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # 图像增强
                    enhanced_img = img
                    
                    # 锐化
                    enhancer = ImageEnhance.Sharpness(enhanced_img)
                    enhanced_img = enhancer.enhance(1.1)  # 轻微锐化
                    
                    # 对比度增强
                    enhancer = ImageEnhance.Contrast(enhanced_img)
                    enhanced_img = enhancer.enhance(1.05)  # 轻微增强对比度
                    
                    # 颜色饱和度
                    enhancer = ImageEnhance.Color(enhanced_img)
                    enhanced_img = enhancer.enhance(1.02)  # 轻微增强饱和度
                    
                    # 降噪（轻微模糊后再锐化）
                    enhanced_img = enhanced_img.filter(ImageFilter.SMOOTH_MORE)
                    enhancer = ImageEnhance.Sharpness(enhanced_img)
                    enhanced_img = enhancer.enhance(1.2)
                    
                    # 生成输出文件路径
                    temp_file = self._generate_temp_filename(file_path, 'optimized.jpg')
                    
                    # 保存优化后的图像
                    enhanced_img.save(temp_file, 'JPEG', quality=95, optimize=True)
                    
                    return temp_file
            
            # 在线程池中执行同步操作
            loop = asyncio.get_event_loop()
            temp_file = await loop.run_in_executor(None, optimize_sync)
            
            self.logger.info(f"图像质量已优化: {file_path} -> {temp_file}")
            return temp_file
            
        except Exception as e:
            self.logger.error(f"图像质量优化失败: {e}")
            return file_path  # 返回原文件
    
    def _generate_temp_filename(self, original_path: str, suffix: str) -> str:
        """生成临时文件名"""
        original_name = Path(original_path).stem
        temp_name = f"{original_name}_{suffix}"
        return os.path.join(self.temp_dir, temp_name)
    
    @ErrorHandler.with_error_handling()
    async def validate_image_quality(self, file_path: str) -> Dict[str, Any]:
        """验证图像质量"""
        try:
            metadata = await self._extract_image_metadata(file_path)
            
            quality_scores = {}
            recommendations = []
            
            # 检查尺寸
            width = metadata.get('width', 0)
            height = metadata.get('height', 0)
            
            if width < MultiModalConstants.MIN_IMAGE_WIDTH or height < MultiModalConstants.MIN_IMAGE_HEIGHT:
                quality_scores['resolution'] = 0.0
                recommendations.append("图像分辨率过低，可能影响分析质量")
            elif width >= 1024 and height >= 768:
                quality_scores['resolution'] = 1.0
            elif width >= 640 and height >= 480:
                quality_scores['resolution'] = 0.8
            else:
                quality_scores['resolution'] = 0.5
                recommendations.append("图像分辨率偏低，建议使用更高分辨率的图像")
            
            # 检查宽高比
            aspect_ratio = metadata.get('aspect_ratio', 0)
            if 0.5 <= aspect_ratio <= 2.0:  # 合理的宽高比范围
                quality_scores['aspect_ratio'] = 1.0
            else:
                quality_scores['aspect_ratio'] = 0.7
                recommendations.append("图像宽高比异常，可能影响分析效果")
            
            # 检查文件大小
            file_size = metadata.get('size_bytes', 0)
            if file_size > 5 * 1024 * 1024:  # 5MB
                quality_scores['file_size'] = 1.0
            elif file_size > 1 * 1024 * 1024:  # 1MB
                quality_scores['file_size'] = 0.9
            elif file_size > 100 * 1024:  # 100KB
                quality_scores['file_size'] = 0.7
            else:
                quality_scores['file_size'] = 0.5
                recommendations.append("文件过小，可能是压缩过度或质量不佳")
            
            # 检查颜色模式
            mode = metadata.get('mode', '')
            if mode in ('RGB', 'RGBA'):
                quality_scores['color_mode'] = 1.0
            elif mode in ('L', 'P'):
                quality_scores['color_mode'] = 0.7
                recommendations.append("图像为灰度或调色板模式，可能影响颜色分析")
            else:
                quality_scores['color_mode'] = 0.5
                recommendations.append("图像颜色模式不常见，可能影响分析效果")
            
            # 计算总体质量分数
            overall_score = sum(quality_scores.values()) / len(quality_scores)
            
            quality_level = "excellent"
            if overall_score < 0.5:
                quality_level = "poor"
            elif overall_score < 0.7:
                quality_level = "fair"
            elif overall_score < 0.9:
                quality_level = "good"
            
            return {
                'overall_score': overall_score,
                'quality_level': quality_level,
                'quality_scores': quality_scores,
                'recommendations': recommendations,
                'metadata': metadata,
                'is_acceptable': overall_score >= 0.5
            }
            
        except Exception as e:
            self.logger.error(f"图像质量验证失败: {e}")
            return {
                'overall_score': 0.0,
                'quality_level': "unknown",
                'quality_scores': {},
                'recommendations': ["无法验证图像质量"],
                'metadata': {},
                'is_acceptable': False,
                'error': str(e)
            }
    
    @ErrorHandler.with_error_handling()
    async def encode_image_to_base64(self, file_path: str) -> str:
        """将图像编码为base64字符串"""
        try:
            async with aiofiles.open(file_path, "rb") as image_file:
                image_data = await image_file.read()
                return base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            self.logger.error(f"图像base64编码失败: {file_path}, 错误: {e}")
            raise
    
    async def cleanup_temp_files(self, file_paths: list):
        """清理临时文件"""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path) and file_path.startswith(self.temp_dir):
                    os.remove(file_path)
                    self.logger.debug(f"已删除临时文件: {file_path}")
            except Exception as e:
                self.logger.warning(f"清理临时文件失败: {file_path}, 错误: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            'status': 'healthy',
            'service': 'image_processor',
            'pil_available': self.pil_available,
            'supported_formats': self.supported_formats,
            'max_dimension': self.max_dimension,
            'temp_dir': self.temp_dir,
            'timestamp': get_current_datetime()
        }