"""
视频生成服务层

该模块实现视频生成相关的业务逻辑，包括：
- Dashscope API调用封装
- 异步任务管理
- 状态跟踪和缓存
- 多轮对话短期记忆
"""

import asyncio
from typing import Optional

import msgpack
from dashscope import VideoSynthesis

from config import mas_config
from libs.factory import infra_registry
from schemas.exceptions import VideoConfigurationException, VideoSubmissionException
from schemas.video_schema import (
    VideoGenerationRequest,
    VideoTaskStatus,
    InputReferenceType
)
from utils import get_component_logger, get_current_timestamp_ms, ExternalClient

logger = get_component_logger(__name__, "VideoService")


class VideoService:
    """
    视频生成服务

    提供:
    - 文本生成视频 (T2V)
    - 图像生成视频 (I2V)
    - 任务状态管理
    - 多轮对话短期记忆
    """

    # Redis键前缀
    TASK_KEY_PREFIX = "video_session"
    TASK_TTL = 86400  # 24小时

    # ------------- serialization -------------
    @staticmethod
    def _pack(data: dict) -> bytes:
        """序列化数据到msgpack"""
        return msgpack.packb(data, use_bin_type=True)

    @staticmethod
    def _unpack(payload: bytes) -> dict:
        """从msgpack反序列化数据"""
        return msgpack.unpackb(payload, raw=False)

    @classmethod
    def _verify_api_key(cls) -> str:
        """验证并返回API密钥"""
        api_key = mas_config.DASHSCOPE_API_KEY
        if not api_key:
            raise VideoConfigurationException()
        return api_key

    # ------------- key helpers -------------
    @classmethod
    def _key(cls, session_id: str) -> str:
        """生成任务状态的Redis键"""
        return f"{cls.TASK_KEY_PREFIX}:{session_id}"

    # ------------- task management -------------
    @classmethod
    async def submit_video_generation(
        cls,
        request: VideoGenerationRequest,
        tenant_id: str
    ) -> str:
        """
        提交视频生成任务到Dashscope

        参数:
            request: 视频生成请求
            tenant_id: 租户ID

        返回:
            str: Dashscope任务ID
        """
        api_key = cls._verify_api_key()

        logger.info(f"[VideoGen] 提交任务 - session_id: {request.session_id}, model: {request.model}")

        # 构建请求参数
        params = {
            "api_key": api_key,
            "model": request.model,
            "prompt": request.prompt,
            "size": request.size,
            "duration": request.length,
            "prompt_extend": request.prompt_extend
        }

        # 添加负面提示词
        if request.negative_prompt:
            params["negative_prompt"] = request.negative_prompt

        # 处理输入参考（图生视频或视频续写）
        if request.input_reference:
            if request.input_reference.type == InputReferenceType.IMAGE:
                params["image_url"] = request.input_reference.url
            elif request.input_reference.type == InputReferenceType.VIDEO:
                params["video_url"] = request.input_reference.url

        # 异步提交任务
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: VideoSynthesis.async_call(**params)
        )

        if response.status_code != 200:
            logger.error(f"[VideoGen] 任务提交失败: {response.message}")
            raise VideoSubmissionException(str(response.message))

        dashscope_task_id = response.output.task_id
        logger.info(f"[VideoGen] 任务已提交 - dashscope_task_id: {dashscope_task_id}")

        # 保存任务映射到Redis
        await cls._save_task(
            tenant_id=tenant_id,
            session_id=request.session_id,
            dashscope_task_id=dashscope_task_id,
            request=request
        )

        return dashscope_task_id

    @classmethod
    async def poll_task_status(
        cls,
        dashscope_task_id: str,
        max_wait_time: int = 600,
        poll_interval: int = 15
    ) -> dict:
        """
        轮询任务状态直到完成

        参数:
            dashscope_task_id: Dashscope任务ID
            max_wait_time: 最大等待时间（秒）
            poll_interval: 轮询间隔（秒）

        返回:
            dict: 任务结果
        """
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            await asyncio.sleep(poll_interval)
            elapsed_time += poll_interval

            # 查询任务状态
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: VideoSynthesis.fetch(task=dashscope_task_id)
            )

            if response.status_code != 200:
                logger.warning(f"[VideoGen] 状态查询失败: {response.message}")
                continue

            task_status = response.output.task_status
            logger.debug(f"[VideoGen] 任务状态: {task_status}, 已等待: {elapsed_time}秒")

            if task_status == "SUCCEEDED":
                return {
                    "status": VideoTaskStatus.SUCCEEDED,
                    "video_url": response.output.video_url,
                    "actual_prompt": getattr(response.output, "actual_prompt", None),
                    "usage": getattr(response, "usage", None)
                }

            elif task_status == "FAILED":
                error_message = getattr(response.output, "message", "Unknown error")
                return {
                    "status": VideoTaskStatus.FAILED,
                    "error": error_message
                }

        # 超时
        return {
            "status": VideoTaskStatus.FAILED,
            "error": f"任务超时，已等待{elapsed_time}秒"
        }

    @classmethod
    async def get_task_status(cls, session_id: str) -> Optional[dict]:
        """
        获取任务状态

        参数:
            tenant_id: 租户ID
            session_id: 会话ID

        返回:
            dict: 任务状态信息
        """
        redis_client = infra_registry.get_cached_clients().redis
        key = cls._key(session_id)

        payload = await redis_client.get(key)
        if not payload:
            return None

        return cls._unpack(payload)

    @classmethod
    async def update_task_status(
        cls,
        session_id: str,
        status: VideoTaskStatus,
        video_url: Optional[str] = None,
        error: Optional[str] = None,
        finished_at: Optional[int] = None
    ):
        """
        更新任务状态

        参数:
            session_id: 会话ID
            status: 新状态
            video_url: 视频URL（成功时）
            error: 错误信息（失败时）
            finished_at: 完成时间
        """
        redis_client = infra_registry.get_cached_clients().redis
        key = cls._key(session_id)

        # 获取现有数据
        payload = await redis_client.get(key)
        if not payload:
            logger.warning(f"[VideoGen] 任务不存在，无法更新: {session_id}")
            return

        data = cls._unpack(payload)

        # 更新字段
        data["status"] = status
        if video_url:
            data["video_url"] = video_url
        if error:
            data["error"] = error
        if finished_at:
            data["finished_at"] = finished_at

        # 保存更新后的数据
        await redis_client.set(key, cls._pack(data), ex=cls.TASK_TTL)
        logger.debug(f"[VideoGen] 任务状态已更新: {session_id} -> {status}")

    @classmethod
    async def _save_task(
        cls,
        tenant_id: str,
        session_id: str,
        dashscope_task_id: str,
        request: VideoGenerationRequest
    ):
        """保存任务到Redis"""
        redis_client = infra_registry.get_cached_clients().redis
        key = cls._key(session_id)

        data = {
            "dashscope_task_id": dashscope_task_id,
            "tenant_id": tenant_id,
            "status": VideoTaskStatus.PENDING,
            "prompt": request.prompt,
            "model": request.model,
            "video_url": None,
            "error": None,
            "created_at": get_current_timestamp_ms(),
            "finished_at": None
        }

        await redis_client.set(key, cls._pack(data), ex=cls.TASK_TTL)
