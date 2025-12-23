"""
视频生成路由器

该模块提供视频生成相关的API端点，包括：
- 异步视频生成（后台处理）
- 任务状态查询
- 支持文本生成视频和图像生成视频
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks

from models import TenantModel
from schemas.video_schema import (
    VideoGenerationRequest,
    VideoGenerationResponse,
    VideoStatusResponse,
    VideoTaskStatus
)
from services.video_service import VideoService
from utils import get_component_logger, get_current_timestamp_ms
from ..wraps import validate_and_get_tenant
from .video_background import BackgroundVideoProcessor

logger = get_component_logger(__name__, "VideoRouter")

# 创建视频路由器
router = APIRouter()


@router.post("", response_model=VideoGenerationResponse)
async def create_video_generation(
    request: VideoGenerationRequest,
    background_tasks: BackgroundTasks,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    创建视频生成任务

    启动异步视频生成任务，立即返回session_id。
    任务完成后会通过配置的回调URL通知（mas_config.CALLBACK_URL）。

    支持的生成模式：
    - 文本生成视频: 仅提供prompt
    - 图像生成视频: 提供prompt + input_reference(type=image)
    - 视频续写: 提供prompt + input_reference(type=video)

    Headers:
        X-Tenant-ID: 租户ID（必需）

    Request Body:
        - session_id: 会话ID，作为任务唯一标识（必需）
        - prompt: 视频内容描述（必需，最多1500字符）
        - model: 视频生成模型（默认: wan2.6-t2v）
        - size: 视频分辨率（默认: 1280*720）
        - length: 视频时长（5/10/15秒，默认: 5）
        - input_reference: 输入参考（可选，图片或视频URL）
        - negative_prompt: 负面提示词（可选）
        - prompt_extend: 是否启用提示词优化（默认: true）

    Returns:
        VideoGenerationResponse: 包含session_id和初始状态
    """
    try:
        created_at = get_current_timestamp_ms()

        logger.info(f"创建视频生成任务 - session_id: {request.session_id}, tenant: {tenant.tenant_id}")

        # 获取后台处理器
        processor = BackgroundVideoProcessor()

        # 添加后台任务
        background_tasks.add_task(
            processor.process_video_generation,
            request=request,
            tenant_id=tenant.tenant_id
        )

        logger.info(f"视频生成任务已提交 - session_id: {request.session_id}")

        # 立即返回响应
        return VideoGenerationResponse(
            session_id=request.session_id,
            status=VideoTaskStatus.PENDING
        )

    except Exception as e:
        logger.error(f"视频生成任务创建失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"视频生成任务创建失败: {str(e)}")


@router.get("/{session_id}/status", response_model=VideoStatusResponse)
async def get_video_status(
    session_id: str,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    获取视频生成任务状态

    查询指定session_id的当前状态和处理进度。

    Headers:
        X-Tenant-ID: 租户ID（必需）

    Path Parameters:
        session_id: 会话ID

    Returns:
        VideoStatusResponse: 任务状态信息
    """
    try:
        task_info = await VideoService.get_task_status(tenant.tenant_id, session_id)

        if not task_info:
            raise HTTPException(
                status_code=404,
                detail=f"任务不存在: {session_id}"
            )

        return VideoStatusResponse(
            session_id=session_id,
            status=VideoTaskStatus(task_info["status"]),
            video_url=task_info.get("video_url"),
            error=task_info.get("error"),
            created_at=task_info["created_at"],
            finished_at=task_info.get("finished_at")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"任务状态查询失败 - session_id: {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"任务状态查询失败: {str(e)}")
