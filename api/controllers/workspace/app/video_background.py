"""
视频生成后台处理器

该模块提供异步视频生成处理功能，支持后台运行视频生成任务
并通过回调机制将结果发送到用户指定的API。
"""

from config import mas_config
from schemas.video_schema import (
    VideoGenerationRequest,
    VideoTaskStatus,
    VideoCallbackPayload
)
from services.video_service import VideoService
from utils import (
    get_component_logger,
    get_current_timestamp_ms,
    ExternalClient
)

logger = get_component_logger(__name__, "VideoBackgroundProcessor")


class BackgroundVideoProcessor:
    """视频生成后台处理器"""

    # 回调端点路径
    CALLBACK_ENDPOINT = "/chat/ai/hook/event"

    def __init__(self):
        """初始化后台处理器"""
        self.client = ExternalClient()

    async def send_callback(
        self,
        callback_url: str,
        payload: dict
    ) -> bool:
        """
        发送回调到用户后端API

        参数:
            callback_url: 回调URL地址
            payload: 回调载荷数据

        返回:
            bool: 是否发送成功
        """
        try:
            await self.client.make_request(
                "POST",
                callback_url,
                data=payload,
                headers={"User-Agent": "MAS-Video-Processor/1.0"},
                timeout=30.0,
                max_retries=3
            )

            logger.info(f"视频回调成功发送到: {callback_url}")
            return True

        except Exception as e:
            logger.error(f"视频回调发送异常: {callback_url}, 错误: {str(e)}")
            return False

    async def process_video_generation(
        self,
        request: VideoGenerationRequest,
        tenant_id: str
    ):
        """
        后台处理视频生成任务

        参数:
            request: 视频生成请求
            tenant_id: 租户ID
        """
        session_id = request.session_id
        start_time = get_current_timestamp_ms()
        logger.info(f"开始后台视频生成 - session_id: {session_id}")

        # 构建回调URL
        callback_url = str(mas_config.CALLBACK_URL).rstrip('/') + self.CALLBACK_ENDPOINT

        try:
            # 1. 查询历史任务
            task = await VideoService.get_task_status(session_id)

            if task:
                logger.info(f"视频任务已存在 - session_id: {session_id}")
                video_url = task.get("video_url")

            # 2. 提交任务到Dashscope
            dashscope_task_id = await VideoService.submit_video_generation(
                request=request,
                tenant_id=tenant_id
            )

            # 3. 更新状态为运行中
            await VideoService.update_task_status(
                tenant_id=tenant_id,
                session_id=session_id,
                status=VideoTaskStatus.RUNNING
            )

            # 4. 轮询等待结果
            result = await VideoService.poll_task_status(dashscope_task_id)

            finished_at = get_current_timestamp_ms()
            processing_time = finished_at - start_time

            # 5. 更新最终状态
            await VideoService.update_task_status(
                tenant_id=tenant_id,
                session_id=session_id,
                status=result["status"],
                video_url=result.get("video_url"),
                error=result.get("error"),
                finished_at=finished_at
            )

            logger.info(
                f"视频生成完成 - session_id: {session_id}, "
                f"status: {result['status']}, 耗时: {processing_time}ms"
            )

            # 6. 发送回调
            callback_payload = VideoCallbackPayload(
                session_id=session_id,
                tenant_id=tenant_id,
                status="succeeded",
                video_url=result.get("video_url"),
                processing_time=processing_time
            )

            content = {
                "eventTime": get_current_timestamp_ms(),
                "eventContent": callback_payload.model_dump(mode="json"),
            }

            await self.send_callback(callback_url, content)

        except Exception as e:
            logger.error(f"视频生成失败 - session_id: {session_id}: {e}", exc_info=True)

            finished_at = get_current_timestamp_ms()
            processing_time = finished_at - start_time

            # 更新失败状态
            await VideoService.update_task_status(
                tenant_id=tenant_id,
                session_id=session_id,
                status=VideoTaskStatus.FAILED,
                error=str(e),
                finished_at=finished_at
            )

            # 发送失败回调
            failure_payload = VideoCallbackPayload(
                session_id=session_id,
                tenant_id=tenant_id,
                status="failed",
                error=str(e),
                processing_time=processing_time
            )

            content = {
                "eventTime": get_current_timestamp_ms(),
                "eventContent": failure_payload.model_dump(mode="json"),
            }

            await self.send_callback(callback_url, content)
