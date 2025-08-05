"""
音频处理管道模块

该模块提供音频文件的预处理和后处理功能。
支持格式转换、质量增强、噪声过滤和音频验证。

核心功能:
- 音频格式转换和优化
- 噪声过滤和质量增强
- 音频元数据提取
- 音频质量验证
"""

import asyncio
import aiofiles
import tempfile
import os
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import subprocess
import json

from src.utils import (
    get_current_datetime,
    get_processing_time_ms,
    LoggerMixin,
    with_error_handling,
    MultiModalConstants
)


class AudioProcessor(LoggerMixin):
    """
    音频处理器类
    
    提供音频文件的预处理和后处理功能。
    支持多种音频格式和质量优化。
    
    属性:
        temp_dir: 临时文件目录
        ffmpeg_available: FFmpeg是否可用
        supported_formats: 支持的音频格式
    """
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        初始化音频处理器
        
        Args:
            temp_dir: 临时文件目录
        """
        super().__init__()
        
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.supported_formats = MultiModalConstants.SUPPORTED_AUDIO_FORMATS
        
        # 检查FFmpeg可用性
        self.ffmpeg_available = self._check_ffmpeg_availability()
        
        if self.ffmpeg_available:
            self.logger.info("音频处理器已初始化，FFmpeg可用")
        else:
            self.logger.warning("音频处理器已初始化，FFmpeg不可用，功能受限")
    
    def _check_ffmpeg_availability(self) -> bool:
        """检查FFmpeg是否可用"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False
    
    @with_error_handling()
    async def process_audio_file(
        self, 
        file_path: str,
        enhance_quality: bool = True,
        normalize_format: bool = True
    ) -> Dict[str, Any]:
        """
        处理音频文件
        
        Args:
            file_path: 音频文件路径
            enhance_quality: 是否增强质量
            normalize_format: 是否标准化格式
            
        Returns:
            处理结果和元数据
        """
        start_time = asyncio.get_event_loop().time()
        
        self.logger.info(f"开始处理音频文件: {file_path}")
        
        try:
            # 验证文件
            await self._validate_audio_file(file_path)
            
            # 提取音频元数据
            metadata = await self._extract_audio_metadata(file_path)
            
            # 处理后的文件路径
            processed_path = file_path
            
            # 格式标准化
            if normalize_format and self.ffmpeg_available:
                processed_path = await self._normalize_audio_format(file_path, metadata)
            
            # 质量增强
            if enhance_quality and self.ffmpeg_available:
                processed_path = await self._enhance_audio_quality(processed_path, metadata)
            
            # 更新元数据
            if processed_path != file_path:
                final_metadata = await self._extract_audio_metadata(processed_path)
                metadata.update(final_metadata)
            
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            result = {
                'original_path': file_path,
                'processed_path': processed_path,
                'metadata': metadata,
                'processing_time_ms': processing_time,
                'enhanced': enhance_quality and self.ffmpeg_available,
                'normalized': normalize_format and self.ffmpeg_available
            }
            
            self.logger.info(
                f"音频文件处理完成: {file_path}, "
                f"耗时: {processing_time:.1f}ms, "
                f"时长: {metadata.get('duration', 0):.1f}秒"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"音频文件处理失败: {file_path}, 错误: {e}")
            raise
    
    async def _validate_audio_file(self, file_path: str):
        """验证音频文件"""
        path = Path(file_path)
        
        # 检查文件是否存在
        if not path.exists():
            raise FileNotFoundError(f"音频文件不存在: {file_path}")
        
        # 检查文件大小
        file_size = path.stat().st_size
        if file_size > MultiModalConstants.MAX_AUDIO_SIZE:
            raise ValueError(f"音频文件过大: {file_size} bytes")
        
        if file_size == 0:
            raise ValueError("音频文件为空")
        
        # 检查文件格式
        extension = path.suffix.lower().lstrip('.')
        if extension not in self.supported_formats:
            raise ValueError(f"不支持的音频格式: {extension}")
    
    async def _extract_audio_metadata(self, file_path: str) -> Dict[str, Any]:
        """提取音频元数据"""
        try:
            if self.ffmpeg_available:
                return await self._extract_metadata_with_ffmpeg(file_path)
            else:
                return await self._extract_metadata_basic(file_path)
        except Exception as e:
            self.logger.warning(f"元数据提取失败: {e}")
            return await self._extract_metadata_basic(file_path)
    
    async def _extract_metadata_with_ffmpeg(self, file_path: str) -> Dict[str, Any]:
        """使用FFmpeg提取音频元数据"""
        try:
            # 使用ffprobe提取详细信息
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"ffprobe失败: {stderr.decode()}")
            
            probe_data = json.loads(stdout.decode())
            
            # 提取音频流信息
            audio_stream = None
            for stream in probe_data.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    audio_stream = stream
                    break
            
            if not audio_stream:
                raise Exception("未找到音频流")
            
            format_info = probe_data.get('format', {})
            
            return {
                'duration': float(format_info.get('duration', 0)),
                'bit_rate': int(format_info.get('bit_rate', 0)),
                'sample_rate': int(audio_stream.get('sample_rate', 0)),
                'channels': int(audio_stream.get('channels', 0)),
                'codec': audio_stream.get('codec_name', ''),
                'format': format_info.get('format_name', ''),
                'size_bytes': int(format_info.get('size', 0))
            }
            
        except Exception as e:
            self.logger.warning(f"FFmpeg元数据提取失败: {e}")
            raise
    
    async def _extract_metadata_basic(self, file_path: str) -> Dict[str, Any]:
        """基础元数据提取"""
        path = Path(file_path)
        file_size = path.stat().st_size
        
        return {
            'size_bytes': file_size,
            'format': path.suffix.lower().lstrip('.'),
            'duration': 0,  # 无法获取，设为0
            'sample_rate': 0,
            'channels': 0,
            'bit_rate': 0,
            'codec': 'unknown'
        }
    
    async def _normalize_audio_format(
        self, 
        file_path: str, 
        metadata: Dict[str, Any]
    ) -> str:
        """标准化音频格式"""
        try:
            # 如果已经是理想格式，跳过转换
            if (metadata.get('codec') == 'pcm_s16le' and 
                metadata.get('sample_rate') == 16000 and 
                metadata.get('channels') == 1):
                return file_path
            
            # 生成输出文件路径
            temp_file = self._generate_temp_filename(file_path, 'normalized.wav')
            
            # FFmpeg转换命令
            cmd = [
                'ffmpeg',
                '-i', file_path,
                '-ar', '16000',  # 采样率16kHz
                '-ac', '1',      # 单声道
                '-c:a', 'pcm_s16le',  # PCM 16位编码
                '-y',            # 覆盖输出文件
                temp_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"音频格式转换失败: {stderr.decode()}")
            
            self.logger.info(f"音频格式已标准化: {file_path} -> {temp_file}")
            return temp_file
            
        except Exception as e:
            self.logger.error(f"音频格式标准化失败: {e}")
            return file_path  # 返回原文件
    
    async def _enhance_audio_quality(
        self, 
        file_path: str, 
        metadata: Dict[str, Any]
    ) -> str:
        """增强音频质量"""
        try:
            # 生成输出文件路径
            temp_file = self._generate_temp_filename(file_path, 'enhanced.wav')
            
            # 构建音频过滤器
            filters = []
            
            # 噪声抑制
            filters.append('anlmdn=s=0.002')
            
            # 音量标准化
            filters.append('dynaudnorm=p=0.95:m=10')
            
            # 高通滤波器去除低频噪声
            filters.append('highpass=f=80')
            
            # 低通滤波器去除高频噪声
            filters.append('lowpass=f=8000')
            
            # FFmpeg增强命令
            cmd = [
                'ffmpeg',
                '-i', file_path,
                '-af', ','.join(filters),
                '-y',
                temp_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                self.logger.warning(f"音频质量增强失败: {stderr.decode()}")
                return file_path  # 返回原文件
            
            self.logger.info(f"音频质量已增强: {file_path} -> {temp_file}")
            return temp_file
            
        except Exception as e:
            self.logger.error(f"音频质量增强失败: {e}")
            return file_path  # 返回原文件
    
    def _generate_temp_filename(self, original_path: str, suffix: str) -> str:
        """生成临时文件名"""
        original_name = Path(original_path).stem
        temp_name = f"{original_name}_{suffix}"
        return os.path.join(self.temp_dir, temp_name)
    
    @with_error_handling()
    async def validate_audio_quality(self, file_path: str) -> Dict[str, Any]:
        """验证音频质量"""
        try:
            metadata = await self._extract_audio_metadata(file_path)
            
            quality_scores = {}
            recommendations = []
            
            # 检查时长
            duration = metadata.get('duration', 0)
            if duration < MultiModalConstants.MIN_AUDIO_DURATION:
                quality_scores['duration'] = 0.0
                recommendations.append("音频时长过短，可能影响识别准确性")
            elif duration > MultiModalConstants.MAX_AUDIO_DURATION:
                quality_scores['duration'] = 0.5
                recommendations.append("音频时长过长，建议分段处理")
            else:
                quality_scores['duration'] = 1.0
            
            # 检查采样率
            sample_rate = metadata.get('sample_rate', 0)
            if sample_rate >= 16000:
                quality_scores['sample_rate'] = 1.0
            elif sample_rate >= 8000:
                quality_scores['sample_rate'] = 0.7
                recommendations.append("采样率偏低，建议提高到16kHz")
            else:
                quality_scores['sample_rate'] = 0.3
                recommendations.append("采样率过低，可能严重影响识别质量")
            
            # 检查比特率
            bit_rate = metadata.get('bit_rate', 0)
            if bit_rate >= 128000:
                quality_scores['bit_rate'] = 1.0
            elif bit_rate >= 64000:
                quality_scores['bit_rate'] = 0.8
            else:
                quality_scores['bit_rate'] = 0.5
                recommendations.append("比特率偏低，可能影响音质")
            
            # 计算总体质量分数
            overall_score = sum(quality_scores.values()) / len(quality_scores)
            
            quality_level = "excellent"
            if overall_score < 0.5:
                quality_level = "poor"
            elif overall_score < 0.8:
                quality_level = "fair"
            elif overall_score < 0.95:
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
            self.logger.error(f"音频质量验证失败: {e}")
            return {
                'overall_score': 0.0,
                'quality_level': "unknown",
                'quality_scores': {},
                'recommendations': ["无法验证音频质量"],
                'metadata': {},
                'is_acceptable': False,
                'error': str(e)
            }
    
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
            'service': 'audio_processor',
            'ffmpeg_available': self.ffmpeg_available,
            'supported_formats': self.supported_formats,
            'temp_dir': self.temp_dir,
            'timestamp': get_current_datetime()
        }