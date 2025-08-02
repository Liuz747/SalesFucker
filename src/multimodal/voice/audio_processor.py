"""
音频预处理器

该模块提供音频文件的预处理功能，包括格式转换、质量优化和元数据提取。
为语音识别提供最佳的音频输入质量。

核心功能:
- 音频格式转换和标准化
- 噪音过滤和质量增强
- 音频元数据提取
- 文件验证和安全检查
"""

import asyncio
import aiofiles
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import tempfile
import shutil

try:
    import librosa
    import soundfile as sf
    import numpy as np
    AUDIO_LIBS_AVAILABLE = True
except ImportError:
    AUDIO_LIBS_AVAILABLE = False

from src.utils import (
    get_current_datetime,
    get_processing_time_ms,
    LoggerMixin,
    ErrorHandler,
    MultiModalConstants,
    MessageConstants
)


class AudioProcessor(LoggerMixin):
    """
    音频预处理器类
    
    提供音频文件的预处理、格式转换和质量优化功能。
    支持多种音频格式的处理和标准化。
    
    属性:
        temp_dir: 临时文件目录
        target_sample_rate: 目标采样率
        target_channels: 目标声道数
        supported_formats: 支持的音频格式
    """
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        初始化音频处理器
        
        Args:
            temp_dir: 临时文件目录，None使用系统默认
        """
        super().__init__()
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.target_sample_rate = 16000  # Whisper推荐采样率
        self.target_channels = 1  # 单声道
        self.supported_formats = MessageConstants.SUPPORTED_AUDIO_FORMATS
        
        if not AUDIO_LIBS_AVAILABLE:
            self.logger.warning("音频处理库未安装，仅支持基础功能")
        
        self.logger.info(f"音频处理器已初始化 - 临时目录: {self.temp_dir}")
    
    @ErrorHandler.with_error_handling()
    async def process_audio_file(self, input_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        处理音频文件
        
        Args:
            input_path: 输入音频文件路径
            output_path: 输出文件路径，None自动生成
            
        Returns:
            处理结果，包含输出路径和音频信息
        """
        start_time = get_current_datetime()
        self.logger.info(f"开始处理音频文件: {input_path}")
        
        try:
            # 验证输入文件
            input_info = await self.validate_audio_file(input_path)
            if not input_info['is_valid']:
                raise ValueError(f"无效的音频文件: {input_info['error']}")
            
            # 生成输出路径
            if not output_path:
                output_path = await self._generate_temp_path(input_path, 'wav')
            
            # 执行音频处理
            if AUDIO_LIBS_AVAILABLE:
                processed_info = await self._process_with_librosa(input_path, output_path)
            else:
                # 简单文件复制（如果格式已支持）
                processed_info = await self._simple_copy(input_path, output_path)
            
            processing_time = get_processing_time_ms(start_time)
            
            result = {
                'input_path': input_path,
                'output_path': output_path,
                'original_info': input_info,
                'processed_info': processed_info,
                'processing_time_ms': processing_time,
                'success': True
            }
            
            self.logger.info(
                f"音频处理完成: {input_path} -> {output_path}, "
                f"耗时: {processing_time}ms"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"音频处理失败: {input_path}, 错误: {e}")
            raise
    
    @ErrorHandler.with_error_handling()
    async def validate_audio_file(self, file_path: str) -> Dict[str, Any]:
        """
        验证音频文件
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            验证结果信息
        """
        result = {
            'is_valid': False,
            'file_path': file_path,
            'error': None,
            'file_size': 0,
            'format': None,
            'duration': None,
            'sample_rate': None,
            'channels': None
        }
        
        try:
            # 检查文件存在
            path = Path(file_path)
            if not path.exists():
                result['error'] = "文件不存在"
                return result
            
            # 检查文件大小
            file_size = path.stat().st_size
            result['file_size'] = file_size
            
            if file_size == 0:
                result['error'] = "文件为空"
                return result
            
            if file_size > MultiModalConstants.MAX_AUDIO_SIZE:
                result['error'] = f"文件过大: {file_size} > {MultiModalConstants.MAX_AUDIO_SIZE}"
                return result
            
            # 检查文件格式
            file_extension = path.suffix.lower().lstrip('.')
            if file_extension not in self.supported_formats:
                result['error'] = f"不支持的格式: {file_extension}"
                return result
            
            result['format'] = file_extension
            
            # 提取音频信息（如果可能）
            if AUDIO_LIBS_AVAILABLE:
                try:
                    audio_info = await self._extract_audio_info(file_path)
                    result.update(audio_info)
                    
                    # 验证音频时长
                    if result['duration']:
                        if result['duration'] < MultiModalConstants.MIN_AUDIO_DURATION:
                            result['error'] = f"音频过短: {result['duration']}s < {MultiModalConstants.MIN_AUDIO_DURATION}s"
                            return result
                        
                        if result['duration'] > MultiModalConstants.MAX_AUDIO_DURATION:
                            result['error'] = f"音频过长: {result['duration']}s > {MultiModalConstants.MAX_AUDIO_DURATION}s"
                            return result
                    
                except Exception as e:
                    self.logger.warning(f"无法提取音频信息: {e}")
            
            result['is_valid'] = True
            return result
            
        except Exception as e:
            result['error'] = str(e)
            return result
    
    async def _extract_audio_info(self, file_path: str) -> Dict[str, Any]:
        """
        提取音频文件信息
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            音频信息字典
        """
        try:
            # 使用librosa加载音频信息（不加载数据）
            info = sf.info(file_path)
            
            return {
                'duration': info.duration,
                'sample_rate': info.samplerate,
                'channels': info.channels,
                'frames': info.frames,
                'format': info.format,
                'subtype': info.subtype
            }
        except Exception as e:
            self.logger.warning(f"提取音频信息失败: {e}")
            return {
                'duration': None,
                'sample_rate': None,
                'channels': None
            }
    
    async def _process_with_librosa(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """
        使用librosa处理音频
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            
        Returns:
            处理后的音频信息
        """
        try:
            # 加载音频数据
            audio_data, original_sr = librosa.load(input_path, sr=None, mono=False)
            
            # 转换为单声道
            if audio_data.ndim > 1:
                audio_data = librosa.to_mono(audio_data)
            
            # 重采样到目标采样率
            if original_sr != self.target_sample_rate:
                audio_data = librosa.resample(
                    audio_data, 
                    orig_sr=original_sr, 
                    target_sr=self.target_sample_rate
                )
            
            # 音频增强（可选）
            audio_data = self._enhance_audio(audio_data)
            
            # 保存处理后的音频
            sf.write(output_path, audio_data, self.target_sample_rate)
            
            return {
                'duration': len(audio_data) / self.target_sample_rate,
                'sample_rate': self.target_sample_rate,
                'channels': 1,
                'frames': len(audio_data),
                'enhanced': True
            }
            
        except Exception as e:
            self.logger.error(f"librosa音频处理失败: {e}")
            # 降级到简单复制
            return await self._simple_copy(input_path, output_path)
    
    def _enhance_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """
        音频增强处理
        
        Args:
            audio_data: 音频数据
            
        Returns:
            增强后的音频数据
        """
        try:
            # 归一化音频
            if np.max(np.abs(audio_data)) > 0:
                audio_data = audio_data / np.max(np.abs(audio_data)) * 0.8
            
            # 简单的噪音过滤（移除过小的信号）
            threshold = np.max(np.abs(audio_data)) * 0.01
            audio_data = np.where(np.abs(audio_data) < threshold, 0, audio_data)
            
            return audio_data
            
        except Exception as e:
            self.logger.warning(f"音频增强失败: {e}")
            return audio_data
    
    async def _simple_copy(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """
        简单文件复制（无法使用librosa时的降级方案）
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            
        Returns:
            文件信息
        """
        try:
            async with aiofiles.open(input_path, 'rb') as src:
                async with aiofiles.open(output_path, 'wb') as dst:
                    await dst.write(await src.read())
            
            # 返回基本信息
            file_size = Path(output_path).stat().st_size
            return {
                'duration': None,
                'sample_rate': None,
                'channels': None,
                'frames': None,
                'file_size': file_size,
                'enhanced': False
            }
            
        except Exception as e:
            self.logger.error(f"文件复制失败: {e}")
            raise
    
    async def _generate_temp_path(self, input_path: str, target_format: str) -> str:
        """
        生成临时文件路径
        
        Args:
            input_path: 输入文件路径
            target_format: 目标格式
            
        Returns:
            临时文件路径
        """
        input_name = Path(input_path).stem
        temp_filename = f"processed_{input_name}_{get_current_datetime().strftime('%Y%m%d_%H%M%S')}.{target_format}"
        return str(Path(self.temp_dir) / temp_filename)
    
    @ErrorHandler.with_error_handling()
    async def batch_process_audio(self, input_paths: List[str]) -> List[Dict[str, Any]]:
        """
        批量处理音频文件
        
        Args:
            input_paths: 输入文件路径列表
            
        Returns:
            处理结果列表
        """
        self.logger.info(f"开始批量处理音频，文件数量: {len(input_paths)}")
        
        # 创建异步任务
        tasks = [self.process_audio_file(path) for path in input_paths]
        
        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"批量处理失败 {input_paths[i]}: {result}")
            else:
                successful_results.append(result)
        
        self.logger.info(f"批量音频处理完成，成功: {len(successful_results)}/{len(input_paths)}")
        return successful_results
    
    async def cleanup_temp_files(self, max_age_hours: int = 24):
        """
        清理临时文件
        
        Args:
            max_age_hours: 文件最大保留时间（小时）
        """
        try:
            temp_path = Path(self.temp_dir)
            current_time = get_current_datetime()
            
            for file_path in temp_path.glob("processed_*"):
                if file_path.is_file():
                    file_age = current_time - datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_age.total_seconds() > max_age_hours * 3600:
                        file_path.unlink()
                        self.logger.debug(f"清理临时文件: {file_path}")
            
        except Exception as e:
            self.logger.error(f"清理临时文件失败: {e}")
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """
        获取处理统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'audio_libs_available': AUDIO_LIBS_AVAILABLE,
            'target_sample_rate': self.target_sample_rate,
            'target_channels': self.target_channels,
            'supported_formats': self.supported_formats,
            'temp_dir': self.temp_dir,
            'max_file_size': MultiModalConstants.MAX_AUDIO_SIZE,
            'duration_limits': {
                'min': MultiModalConstants.MIN_AUDIO_DURATION,
                'max': MultiModalConstants.MAX_AUDIO_DURATION
            },
            'timestamp': get_current_datetime()
        }