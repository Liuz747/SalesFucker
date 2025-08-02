"""
多模态API端点

该模块提供多模态交互的FastAPI端点。
支持语音上传、图像上传和多模态对话处理。
重构后采用模块化设计，提高代码组织性和可维护性。

核心功能:
- 语音文件上传和处理
- 图像文件上传和分析
- 多模态对话管理
- 实时处理状态追踪
"""

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional

from src.utils import (
    get_processing_time_ms,
    ProcessingType
)
from src.api.v1.multimodal_handlers import MultiModalAPIHandler
from src.api.v1.multimodal_tasks import MultiModalTaskProcessor
from src.api.v1.multimodal_utils import (
    create_audio_attachment,
    create_image_attachment,
    build_upload_response,
    build_multimodal_response,
    build_status_response,
    build_health_response
)


# 创建路由器
router = APIRouter(prefix="/multimodal", tags=["multimodal"])

# 全局处理器实例
api_handler = MultiModalAPIHandler()
task_processor = MultiModalTaskProcessor(api_handler)


@router.post("/voice/upload")
async def upload_voice_file(
    background_tasks: BackgroundTasks,
    tenant_id: str = Form(...),
    customer_id: Optional[str] = Form(None),
    conversation_id: Optional[str] = Form(None),
    language: Optional[str] = Form("zh"),
    file: UploadFile = File(...)
) -> JSONResponse:
    """
    上传语音文件进行处理
    
    Args:
        tenant_id: 租户标识符
        customer_id: 客户标识符
        conversation_id: 对话标识符
        language: 语言偏好
        file: 音频文件
    
    Returns:
        处理状态和任务ID
    """
    try:
        # 验证并保存文件
        temp_path, audio_attachment = await api_handler.validate_and_save_file(
            file, 'audio', tenant_id, customer_id
        )
        
        # 生成任务ID
        import uuid
        task_id = str(uuid.uuid4())
        
        # 创建任务状态
        api_handler.create_task_status(task_id, 'voice_transcription')
        
        # 启动后台处理
        background_tasks.add_task(
            task_processor.process_voice_file,
            task_id,
            audio_attachment,
            tenant_id,
            customer_id,
            conversation_id,
            language,
            temp_path
        )
        
        api_handler.logger.info(f"语音文件上传成功: {file.filename}, 任务ID: {task_id}")
        
        return JSONResponse(build_upload_response(task_id, 'voice'))
        
    except HTTPException:
        raise
    except Exception as e:
        api_handler.logger.error(f"语音文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/image/upload")
async def upload_image_file(
    background_tasks: BackgroundTasks,
    tenant_id: str = Form(...),
    customer_id: Optional[str] = Form(None),
    conversation_id: Optional[str] = Form(None),
    analysis_type: Optional[str] = Form(ProcessingType.IMAGE_ANALYSIS),
    language: Optional[str] = Form("zh"),
    file: UploadFile = File(...)
) -> JSONResponse:
    """
    上传图像文件进行分析
    
    Args:
        tenant_id: 租户标识符
        customer_id: 客户标识符
        conversation_id: 对话标识符
        analysis_type: 分析类型
        language: 语言偏好
        file: 图像文件
    
    Returns:
        处理状态和任务ID
    """
    try:
        # 验证并保存文件
        temp_path, image_attachment = await api_handler.validate_and_save_file(
            file, 'image', tenant_id, customer_id
        )
        
        # 设置分析类型
        if analysis_type in [ProcessingType.SKIN_ANALYSIS, ProcessingType.PRODUCT_RECOGNITION]:
            image_attachment.set_analysis_type(analysis_type)
        
        # 生成任务ID
        import uuid
        task_id = str(uuid.uuid4())
        
        # 创建任务状态
        api_handler.create_task_status(task_id, analysis_type)
        
        # 启动后台处理
        background_tasks.add_task(
            task_processor.process_image_file,
            task_id,
            image_attachment,
            tenant_id,
            customer_id,
            conversation_id,
            language,
            temp_path
        )
        
        api_handler.logger.info(f"图像文件上传成功: {file.filename}, 任务ID: {task_id}")
        
        return JSONResponse(build_upload_response(task_id, 'image', 15))
        
    except HTTPException:
        raise
    except Exception as e:
        api_handler.logger.error(f"图像文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversation/multimodal")
async def create_multimodal_conversation(
    background_tasks: BackgroundTasks,
    tenant_id: str = Form(...),
    customer_id: Optional[str] = Form(None),
    conversation_id: Optional[str] = Form(None),
    text_message: Optional[str] = Form(None),
    language: Optional[str] = Form("zh"),
    voice_files: Optional[List[UploadFile]] = File(None),
    image_files: Optional[List[UploadFile]] = File(None)
) -> JSONResponse:
    """
    创建多模态对话
    
    Args:
        tenant_id: 租户标识符
        customer_id: 客户标识符
        conversation_id: 对话标识符
        text_message: 文本消息
        language: 语言偏好
        voice_files: 语音文件列表
        image_files: 图像文件列表
    
    Returns:
        对话处理结果
    """
    try:
        from datetime import datetime
        start_time = datetime.now()
        
        # 处理文件附件
        voice_attachments = []
        if voice_files:
            for voice_file in voice_files:
                if voice_file.filename:
                    attachment = await create_audio_attachment(
                        voice_file, tenant_id, customer_id, api_handler.temp_dir
                    )
                    voice_attachments.append(attachment)
        
        image_attachments = []
        if image_files:
            for image_file in image_files:
                if image_file.filename:
                    attachment = await create_image_attachment(
                        image_file, tenant_id, customer_id, api_handler.temp_dir
                    )
                    image_attachments.append(attachment)
        
        # 创建多模态消息
        multimodal_message = await api_handler.create_multimodal_message(
            tenant_id=tenant_id,
            customer_id=customer_id,
            conversation_id=conversation_id,
            text_message=text_message,
            language=language,
            voice_attachments=voice_attachments,
            image_attachments=image_attachments
        )
        
        # 生成任务ID
        import uuid
        task_id = str(uuid.uuid4())
        
        # 创建任务状态
        api_handler.create_task_status(
            task_id, 
            'multimodal_conversation',
            conversation_id=multimodal_message.conversation_id,
            message_id=multimodal_message.message_id
        )
        
        # 启动后台处理
        background_tasks.add_task(
            task_processor.process_multimodal_conversation,
            task_id,
            multimodal_message,
            tenant_id
        )
        
        processing_time = get_processing_time_ms(start_time)
        
        api_handler.logger.info(
            f"多模态对话创建成功: {multimodal_message.conversation_id}, "
            f"任务ID: {task_id}, 耗时: {processing_time}ms"
        )
        
        # 构建响应
        input_type = multimodal_message.context.get('input_type', 'text')
        attachment_counts = {
            'voice_count': len(voice_attachments),
            'image_count': len(image_attachments)
        }
        
        return JSONResponse(build_multimodal_response(
            task_id,
            multimodal_message.conversation_id,
            multimodal_message.message_id,
            input_type,
            attachment_counts
        ))
        
    except HTTPException:
        raise
    except Exception as e:
        api_handler.logger.error(f"多模态对话创建失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}")
async def get_processing_status(task_id: str) -> JSONResponse:
    """
    获取处理状态
    
    Args:
        task_id: 任务标识符
    
    Returns:
        处理状态信息
    """
    try:
        task_info = api_handler.get_task_status(task_id)
        if not task_info:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return JSONResponse(build_status_response(task_info, task_id))
        
    except HTTPException:
        raise
    except Exception as e:
        api_handler.logger.error(f"状态查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversation/{conversation_id}/history")
async def get_conversation_history(
    conversation_id: str,
    tenant_id: str,
    limit: int = 20
) -> JSONResponse:
    """
    获取对话历史
    
    Args:
        conversation_id: 对话标识符
        tenant_id: 租户标识符
        limit: 返回记录数量
    
    Returns:
        对话历史记录
    """
    try:
        # 在实际应用中，这里应该从数据库获取历史记录
        # 目前返回模拟数据
        return JSONResponse({
            'conversation_id': conversation_id,
            'tenant_id': tenant_id,
            'messages': [],
            'total_messages': 0,
            'message': '对话历史功能正在开发中'
        })
        
    except Exception as e:
        api_handler.logger.error(f"对话历史获取失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    tenant_id: str
) -> JSONResponse:
    """
    删除对话
    
    Args:
        conversation_id: 对话标识符
        tenant_id: 租户标识符
    
    Returns:
        删除结果
    """
    try:
        # 在实际应用中，这里应该从数据库删除对话数据
        # 同时清理相关的临时文件
        
        return JSONResponse({
            'success': True,
            'conversation_id': conversation_id,
            'message': '对话已删除'
        })
        
    except Exception as e:
        api_handler.logger.error(f"对话删除失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check() -> JSONResponse:
    """健康检查端点"""
    try:
        health_info = api_handler.get_service_health()
        return JSONResponse(build_health_response(
            health_info['active_tasks'],
            health_info['supported_formats']
        ))
        
    except Exception as e:
        api_handler.logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 注意: 辅助函数已移动到 multimodal_utils.py 和 multimodal_tasks.py 模块中