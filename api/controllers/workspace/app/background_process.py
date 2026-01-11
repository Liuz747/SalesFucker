"""
后台工作流处理器

该模块提供异步工作流处理功能，支持后台运行多智能体工作流
并通过回调机制将结果发送到用户指定的后端API。

主要功能:
- 后台工作流执行管理
- 状态跟踪和持久化
- 回调处理和重试机制
- 错误处理和审计日志
"""

from uuid import UUID

from config import mas_config
from core.app import Orchestrator
from libs.types import MessageParams, ThreadStatus
from models import Thread, WorkflowRun
from schemas.conversation_schema import CallbackPayload
from services import ThreadService
from utils import (
    get_component_logger,
    get_current_datetime,
    get_processing_time_ms,
    get_current_timestamp,
    ExternalClient
)


logger = get_component_logger(__name__, "BackgroundProcessor")


class BackgroundWorkflowProcessor:
    """后台工作流处理器"""

    def __init__(self):
        """初始化后台处理器"""
        self.client = ExternalClient()
        
        # 回调端点路径
        self.callback_endpoint = "/api"
    
    async def send_callback(
        self,
        callback_url: str,
        payload: CallbackPayload
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
                data=payload.model_dump(),
                headers={"User-Agent": "MAS-Background-Processor/1.0"},
                timeout=30.0,
                max_retries=3
            )
            
            logger.info(f"回调成功发送到: {callback_url}")
            return True
                        
        except Exception as e:
            logger.error(f"回调发送异常: {callback_url}, 错误: {str(e)}")
            return False
    
    async def process_workflow_background(
        self,
        orchestrator: Orchestrator,
        run_id: UUID,
        thread: Thread,
        inputs: MessageParams
    ):
        """在后台处理工作流"""
        start_time = get_current_datetime()
        callback_url = str(mas_config.CALLBACK_URL).rstrip('/') + self.callback_endpoint
        logger.info(f"开始后台处理工作流 - 运行: {run_id}, 线程: {thread.thread_id}")

        try:
            # 创建工作流执行模型
            workflow = WorkflowRun(
                workflow_id=run_id,
                thread_id=thread.thread_id,
                assistant_id=thread.assistant_id,
                tenant_id=thread.tenant_id,
                type="chat",
                inputs=inputs
            )

            # 使用编排器处理消息 - 核心工作流调用
            result = await orchestrator.dispatch(workflow)

            # 构建工作流数据
            workflow_data = {
                "inputs": inputs,
                "output": result.output,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens
            }

            # 更新线程状态
            await ThreadService.update_thread_status(thread.thread_id, ThreadStatus.ACTIVE)
            logger.debug(f"线程状态更新: {thread.thread_id}")

            processing_time = get_processing_time_ms(start_time)

            logger.info(f"工作流处理完成 - 运行: {run_id}, 工作流: {run_id}, 耗时: {processing_time:.2f}ms")

            payload = CallbackPayload(
                run_id=run_id,
                thread_id=thread.thread_id,
                assistant_id=thread.assistant_id,
                tenant_id=thread.tenant_id,
                status="completed",
                data=workflow_data,
                processing_time=processing_time,
                finished_at=get_current_timestamp()
            )

            # 发送回调
            await self.send_callback(callback_url, payload)

        except Exception as e:
            logger.error(f"后台处理失败 - 运行: {run_id}: {e}", exc_info=True)

            # 更新线程状态为失败
            await ThreadService.update_thread_status(thread.thread_id, ThreadStatus.FAILED)
            logger.debug(f"线程状态更新为失败: {thread.thread_id}")

            # 发送失败回调
            failure_payload = CallbackPayload(
                run_id=run_id,
                thread_id=thread.thread_id,
                assistant_id=thread.assistant_id,
                tenant_id=thread.tenant_id,
                status="failed",
                error=str(e),
                processing_time=get_processing_time_ms(start_time),
                finished_at=get_current_timestamp()
            )
            await self.send_callback(callback_url, failure_payload)
