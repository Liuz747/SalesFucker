"""
多模态处理API端点

该模块提供多模态内容处理相关的API端点，包括语音识别、
图像分析、批量处理等功能。

端点功能:
- 语音文件上传和转录
- 图像文件上传和分析
- 多模态对话处理
- 批量文件处理
- 处理状态查询和监控
"""

from fastapi import APIRouter, HTTPException, File, UploadFile, Form, BackgroundTasks, Query
from typing import Dict, Any, Optional, List
from datetime import datetime

from .schemas.multimodal import (
    VoiceProcessingRequest,
    ImageAnalysisRequest,
    BatchMultimodalRequest,
    ProcessingStatusResponse,
    BatchProcessingResponse,
    MultimodalCapabilitiesResponse,
    ProcessingType,
    AnalysisType
)
from .multimodal_handler import MultimodalHandler
from utils import get_component_logger

logger = get_component_logger(__name__, "MultimodalEndpoints")

# 创建路由器
router = APIRouter()

# 创建处理器实例
multimodal_handler = MultimodalHandler()


@router.post("/voice/upload", response_model=Dict[str, Any])
async def upload_voice_file(
    background_tasks: BackgroundTasks,
    tenant_id: str = Form(..., description="租户标识符"),
    customer_id: Optional[str] = Form(None, description="客户ID"),
    thread_id: Optional[str] = Form(None, description="对话ID"),
    language: str = Form("zh-CN", description="语言代码"),
    enable_emotion_detection: bool = Form(False, description="启用情感检测"),
    enable_sentiment_analysis: bool = Form(True, description="启用情感分析"),
    noise_reduction: bool = Form(True, description="启用降噪"),
    async_processing: bool = Form(True, description="异步处理"),
    file: UploadFile = File(..., description="音频文件")
):
    """
    上传语音文件进行处理
    
    支持多种音频格式，提供语音转文本、情感分析等功能。
    """
    try:
        # 验证文件格式
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        # 检测音频格式
        audio_format = await multimodal_handler.detect_audio_format(file)
        
        # 创建处理请求
        processing_request = VoiceProcessingRequest(
            tenant_id=tenant_id,
            customer_id=customer_id,
            processing_type=ProcessingType.VOICE_TO_TEXT,
            language=language,
            audio_format=audio_format,
            enable_emotion_detection=enable_emotion_detection,
            enable_sentiment_analysis=enable_sentiment_analysis,
            noise_reduction=noise_reduction,
            async_processing=async_processing
        )
        
        # 处理文件上传
        result = await multimodal_handler.process_voice_upload(
            file=file,
            request=processing_request,
            thread_id=thread_id,
            background_tasks=background_tasks
        )
        
        return result
        
    except Exception as e:
        logger.error(f"语音文件上传失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/image/upload", response_model=Dict[str, Any])
async def upload_image_file(
    background_tasks: BackgroundTasks,
    tenant_id: str = Form(..., description="租户标识符"),
    customer_id: Optional[str] = Form(None, description="客户ID"),
    thread_id: Optional[str] = Form(None, description="对话ID"),
    analysis_types: List[AnalysisType] = Form([AnalysisType.GENERAL_ANALYSIS], description="分析类型列表"),
    detect_products: bool = Form(True, description="检测化妆品产品"),
    analyze_skin_condition: bool = Form(False, description="分析肌肤状况"),
    image_quality: Optional[str] = Form("medium", description="图像质量要求"),
    async_processing: bool = Form(True, description="异步处理"),
    file: UploadFile = File(..., description="图像文件")
):
    """
    上传图像文件进行分析
    
    支持多种图像格式，提供产品识别、肌肤分析等功能。
    """
    try:
        # 验证文件格式
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        # 检测图像格式
        image_format = await multimodal_handler.detect_image_format(file)
        
        # 验证文件大小
        file_size = await multimodal_handler.get_file_size(file)
        if file_size > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(status_code=413, detail="文件大小超过限制（50MB）")
        
        # 创建处理请求
        processing_request = ImageAnalysisRequest(
            tenant_id=tenant_id,
            customer_id=customer_id,
            processing_type=ProcessingType.IMAGE_ANALYSIS,
            image_format=image_format,
            analysis_types=analysis_types,
            image_quality=image_quality,
            max_image_size_mb=file_size / (1024 * 1024),
            detect_products=detect_products,
            analyze_skin_condition=analyze_skin_condition,
            async_processing=async_processing
        )
        
        # 处理文件上传
        result = await multimodal_handler.process_image_upload(
            file=file,
            request=processing_request,
            thread_id=thread_id,
            background_tasks=background_tasks
        )
        
        return result
        
    except Exception as e:
        logger.error(f"图像文件上传失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversation/multimodal", response_model=Dict[str, Any])
async def create_multimodal_conversation(
    background_tasks: BackgroundTasks,
    tenant_id: str = Form(..., description="租户标识符"),
    customer_id: Optional[str] = Form(None, description="客户ID"),
    thread_id: Optional[str] = Form(None, description="对话ID"),
    text_message: Optional[str] = Form(None, description="文本消息"),
    language: str = Form("zh-CN", description="语言代码"),
    voice_files: Optional[List[UploadFile]] = File(None, description="语音文件列表"),
    image_files: Optional[List[UploadFile]] = File(None, description="图像文件列表")
):
    """
    创建多模态对话
    
    支持同时处理文本、语音和图像输入，提供综合的对话体验。
    """
    try:
        # 验证至少有一种输入
        if not text_message and not voice_files and not image_files:
            raise HTTPException(status_code=400, detail="至少需要提供一种输入类型")
        
        # 处理多模态对话创建
        result = await multimodal_handler.create_multimodal_conversation(
            tenant_id=tenant_id,
            customer_id=customer_id,
            thread_id=thread_id,
            text_message=text_message,
            language=language,
            voice_files=voice_files or [],
            image_files=image_files or [],
            background_tasks=background_tasks
        )
        
        return result
        
    except Exception as e:
        logger.error(f"多模态对话创建失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/process", response_model=BatchProcessingResponse)
async def batch_process_files(
    request: BatchMultimodalRequest,
    background_tasks: BackgroundTasks
):
    """
    批量处理多模态文件
    
    支持批量上传和处理多个文件，提高处理效率。
    """
    try:
        # JWT认证中已验证租户身份，无需重复检查
        
        # 处理批量请求
        result = await multimodal_handler.batch_process_files(
            request=request,
            tenant_id=request.tenant_id,
            background_tasks=background_tasks
        )
        
        return result
        
    except Exception as e:
        logger.error(f"批量处理失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{processing_id}", response_model=ProcessingStatusResponse)
async def get_processing_status(
    processing_id: str,
    tenant_id: str = Query(..., description="租户标识符")
):
    """
    获取处理状态
    
    查询指定处理任务的当前状态和进度。
    """
    try:
        result = await multimodal_handler.get_processing_status(
            processing_id=processing_id,
            tenant_id=tenant_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"获取处理状态失败 {processing_id}: {e}", exc_info=True)
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="处理任务不存在")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/result/{processing_id}")
async def get_processing_result(
    processing_id: str,
    tenant_id: str = Query(..., description="租户标识符")
):
    """
    获取处理结果
    
    获取已完成处理任务的详细结果。
    """
    try:
        result = await multimodal_handler.get_processing_result(
            processing_id=processing_id,
            tenant_id=tenant_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"获取处理结果失败 {processing_id}: {e}", exc_info=True)
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="处理任务不存在")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capabilities", response_model=MultimodalCapabilitiesResponse)
async def get_multimodal_capabilities():
    """
    获取多模态处理能力
    
    返回系统支持的文件格式、处理类型和性能限制。
    """
    try:
        capabilities = await multimodal_handler.get_capabilities()
        
        return MultimodalCapabilitiesResponse(
            success=True,
            message="多模态能力信息获取成功",
            data=capabilities,
            supported_formats=capabilities["supported_formats"],
            processing_limits=capabilities["processing_limits"],
            available_models=capabilities["available_models"],
            features=capabilities["features"],
            performance_benchmarks=capabilities.get("performance_benchmarks")
        )
        
    except Exception as e:
        logger.error(f"获取多模态能力失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/processing/{processing_id}")
async def cancel_processing(
    processing_id: str,
    tenant_id: str = Query(..., description="租户标识符")
):
    """
    取消处理任务
    
    取消正在进行的处理任务并清理相关资源。
    """
    try:
        result = await multimodal_handler.cancel_processing(
            processing_id=processing_id,
            tenant_id=tenant_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"取消处理任务失败 {processing_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# 管理端点

@router.get("/admin/stats")
async def get_processing_stats(
    tenant_id: str = Query(..., description="租户标识符"),
    days: int = Query(7, ge=1, le=30, description="统计天数")
):
    """
    获取处理统计信息
    
    管理员端点，返回多模态处理的统计数据和趋势。
    """
    try:
        stats = await multimodal_handler.get_processing_stats(
            tenant_id=tenant_id,
            days=days
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"获取处理统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/cleanup")
async def cleanup_processing_data(
    tenant_id: str = Query(..., description="租户标识符"),
    older_than_days: int = Query(30, ge=1, le=365, description="清理多少天前的数据")
):
    """
    清理处理数据
    
    管理员端点，清理过期的临时文件和处理记录。
    """
    try:
        result = await multimodal_handler.cleanup_processing_data(
            tenant_id=tenant_id,
            older_than_days=older_than_days
        )
        
        return result
        
    except Exception as e:
        logger.error(f"清理处理数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# 健康检查

@router.get("/health")
async def health_check():
    """
    多模态服务健康检查
    
    检查多模态处理服务的运行状态。
    """
    try:
        health_info = await multimodal_handler.get_service_health()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "multimodal",
            "active_tasks": health_info.get("active_tasks", 0),
            "supported_formats": health_info.get("supported_formats", {}),
            "performance_metrics": health_info.get("performance_metrics", {})
        }
        
    except Exception as e:
        logger.error(f"多模态服务健康检查失败: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "service": "multimodal",
            "error": str(e)
        }