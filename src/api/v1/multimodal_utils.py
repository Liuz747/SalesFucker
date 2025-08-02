"""
多模态API工具模块

该模块提供多模态API的辅助工具函数。
将通用的工具函数从主路由文件中分离，提高代码复用性。

核心功能:
- 文件附件创建
- 数据格式转换
- 通用验证函数
- 响应构建工具
"""

import uuid
import os
from typing import Dict, Any, Optional, List
from fastapi import UploadFile

from src.utils import (
    get_current_datetime,
    MultiModalConstants
)
from src.multimodal.core.attachment import AudioAttachment, ImageAttachment


async def create_audio_attachment(
    file: UploadFile,
    tenant_id: str,
    customer_id: Optional[str],
    temp_dir: str
) -> AudioAttachment:
    """
    创建音频附件
    
    Args:
        file: 上传的音频文件
        tenant_id: 租户标识符
        customer_id: 客户标识符
        temp_dir: 临时目录
        
    Returns:
        音频附件对象
    """
    file_content = await file.read()
    
    # 验证文件
    file_extension = file.filename.split('.')[-1].lower()
    if file_extension not in MultiModalConstants.SUPPORTED_AUDIO_FORMATS:
        raise ValueError(f"Unsupported audio format: {file_extension}")
    
    if len(file_content) > MultiModalConstants.MAX_AUDIO_SIZE:
        raise ValueError("Audio file too large")
    
    # 保存临时文件
    temp_filename = f"{uuid.uuid4()}_{file.filename}"
    temp_path = os.path.join(temp_dir, temp_filename)
    
    with open(temp_path, "wb") as temp_file:
        temp_file.write(file_content)
    
    return AudioAttachment(
        file_name=file.filename,
        content_type=file.content_type or f"audio/{file_extension}",
        file_size=len(file_content),
        upload_path=temp_path,
        tenant_id=tenant_id,
        customer_id=customer_id
    )


async def create_image_attachment(
    file: UploadFile,
    tenant_id: str,
    customer_id: Optional[str],
    temp_dir: str
) -> ImageAttachment:
    """
    创建图像附件
    
    Args:
        file: 上传的图像文件
        tenant_id: 租户标识符
        customer_id: 客户标识符
        temp_dir: 临时目录
        
    Returns:
        图像附件对象
    """
    file_content = await file.read()
    
    # 验证文件
    file_extension = file.filename.split('.')[-1].lower()
    if file_extension not in MultiModalConstants.SUPPORTED_IMAGE_FORMATS:
        raise ValueError(f"Unsupported image format: {file_extension}")
    
    if len(file_content) > MultiModalConstants.MAX_IMAGE_SIZE:
        raise ValueError("Image file too large")
    
    # 保存临时文件
    temp_filename = f"{uuid.uuid4()}_{file.filename}"
    temp_path = os.path.join(temp_dir, temp_filename)
    
    with open(temp_path, "wb") as temp_file:
        temp_file.write(file_content)
    
    return ImageAttachment(
        file_name=file.filename,
        content_type=file.content_type or f"image/{file_extension}",
        file_size=len(file_content),
        upload_path=temp_path,
        tenant_id=tenant_id,
        customer_id=customer_id
    )


def build_upload_response(
    task_id: str,
    file_type: str,
    estimated_time: int = 10
) -> Dict[str, Any]:
    """
    构建文件上传响应
    
    Args:
        task_id: 任务标识符
        file_type: 文件类型
        estimated_time: 预估处理时间
        
    Returns:
        响应数据
    """
    file_type_messages = {
        'voice': '语音文件已上传，正在处理中',
        'image': '图像文件已上传，正在分析中'
    }
    
    return {
        'success': True,
        'task_id': task_id,
        'status': 'processing',
        'message': file_type_messages.get(file_type, '文件已上传，正在处理中'),
        'estimated_time_seconds': estimated_time
    }


def build_multimodal_response(
    task_id: str,
    conversation_id: str,
    message_id: str,
    input_type: str,
    attachment_counts: Dict[str, int],
    estimated_time: int = 20
) -> Dict[str, Any]:
    """
    构建多模态对话响应
    
    Args:
        task_id: 任务标识符
        conversation_id: 对话标识符
        message_id: 消息标识符
        input_type: 输入类型
        attachment_counts: 附件数量
        estimated_time: 预估处理时间
        
    Returns:
        响应数据
    """
    return {
        'success': True,
        'task_id': task_id,
        'conversation_id': conversation_id,
        'message_id': message_id,
        'status': 'processing',
        'input_type': input_type,
        'attachments': attachment_counts,
        'message': '多模态对话已创建，正在处理中',
        'estimated_time_seconds': estimated_time
    }


def build_status_response(task_info: Dict[str, Any], task_id: str) -> Dict[str, Any]:
    """
    构建状态查询响应
    
    Args:
        task_info: 任务信息
        task_id: 任务标识符
        
    Returns:
        响应数据
    """
    return {
        'task_id': task_id,
        'status': task_info.get('status', 'unknown'),
        'task_type': task_info.get('task_type', 'unknown'),
        'progress': task_info.get('progress', 0),
        'created_at': task_info.get('created_at'),
        'completed_at': task_info.get('completed_at'),
        'result': task_info.get('result'),
        'error': task_info.get('error')
    }


def build_health_response(
    active_tasks: int,
    supported_formats: Dict[str, List[str]]
) -> Dict[str, Any]:
    """
    构建健康检查响应
    
    Args:
        active_tasks: 活跃任务数
        supported_formats: 支持的文件格式
        
    Returns:
        响应数据
    """
    return {
        'status': 'healthy',
        'service': 'multimodal_api',
        'timestamp': get_current_datetime(),
        'active_tasks': active_tasks,
        'supported_formats': supported_formats
    }


def build_error_response(error_message: str) -> Dict[str, Any]:
    """
    构建错误响应
    
    Args:
        error_message: 错误消息
        
    Returns:
        错误响应数据
    """
    return {
        'success': False,
        'error': error_message,
        'timestamp': get_current_datetime()
    }