"""
多模态处理器

该模块提供多模态内容的统一处理接口，协调语音转录和图像分析服务。
实现异步处理、状态管理和结果聚合。

核心功能:
- 统一的多模态处理接口
- 异步处理管理
- 结果聚合和状态同步
- 错误处理和重试机制
"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from src.utils import (
    get_current_datetime,
    get_processing_time_ms,
    LoggerMixin,
    ErrorHandler,
    ProcessingStatus,
    ProcessingType,
    MultiModalConstants
)
from .message import MultiModalMessage, ProcessingResult
from .attachment import BaseAttachment, AudioAttachment, ImageAttachment


class MultiModalProcessor(LoggerMixin):
    """
    多模态处理器类
    
    提供多模态内容的统一处理接口，协调各种处理服务。
    支持异步处理、批量操作和智能调度。
    
    属性:
        tenant_id: 租户标识符
        voice_processor: 语音处理器实例
        image_processor: 图像处理器实例
        processing_queue: 处理队列
        max_concurrent: 最大并发处理数
    """
    
    def __init__(self, tenant_id: str):
        """
        初始化多模态处理器
        
        Args:
            tenant_id: 租户标识符
        """
        super().__init__()
        self.tenant_id = tenant_id
        self.voice_processor = None
        self.image_processor = None
        self.processing_queue = asyncio.Queue()
        self.max_concurrent = MultiModalConstants.MAX_CONCURRENT_PROCESSING
        
        self.logger.info(f"多模态处理器已初始化 - 租户: {tenant_id}")
    
    def set_voice_processor(self, processor):
        """设置语音处理器"""
        self.voice_processor = processor
        self.logger.info("语音处理器已设置")
    
    def set_image_processor(self, processor):
        """设置图像处理器"""
        self.image_processor = processor
        self.logger.info("图像处理器已设置")
    
    @ErrorHandler.with_error_handling()
    async def process_message(self, message: MultiModalMessage) -> MultiModalMessage:
        """
        处理多模态消息
        
        Args:
            message: 多模态消息
            
        Returns:
            处理后的消息
        """
        start_time = datetime.now()
        self.logger.info(f"开始处理多模态消息: {message.message_id}")
        
        if not message.attachments:
            self.logger.info("消息无附件，跳过多模态处理")
            return message
        
        # 创建处理任务
        tasks = []
        for attachment in message.attachments:
            if isinstance(attachment, AudioAttachment):
                tasks.append(self._process_audio_attachment(attachment))
            elif isinstance(attachment, ImageAttachment):
                tasks.append(self._process_image_attachment(attachment))
        
        # 并发执行处理任务
        if tasks:
            results = await self._execute_concurrent_tasks(tasks)
            
            # 添加处理结果到消息
            for result in results:
                if result:
                    message.add_processing_result(result)
        
        # 更新整合内容
        message.update_combined_content()
        
        processing_time = get_processing_time_ms(start_time)
        self.logger.info(
            f"多模态消息处理完成: {message.message_id}, "
            f"耗时: {processing_time}ms, "
            f"附件数: {len(message.attachments)}"
        )
        
        return message
    
    async def _execute_concurrent_tasks(self, tasks: List) -> List[ProcessingResult]:
        """
        并发执行处理任务
        
        Args:
            tasks: 任务列表
            
        Returns:
            处理结果列表
        """
        # 限制并发数量
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def bounded_task(task):
            async with semaphore:
                return await task
        
        # 执行所有任务
        results = await asyncio.gather(
            *[bounded_task(task) for task in tasks],
            return_exceptions=True
        )
        
        # 过滤异常结果
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"处理任务异常: {result}")
            elif result:
                valid_results.append(result)
        
        return valid_results
    
    @ErrorHandler.with_error_handling()
    async def _process_audio_attachment(self, attachment: AudioAttachment) -> Optional[ProcessingResult]:
        """
        处理音频附件
        
        Args:
            attachment: 音频附件
            
        Returns:
            处理结果
        """
        if not self.voice_processor:
            self.logger.error("语音处理器未设置")
            return self._create_error_result(
                attachment.attachment_id,
                ProcessingType.VOICE_TRANSCRIPTION,
                "语音处理器未设置"
            )
        
        start_time = datetime.now()
        attachment.update_status(ProcessingStatus.TRANSCRIBING)
        
        try:
            # 调用语音处理器
            transcription_result = await self.voice_processor.transcribe_audio(
                attachment.upload_path,
                language=attachment.language or MultiModalConstants.DEFAULT_VOICE_LANGUAGE
            )
            
            # 更新附件信息
            attachment.transcription = transcription_result.get('text', '')
            attachment.confidence_score = transcription_result.get('confidence', 0.0)
            attachment.language = transcription_result.get('language', attachment.language)
            
            # 检查结果质量
            if attachment.is_transcription_confident():
                attachment.update_status(ProcessingStatus.COMPLETED)
                status = ProcessingStatus.COMPLETED
            else:
                attachment.update_status(ProcessingStatus.COMPLETED, {
                    'low_confidence': True,
                    'confidence_score': attachment.confidence_score
                })
                status = ProcessingStatus.COMPLETED
            
            processing_time = get_processing_time_ms(start_time)
            
            return ProcessingResult(
                attachment_id=attachment.attachment_id,
                processing_type=ProcessingType.VOICE_TRANSCRIPTION,
                status=status,
                result_data={
                    'transcription': attachment.transcription,
                    'language': attachment.language,
                    'duration': attachment.duration
                },
                confidence_score=attachment.confidence_score,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            attachment.update_status(ProcessingStatus.ERROR, {'error': str(e)})
            self.logger.error(f"音频处理失败: {e}")
            return self._create_error_result(
                attachment.attachment_id,
                ProcessingType.VOICE_TRANSCRIPTION,
                str(e)
            )
    
    @ErrorHandler.with_error_handling()
    async def _process_image_attachment(self, attachment: ImageAttachment) -> Optional[ProcessingResult]:
        """
        处理图像附件
        
        Args:
            attachment: 图像附件
            
        Returns:
            处理结果
        """
        if not self.image_processor:
            self.logger.error("图像处理器未设置")
            return self._create_error_result(
                attachment.attachment_id,
                attachment.processing_type,
                "图像处理器未设置"
            )
        
        start_time = datetime.now()
        attachment.update_status(ProcessingStatus.ANALYZING)
        
        try:
            # 根据分析类型调用相应的处理方法
            if attachment.analysis_type == ProcessingType.SKIN_ANALYSIS:
                analysis_result = await self.image_processor.analyze_skin(
                    attachment.upload_path
                )
            elif attachment.analysis_type == ProcessingType.PRODUCT_RECOGNITION:
                analysis_result = await self.image_processor.recognize_product(
                    attachment.upload_path
                )
            else:
                analysis_result = await self.image_processor.analyze_general(
                    attachment.upload_path
                )
            
            # 更新附件信息
            attachment.analysis_results = analysis_result.get('results', {})
            attachment.confidence_scores = analysis_result.get('confidence_scores', {})
            attachment.detected_objects = analysis_result.get('objects', [])
            
            # 检查结果质量
            if attachment.is_analysis_confident():
                attachment.update_status(ProcessingStatus.COMPLETED)
                status = ProcessingStatus.COMPLETED
            else:
                attachment.update_status(ProcessingStatus.COMPLETED, {
                    'low_confidence': True,
                    'confidence_scores': attachment.confidence_scores
                })
                status = ProcessingStatus.COMPLETED
            
            processing_time = get_processing_time_ms(start_time)
            
            return ProcessingResult(
                attachment_id=attachment.attachment_id,
                processing_type=attachment.processing_type,
                status=status,
                result_data=attachment.analysis_results,
                confidence_score=analysis_result.get('overall_confidence', 0.0),
                processing_time_ms=processing_time,
                metadata={
                    'objects_detected': len(attachment.detected_objects),
                    'analysis_type': attachment.analysis_type
                }
            )
            
        except Exception as e:
            attachment.update_status(ProcessingStatus.ERROR, {'error': str(e)})
            self.logger.error(f"图像处理失败: {e}")
            return self._create_error_result(
                attachment.attachment_id,
                attachment.processing_type,
                str(e)
            )
    
    def _create_error_result(
        self, 
        attachment_id: str, 
        processing_type: ProcessingType, 
        error_message: str
    ) -> ProcessingResult:
        """
        创建错误结果
        
        Args:
            attachment_id: 附件ID
            processing_type: 处理类型
            error_message: 错误信息
            
        Returns:
            错误处理结果
        """
        return ProcessingResult(
            attachment_id=attachment_id,
            processing_type=processing_type,
            status=ProcessingStatus.ERROR,
            error_message=error_message,
            result_data={},
            confidence_score=0.0
        )
    
    @ErrorHandler.with_error_handling()
    async def batch_process_images(
        self, 
        attachments: List[ImageAttachment],
        analysis_type: ProcessingType = ProcessingType.IMAGE_ANALYSIS
    ) -> List[ProcessingResult]:
        """
        批量处理图像
        
        Args:
            attachments: 图像附件列表
            analysis_type: 分析类型
            
        Returns:
            处理结果列表
        """
        self.logger.info(f"开始批量处理图像，数量: {len(attachments)}")
        
        # 设置分析类型
        for attachment in attachments:
            attachment.set_analysis_type(analysis_type)
        
        # 创建处理任务
        tasks = [self._process_image_attachment(att) for att in attachments]
        
        # 执行批量处理
        results = await self._execute_concurrent_tasks(tasks)
        
        self.logger.info(f"批量图像处理完成，成功处理: {len(results)}")
        return results
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """
        获取处理统计信息
        
        Returns:
            处理统计数据
        """
        return {
            'tenant_id': self.tenant_id,
            'voice_processor_available': self.voice_processor is not None,
            'image_processor_available': self.image_processor is not None,
            'max_concurrent': self.max_concurrent,
            'queue_size': self.processing_queue.qsize(),
            'timestamp': get_current_datetime()
        }