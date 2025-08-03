"""
多模态API端点集合

该模块提供简化的多模态API端点定义。
主要处理逻辑已移至专门的处理器模块。
"""

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid

from src.utils import ProcessingType
from src.api.v1.multimodal_handlers import MultiModalAPIHandler
from src.api.v1.multimodal_tasks import MultiModalTaskProcessor
from src.api.v1.multimodal_utils import (
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


class MultiLLMRequest(BaseModel):
    """多LLM请求模型"""
    preferred_provider: Optional[str] = Field(None, description="首选LLM供应商")
    model_name: Optional[str] = Field(None, description="指定模型名称")
    routing_strategy: Optional[str] = Field(None, description="路由策略")
    max_cost: Optional[float] = Field(None, description="最大成本限制")


@router.post("/voice/upload")
async def upload_voice_file(
    background_tasks: BackgroundTasks,
    tenant_id: str = Form(...),
    customer_id: Optional[str] = Form(None),
    conversation_id: Optional[str] = Form(None),
    language: Optional[str] = Form("zh"),
    preferred_provider: Optional[str] = Form(None),
    model_name: Optional[str] = Form(None),
    file: UploadFile = File(...)
) -> JSONResponse:
    """上传语音文件进行处理"""
    try:
        # 验证并保存文件
        temp_path, audio_attachment = await api_handler.validate_and_save_file(
            file, 'audio', tenant_id, customer_id
        )
        
        # 生成任务ID并创建状态
        task_id = str(uuid.uuid4())
        api_handler.create_task_status(task_id, 'voice_transcription')
        
        # 创建多LLM请求信息
        multi_llm_request = {
            "preferred_provider": preferred_provider,
            "model_name": model_name
        }
        
        # 启动后台处理
        background_tasks.add_task(
            task_processor.process_voice_file,
            task_id, audio_attachment, tenant_id, customer_id,
            conversation_id, language, temp_path, multi_llm_request
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
    preferred_provider: Optional[str] = Form(None),
    model_name: Optional[str] = Form(None),
    file: UploadFile = File(...)
) -> JSONResponse:
    """上传图像文件进行分析"""
    try:
        # 验证并保存文件
        temp_path, image_attachment = await api_handler.validate_and_save_file(
            file, 'image', tenant_id, customer_id
        )
        
        # 设置分析类型
        if analysis_type in [ProcessingType.SKIN_ANALYSIS, ProcessingType.PRODUCT_RECOGNITION]:
            image_attachment.set_analysis_type(analysis_type)
        
        # 生成任务ID并创建状态
        task_id = str(uuid.uuid4())
        api_handler.create_task_status(task_id, analysis_type)
        
        # 创建多LLM请求信息
        multi_llm_request = {
            "preferred_provider": preferred_provider,
            "model_name": model_name
        }
        
        # 启动后台处理
        background_tasks.add_task(
            task_processor.process_image_file,
            task_id, image_attachment, tenant_id, customer_id,
            conversation_id, language, temp_path, multi_llm_request
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
    """创建多模态对话"""
    try:
        from datetime import datetime
        from src.api.v1.multimodal_utils import create_audio_attachment, create_image_attachment
        
        start_time = datetime.now()
        
        # 处理语音附件
        voice_attachments = []
        if voice_files:
            for voice_file in voice_files:
                if voice_file.filename:
                    attachment = await create_audio_attachment(
                        voice_file, tenant_id, customer_id, api_handler.temp_dir
                    )
                    voice_attachments.append(attachment)
        
        # 处理图像附件
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
        
        # 生成任务ID并创建状态
        task_id = str(uuid.uuid4())
        api_handler.create_task_status(
            task_id, 'multimodal_conversation',
            conversation_id=multimodal_message.conversation_id,
            message_id=multimodal_message.message_id
        )
        
        # 启动后台处理
        background_tasks.add_task(
            task_processor.process_multimodal_conversation,
            task_id, multimodal_message, tenant_id
        )
        
        from src.utils import get_processing_time_ms
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
            task_id, multimodal_message.conversation_id,
            multimodal_message.message_id, input_type, attachment_counts
        ))
        
    except HTTPException:
        raise
    except Exception as e:
        api_handler.logger.error(f"多模态对话创建失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}")
async def get_processing_status(task_id: str) -> JSONResponse:
    """获取处理状态"""
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
    """获取对话历史"""
    try:
        # 在实际应用中，这里应该从数据库获取历史记录
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
    """删除对话"""
    try:
        # 在实际应用中，这里应该从数据库删除对话数据
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