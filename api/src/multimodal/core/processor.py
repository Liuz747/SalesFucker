"""
多模态处理器核心模块

该模块提供多模态消息的统一处理入口，协调语音转录、图像分析和智能体集成。
实现异步处理管道，确保高性能和可靠性。

核心功能:
- 多模态消息统一处理入口
- 异步处理管道和任务协调
- 智能体集成和结果聚合
- 错误处理和降级机制
"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import uuid

from utils import (
    get_current_datetime,
    get_processing_time_ms,
    LoggerMixin,
    ProcessingStatus,
    ProcessingType,
    InputType,
    MultiModalConstants
)
from src.multimodal.core.message import MultiModalMessage, ProcessingResult
from src.multimodal.core.attachment import AudioAttachment, ImageAttachment
from src.multimodal.voice.whisper_service import WhisperService
from src.multimodal.image.gpt4v_service import GPT4VService
from src.agents.base import AgentMessage


class MultiModalProcessor(LoggerMixin):
    """
    多模态处理器核心类
    
    负责协调和管理所有多模态内容的处理流程。
    提供统一的处理接口和异步处理能力。
    
    属性:
        whisper_service: Whisper语音识别服务
        gpt4v_service: GPT-4V图像分析服务
        max_concurrent: 最大并发处理数
        processing_timeout: 处理超时时间
    """
    
    def __init__(
        self,
        openai_api_key: str,
        max_concurrent: int = MultiModalConstants.MAX_CONCURRENT_PROCESSING
    ):
        """
        初始化多模态处理器
        
        Args:
            openai_api_key: OpenAI API密钥
            max_concurrent: 最大并发处理数
        """
        super().__init__()
        
        # 初始化服务
        self.whisper_service = WhisperService(openai_api_key)
        self.gpt4v_service = GPT4VService(openai_api_key)
        
        # 处理配置
        self.max_concurrent = max_concurrent
        self.processing_timeout = 30.0  # 30秒总超时
        
        # 异步资源
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._processing_tasks: Dict[str, asyncio.Task] = {}
        
        self.logger.info("多模态处理器已初始化")
    
    async def process_multimodal_message(
        self, 
        message: MultiModalMessage,
        agent_context: Optional[Dict[str, Any]] = None
    ) -> MultiModalMessage:
        """
        处理多模态消息
        
        Args:
            message: 多模态消息对象
            agent_context: 智能体上下文信息
            
        Returns:
            处理完成的多模态消息
        """
        start_time = datetime.now()
        
        self.logger.info(
            f"开始处理多模态消息: {message.message_id}, "
            f"附件数量: {len(message.attachments)}"
        )
        
        try:
            # 验证消息和附件
            self._validate_message(message)
            
            # 如果没有附件，直接返回
            if not message.attachments:
                self.logger.info(f"消息无附件，跳过多模态处理: {message.message_id}")
                return message
            
            # 处理所有附件
            processing_results = await self._process_all_attachments(
                message.attachments, 
                agent_context or {}
            )
            
            # 更新消息中的处理结果
            for result in processing_results:
                message.add_processing_result(result)
            
            # 更新整合内容
            message.update_combined_content()
            
            # 计算处理时间
            processing_time = get_processing_time_ms(start_time)
            message.multimodal_context.update({
                'processing_time_ms': processing_time,
                'processed_at': get_current_datetime(),
                'processing_summary': message.get_processing_summary()
            })
            
            self.logger.info(
                f"多模态消息处理完成: {message.message_id}, "
                f"耗时: {processing_time}ms, "
                f"成功率: {self._calculate_success_rate(processing_results):.1%}"
            )
            
            return message
            
        except Exception as e:
            self.logger.error(f"多模态消息处理失败: {message.message_id}, 错误: {e}")
            
            # 创建错误结果
            error_result = ProcessingResult(
                attachment_id="error",
                processing_type=ProcessingType.IMAGE_ANALYSIS,
                status=ProcessingStatus.ERROR,
                error_message=str(e),
                processing_time_ms=get_processing_time_ms(start_time)
            )
            message.add_processing_result(error_result)
            
            return message
    
    async def _process_all_attachments(
        self,
        attachments: List,
        context: Dict[str, Any]
    ) -> List[ProcessingResult]:
        """
        处理所有附件
        
        Args:
            attachments: 附件列表
            context: 处理上下文
            
        Returns:
            处理结果列表
        """
        # 创建处理任务
        tasks = []
        for attachment in attachments:
            if isinstance(attachment, AudioAttachment):
                task = self._process_audio_attachment(attachment, context)
            elif isinstance(attachment, ImageAttachment):
                task = self._process_image_attachment(attachment, context)
            else:
                self.logger.warning(f"不支持的附件类型: {type(attachment)}")
                continue
            
            tasks.append(task)
        
        # 并发执行处理任务
        if tasks:
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=self.processing_timeout
                )
                
                # 处理结果
                processing_results = []
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        self.logger.error(f"附件处理失败: {attachments[i].attachment_id}, 错误: {result}")
                        error_result = ProcessingResult(
                            attachment_id=attachments[i].attachment_id,
                            processing_type=attachments[i].processing_type,
                            status=ProcessingStatus.ERROR,
                            error_message=str(result)
                        )
                        processing_results.append(error_result)
                    else:
                        processing_results.append(result)
                
                return processing_results
                
            except asyncio.TimeoutError:
                self.logger.error(f"多模态处理超时: {self.processing_timeout}秒")
                raise Exception("多模态处理超时")
        
        return []
    
    async def _process_audio_attachment(
        self,
        attachment: AudioAttachment,
        context: Dict[str, Any]
    ) -> ProcessingResult:
        """
        处理音频附件
        
        Args:
            attachment: 音频附件
            context: 处理上下文
            
        Returns:
            处理结果
        """
        async with self._semaphore:
            start_time = datetime.now()
            
            try:
                attachment.update_status(ProcessingStatus.PROCESSING)
                
                # 确定语言
                language = context.get('language', 'zh')
                if language not in MultiModalConstants.SUPPORTED_LANGUAGES:
                    language = MultiModalConstants.DEFAULT_VOICE_LANGUAGE
                
                # 调用Whisper转录
                transcription_result = await self.whisper_service.transcribe_audio(
                    attachment.upload_path,
                    language=language,
                    prompt=context.get('prompt')
                )
                
                # 更新附件信息
                attachment.transcription = transcription_result['text']
                attachment.confidence_score = transcription_result['confidence']
                attachment.language = transcription_result['language']
                attachment.duration = transcription_result.get('duration')
                
                # 更新状态
                attachment.update_status(
                    ProcessingStatus.COMPLETED,
                    {
                        'transcription_result': transcription_result,
                        'language_detected': transcription_result['language'],
                        'is_high_quality': transcription_result['is_high_quality']
                    }
                )
                
                # 创建处理结果
                processing_time = get_processing_time_ms(start_time)
                return ProcessingResult(
                    attachment_id=attachment.attachment_id,
                    processing_type=ProcessingType.VOICE_TRANSCRIPTION,
                    status=ProcessingStatus.COMPLETED,
                    result_data={
                        'text': transcription_result['text'],
                        'language': transcription_result['language'],
                        'duration': transcription_result.get('duration'),
                        'segments': transcription_result.get('segments', [])
                    },
                    confidence_score=transcription_result['confidence'],
                    processing_time_ms=processing_time,
                    metadata=transcription_result
                )
                
            except Exception as e:
                self.logger.error(f"音频附件处理失败: {attachment.attachment_id}, 错误: {e}")
                
                attachment.update_status(ProcessingStatus.ERROR, {'error': str(e)})
                
                return ProcessingResult(
                    attachment_id=attachment.attachment_id,
                    processing_type=ProcessingType.VOICE_TRANSCRIPTION,
                    status=ProcessingStatus.ERROR,
                    error_message=str(e),
                    processing_time_ms=get_processing_time_ms(start_time)
                )
    
    async def _process_image_attachment(
        self,
        attachment: ImageAttachment,
        context: Dict[str, Any]
    ) -> ProcessingResult:
        """
        处理图像附件
        
        Args:
            attachment: 图像附件
            context: 处理上下文
            
        Returns:
            处理结果
        """
        async with self._semaphore:
            start_time = datetime.now()
            
            try:
                attachment.update_status(ProcessingStatus.PROCESSING)
                
                # 确定分析类型
                analysis_type = attachment.analysis_type or context.get('analysis_type', ProcessingType.IMAGE_ANALYSIS)
                language = context.get('language', 'zh')
                
                # 根据分析类型调用不同的分析方法
                if analysis_type == ProcessingType.SKIN_ANALYSIS:
                    analysis_result = await self.gpt4v_service.analyze_skin(
                        attachment.upload_path, 
                        language
                    )
                elif analysis_type == ProcessingType.PRODUCT_RECOGNITION:
                    analysis_result = await self.gpt4v_service.recognize_product(
                        attachment.upload_path, 
                        language
                    )
                else:
                    analysis_result = await self.gpt4v_service.analyze_general(
                        attachment.upload_path, 
                        language
                    )
                
                # 更新附件信息
                attachment.analysis_results = analysis_result['results']
                attachment.confidence_scores = analysis_result['confidence_scores']
                
                # 更新状态
                attachment.update_status(
                    ProcessingStatus.COMPLETED,
                    {
                        'analysis_result': analysis_result,
                        'analysis_type': analysis_type,
                        'overall_confidence': analysis_result['overall_confidence']
                    }
                )
                
                # 创建处理结果
                processing_time = get_processing_time_ms(start_time)
                return ProcessingResult(
                    attachment_id=attachment.attachment_id,
                    processing_type=analysis_type,
                    status=ProcessingStatus.COMPLETED,
                    result_data=analysis_result['results'],
                    confidence_score=analysis_result['overall_confidence'],
                    processing_time_ms=processing_time,
                    metadata=analysis_result
                )
                
            except Exception as e:
                self.logger.error(f"图像附件处理失败: {attachment.attachment_id}, 错误: {e}")
                
                attachment.update_status(ProcessingStatus.ERROR, {'error': str(e)})
                
                return ProcessingResult(
                    attachment_id=attachment.attachment_id,
                    processing_type=attachment.processing_type,
                    status=ProcessingStatus.ERROR,
                    error_message=str(e),
                    processing_time_ms=get_processing_time_ms(start_time)
                )
    
    def _validate_message(self, message: MultiModalMessage):
        """验证多模态消息"""
        if not message.message_id:
            raise ValueError("消息ID不能为空")
        
        if not message.tenant_id:
            raise ValueError("租户ID不能为空")
        
        # 验证附件
        for attachment in message.attachments:
            if not attachment.is_valid_format():
                raise ValueError(f"附件格式不支持: {attachment.file_name}")
            
            if not attachment.upload_path:
                raise ValueError(f"附件路径为空: {attachment.attachment_id}")
    
    def _calculate_success_rate(self, results: List[ProcessingResult]) -> float:
        """计算处理成功率"""
        if not results:
            return 0.0
        
        successful_count = len([r for r in results if r.is_successful()])
        return successful_count / len(results)
    
    async def create_agent_message_from_multimodal(
        self,
        multimodal_message: MultiModalMessage
    ) -> AgentMessage:
        """
        从多模态消息创建智能体消息
        
        Args:
            multimodal_message: 多模态消息
            
        Returns:
            智能体消息
        """
        # 创建基础智能体消息
        agent_message = AgentMessage(
            sender="multimodal_processor",
            recipient="agent_orchestrator",
            message_type="query",
            tenant_id=multimodal_message.tenant_id,
            customer_id=multimodal_message.customer_id,
            conversation_id=multimodal_message.conversation_id,
            session_id=multimodal_message.session_id
        )
        
        # 复制基础属性
        if hasattr(multimodal_message, 'payload'):
            agent_message.payload = multimodal_message.payload.copy()
        
        # 添加多模态处理结果
        multimodal_context = {
            'input_type': multimodal_message.context.get('input_type', InputType.TEXT),
            'has_attachments': len(multimodal_message.attachments) > 0,
            'attachment_count': len(multimodal_message.attachments),
            'processing_summary': multimodal_message.get_processing_summary()
        }
        
        # 添加转录文本
        transcriptions = multimodal_message.get_transcriptions()
        if transcriptions:
            multimodal_context['transcriptions'] = transcriptions
            # 如果有转录文本，更新消息内容
            if not agent_message.payload.get('message'):
                agent_message.payload['message'] = ' '.join(transcriptions)
            else:
                agent_message.payload['message'] += ' ' + ' '.join(transcriptions)
        
        # 添加图像分析结果
        analysis_results = multimodal_message.get_analysis_results()
        if analysis_results:
            multimodal_context['image_analysis'] = analysis_results
        
        # 添加整合内容
        if multimodal_message.combined_content:
            agent_message.payload['combined_content'] = multimodal_message.combined_content
        
        # 更新上下文
        agent_message.context.update(multimodal_context)
        
        return agent_message
    
    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            服务状态信息
        """
        try:
            # 检查子服务状态
            whisper_health = await self.whisper_service.health_check()
            gpt4v_health = await self.gpt4v_service.health_check()
            
            # 汇总状态
            overall_status = "healthy"
            if whisper_health['status'] != 'healthy' or gpt4v_health['status'] != 'healthy':
                overall_status = "degraded"
            
            return {
                'status': overall_status,
                'service': 'multimodal_processor',
                'whisper_service': whisper_health,
                'gpt4v_service': gpt4v_health,
                'max_concurrent': self.max_concurrent,
                'active_tasks': len(self._processing_tasks),
                'timestamp': get_current_datetime()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': get_current_datetime()
            }