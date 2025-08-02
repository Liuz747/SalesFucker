"""
多模态后台任务模块

该模块定义多模态处理的后台任务。
将各种处理任务集中管理，提高代码组织性。

核心功能:
- 语音文件后台处理
- 图像文件后台处理
- 多模态对话处理
- 错误处理和清理
"""

import os
from typing import Dict, Any, Optional

from src.utils import (
    get_current_datetime,
    LoggerMixin,
    ProcessingStatus,
    ProcessingType
)
from src.multimodal.core.attachment import AudioAttachment, ImageAttachment
from src.multimodal.core.message import MultiModalMessage
from src.api.v1.multimodal_handlers import MultiModalAPIHandler


class MultiModalTaskProcessor(LoggerMixin):
    """
    多模态任务处理器
    
    管理所有多模态处理的后台任务。
    提供统一的任务执行和错误处理机制。
    
    属性:
        api_handler: API处理器实例
    """
    
    def __init__(self, api_handler: MultiModalAPIHandler):
        super().__init__()
        self.api_handler = api_handler
    
    async def process_voice_file(
        self,
        task_id: str,
        attachment: AudioAttachment,
        tenant_id: str,
        customer_id: Optional[str],
        conversation_id: Optional[str],
        language: str,
        temp_path: str
    ):
        """后台处理语音文件"""
        try:
            # 更新状态
            self.api_handler.update_task_status(task_id, progress=10)
            
            # 获取处理器
            processor = await self.api_handler.get_processor(tenant_id)
            
            # 处理语音
            self.api_handler.update_task_status(task_id, progress=50)
            transcription_result = await processor.whisper_service.transcribe_audio(
                temp_path, language
            )
            
            # 更新附件信息
            attachment.transcription = transcription_result['text']
            attachment.confidence_score = transcription_result['confidence']
            attachment.language = transcription_result['language']
            attachment.update_status(ProcessingStatus.COMPLETED)
            
            # 完成处理
            self.api_handler.update_task_status(task_id, **{
                'status': 'completed',
                'progress': 100,
                'completed_at': get_current_datetime(),
                'result': {
                    'transcription': transcription_result['text'],
                    'language': transcription_result['language'],
                    'confidence': transcription_result['confidence'],
                    'duration': transcription_result.get('duration')
                }
            })
            
            self.logger.info(f"语音处理完成: {task_id}")
            
        except Exception as e:
            self._handle_task_error(task_id, e, "语音处理失败")
        
        finally:
            await self._cleanup_temp_file(temp_path)
    
    async def process_image_file(
        self,
        task_id: str,
        attachment: ImageAttachment,
        tenant_id: str,
        customer_id: Optional[str],
        conversation_id: Optional[str],
        language: str,
        temp_path: str
    ):
        """后台处理图像文件"""
        try:
            # 更新状态
            self.api_handler.update_task_status(task_id, progress=10)
            
            # 获取处理器
            processor = await self.api_handler.get_processor(tenant_id)
            
            # 处理图像
            self.api_handler.update_task_status(task_id, progress=50)
            
            # 根据分析类型调用不同的方法
            analysis_type = attachment.analysis_type or ProcessingType.IMAGE_ANALYSIS
            
            if analysis_type == ProcessingType.SKIN_ANALYSIS:
                analysis_result = await processor.gpt4v_service.analyze_skin(temp_path, language)
            elif analysis_type == ProcessingType.PRODUCT_RECOGNITION:
                analysis_result = await processor.gpt4v_service.recognize_product(temp_path, language)
            else:
                analysis_result = await processor.gpt4v_service.analyze_general(temp_path, language)
            
            # 更新附件信息
            attachment.analysis_results = analysis_result['results']
            attachment.confidence_scores = analysis_result['confidence_scores']
            attachment.update_status(ProcessingStatus.COMPLETED)
            
            # 完成处理
            self.api_handler.update_task_status(task_id, **{
                'status': 'completed',
                'progress': 100,
                'completed_at': get_current_datetime(),
                'result': {
                    'analysis_type': analysis_type,
                    'results': analysis_result['results'],
                    'confidence': analysis_result['overall_confidence']
                }
            })
            
            self.logger.info(f"图像处理完成: {task_id}")
            
        except Exception as e:
            self._handle_task_error(task_id, e, "图像处理失败")
        
        finally:
            await self._cleanup_temp_file(temp_path)
    
    async def process_multimodal_conversation(
        self,
        task_id: str,
        multimodal_message: MultiModalMessage,
        tenant_id: str
    ):
        """后台处理多模态对话"""
        try:
            # 更新状态
            self.api_handler.update_task_status(task_id, progress=10)
            
            # 获取处理器和编排器
            processor = await self.api_handler.get_processor(tenant_id)
            orchestrator = await self.api_handler.get_orchestrator(tenant_id)
            
            # 处理多模态消息
            self.api_handler.update_task_status(task_id, progress=30)
            processed_message = await processor.process_multimodal_message(multimodal_message)
            
            # 转换为智能体消息
            self.api_handler.update_task_status(task_id, progress=50)
            agent_message = await processor.create_agent_message_from_multimodal(processed_message)
            
            # 通过智能体编排器处理
            self.api_handler.update_task_status(task_id, progress=80)
            # 注意：这里需要根据实际的编排器接口调整
            # response = await orchestrator.process_message(agent_message)
            
            # 完成处理
            self.api_handler.update_task_status(task_id, **{
                'status': 'completed',
                'progress': 100,
                'completed_at': get_current_datetime(),
                'result': {
                    'conversation_id': processed_message.conversation_id,
                    'message_id': processed_message.message_id,
                    'processing_summary': processed_message.get_processing_summary(),
                    'combined_content': processed_message.combined_content,
                    # 'agent_response': response.payload if 'response' in locals() else None
                }
            })
            
            self.logger.info(f"多模态对话处理完成: {task_id}")
            
        except Exception as e:
            self._handle_task_error(task_id, e, "多模态对话处理失败")
        
        finally:
            # 清理临时文件
            temp_paths = []
            for attachment in multimodal_message.attachments:
                if attachment.upload_path:
                    temp_paths.append(attachment.upload_path)
            
            await self.api_handler.cleanup_temp_files(temp_paths)
    
    def _handle_task_error(self, task_id: str, error: Exception, context: str):
        """处理任务错误"""
        self.api_handler.update_task_status(task_id, **{
            'status': 'error',
            'error': str(error),
            'completed_at': get_current_datetime()
        })
        self.logger.error(f"{context}: {task_id}, 错误: {error}")
    
    async def _cleanup_temp_file(self, temp_path: str):
        """清理单个临时文件"""
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as e:
            self.logger.warning(f"临时文件清理失败: {e}")