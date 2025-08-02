"""
多模态API处理器模块

该模块提供多模态API端点的核心处理逻辑。
将处理器逻辑从路由定义中分离，提高代码组织性和可维护性。

核心功能:
- 文件上传处理和验证
- 多模态消息创建和管理
- 后台任务协调
- 状态跟踪和管理
"""

from typing import Dict, Any, Optional, List
import tempfile
import os
import uuid
from datetime import datetime
from fastapi import UploadFile, HTTPException

from src.utils import (
    get_current_datetime,
    get_processing_time_ms,
    LoggerMixin,
    ErrorHandler,
    InputType,
    ProcessingType,
    ProcessingStatus,
    MultiModalConstants
)
from src.multimodal.core.processor import MultiModalProcessor
from src.multimodal.core.message import MultiModalMessage
from src.multimodal.core.attachment import AudioAttachment, ImageAttachment
from src.agents.core.orchestrator import AgentOrchestrator


class MultiModalAPIHandler(LoggerMixin):
    """
    多模态API处理器
    
    负责处理多模态API的核心业务逻辑，包括文件处理、
    消息创建和任务管理。
    
    属性:
        temp_dir: 临时文件目录
        processing_status: 处理状态缓存
        _processor_instances: 处理器实例缓存
        _orchestrator_instances: 编排器实例缓存
    """
    
    def __init__(self):
        super().__init__()
        self.temp_dir = tempfile.gettempdir()
        self.processing_status = {}  # 处理状态缓存
        self._processor_instances = {}
        self._orchestrator_instances = {}
    
    async def get_processor(self, tenant_id: str) -> MultiModalProcessor:
        """获取多模态处理器实例"""
        if tenant_id not in self._processor_instances:
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise HTTPException(status_code=500, detail="OpenAI API key not configured")
            
            self._processor_instances[tenant_id] = MultiModalProcessor(openai_api_key)
        
        return self._processor_instances[tenant_id]
    
    async def get_orchestrator(self, tenant_id: str) -> AgentOrchestrator:
        """获取智能体编排器实例"""
        if tenant_id not in self._orchestrator_instances:
            self._orchestrator_instances[tenant_id] = AgentOrchestrator(tenant_id)
        
        return self._orchestrator_instances[tenant_id]
    
    @ErrorHandler.with_error_handling()
    async def validate_and_save_file(
        self,
        file: UploadFile,
        file_type: str,
        tenant_id: str,
        customer_id: Optional[str] = None
    ) -> tuple[str, Any]:
        """
        验证并保存上传文件
        
        Args:
            file: 上传的文件
            file_type: 文件类型 ('audio' 或 'image')
            tenant_id: 租户标识符
            customer_id: 客户标识符
            
        Returns:
            临时文件路径和附件对象
        """
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # 检查文件格式
        file_extension = file.filename.split('.')[-1].lower()
        
        if file_type == 'audio':
            if file_extension not in MultiModalConstants.SUPPORTED_AUDIO_FORMATS:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Unsupported audio format: {file_extension}"
                )
            max_size = MultiModalConstants.MAX_AUDIO_SIZE
        elif file_type == 'image':
            if file_extension not in MultiModalConstants.SUPPORTED_IMAGE_FORMATS:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Unsupported image format: {file_extension}"
                )
            max_size = MultiModalConstants.MAX_IMAGE_SIZE
        else:
            raise HTTPException(status_code=400, detail="Invalid file type")
        
        # 检查文件大小
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(status_code=400, detail="File too large")
        
        # 保存临时文件
        task_id = str(uuid.uuid4())
        temp_filename = f"{task_id}_{file.filename}"
        temp_path = os.path.join(self.temp_dir, temp_filename)
        
        with open(temp_path, "wb") as temp_file:
            temp_file.write(file_content)
        
        # 创建附件对象
        if file_type == 'audio':
            attachment = AudioAttachment(
                file_name=file.filename,
                content_type=file.content_type or f"audio/{file_extension}",
                file_size=len(file_content),
                upload_path=temp_path,
                tenant_id=tenant_id,
                customer_id=customer_id
            )
        else:  # image
            attachment = ImageAttachment(
                file_name=file.filename,
                content_type=file.content_type or f"image/{file_extension}",
                file_size=len(file_content),
                upload_path=temp_path,
                tenant_id=tenant_id,
                customer_id=customer_id
            )
        
        return temp_path, attachment
    
    def create_task_status(
        self,
        task_id: str,
        task_type: str,
        **additional_data
    ) -> Dict[str, Any]:
        """创建任务状态记录"""
        status = {
            'status': 'processing',
            'task_type': task_type,
            'created_at': get_current_datetime(),
            'progress': 0
        }
        status.update(additional_data)
        
        self.processing_status[task_id] = status
        return status
    
    def update_task_status(
        self,
        task_id: str,
        **updates
    ):
        """更新任务状态"""
        if task_id in self.processing_status:
            self.processing_status[task_id].update(updates)
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        return self.processing_status.get(task_id)
    
    @ErrorHandler.with_error_handling()
    async def create_multimodal_message(
        self,
        tenant_id: str,
        customer_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        text_message: Optional[str] = None,
        language: str = "zh",
        voice_attachments: List[AudioAttachment] = None,
        image_attachments: List[ImageAttachment] = None
    ) -> MultiModalMessage:
        """
        创建多模态消息
        
        Args:
            tenant_id: 租户标识符
            customer_id: 客户标识符
            conversation_id: 对话标识符
            text_message: 文本消息
            language: 语言偏好
            voice_attachments: 语音附件列表
            image_attachments: 图像附件列表
            
        Returns:
            多模态消息对象
        """
        # 生成消息ID和对话ID
        message_id = str(uuid.uuid4())
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        # 创建多模态消息
        multimodal_message = MultiModalMessage(
            message_id=message_id,
            sender="customer",
            recipient="agent_orchestrator",
            message_type="query",
            tenant_id=tenant_id,
            customer_id=customer_id,
            conversation_id=conversation_id,
            payload={'message': text_message or ''}
        )
        
        # 确定输入类型
        input_type = InputType.TEXT
        if voice_attachments and image_attachments:
            input_type = InputType.MULTIMODAL
        elif voice_attachments:
            input_type = InputType.VOICE
        elif image_attachments:
            input_type = InputType.IMAGE
        
        multimodal_message.context['input_type'] = input_type
        multimodal_message.context['language'] = language
        
        # 添加附件
        if voice_attachments:
            for attachment in voice_attachments:
                multimodal_message.add_attachment(attachment)
        
        if image_attachments:
            for attachment in image_attachments:
                multimodal_message.add_attachment(attachment)
        
        return multimodal_message
    
    async def cleanup_temp_files(self, file_paths: List[str]):
        """清理临时文件"""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path) and file_path.startswith(self.temp_dir):
                    os.remove(file_path)
                    self.logger.debug(f"已删除临时文件: {file_path}")
            except Exception as e:
                self.logger.warning(f"清理临时文件失败: {file_path}, 错误: {e}")
    
    def get_service_health(self) -> Dict[str, Any]:
        """获取服务健康状态"""
        return {
            'status': 'healthy',
            'service': 'multimodal_api_handler',
            'timestamp': get_current_datetime(),
            'active_tasks': len(self.processing_status),
            'supported_formats': {
                'audio': MultiModalConstants.SUPPORTED_AUDIO_FORMATS,
                'image': MultiModalConstants.SUPPORTED_IMAGE_FORMATS
            }
        }