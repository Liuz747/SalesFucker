"""
对话状态管理模块

该模块负责对话状态的管理、监控和状态转换。

核心功能:
- 对话状态初始化和验证
- 状态转换和更新管理
- 状态监控和统计
- 错误状态处理
"""

from typing import Dict, Any, Optional

from src.agents.base import ThreadState
from utils import (
    get_component_logger,
    get_current_datetime,
    StatusMixin
)


class ThreadStateManager(StatusMixin):
    """
    对话状态管理器
    
    负责管理对话状态的生命周期，使用StatusMixin提供标准化状态管理。
    
    属性:
        tenant_id: 租户标识符
        logger: 日志记录器
        state_stats: 状态统计信息
    """
    
    def __init__(self, tenant_id: str):
        """
        初始化对话状态管理器
        
        参数:
            tenant_id: 租户标识符
        """
        super().__init__()
        
        self.tenant_id = tenant_id
        self.logger = get_component_logger(__name__, tenant_id)
        
        # 状态统计信息
        self.state_stats = {
            "total_conversations": 0,
            "successful_completions": 0,
            "error_completions": 0,
            "average_processing_time": 0.0,
            "last_activity": None
        }
    
    def create_initial_state(
        self, 
        customer_input: str, 
        customer_id: Optional[str] = None,
        input_type: str = "text"
    ) -> ThreadState:
        """
        创建初始对话状态
        
        根据客户输入和相关信息创建新的对话状态实例。
        
        参数:
            customer_input: 客户输入内容
            customer_id: 可选的客户标识符
            input_type: 输入类型 (text/voice/image)
            
        返回:
            ThreadState: 初始化的对话状态
        """
        initial_state = ThreadState(
            tenant_id=self.tenant_id,
            customer_id=customer_id,
            customer_input=customer_input,
            input_type=input_type
        )
        
        # 更新统计信息
        self.state_stats["total_conversations"] += 1
        self.state_stats["last_activity"] = get_current_datetime()
        
        self.logger.info(
            f"创建新对话状态 - 租户: {self.tenant_id}, "
            f"客户: {customer_id}, 输入类型: {input_type}"
        )
        
        return initial_state
    
    def validate_state(self, state: ThreadState) -> bool:
        """
        验证对话状态的有效性
        
        检查对话状态是否包含必要的信息和正确的格式。
        
        参数:
            state: 要验证的对话状态
            
        返回:
            bool: 验证是否通过
        """
        try:
            # 检查必要字段
            if not state.tenant_id:
                self.logger.error("对话状态缺少租户ID")
                return False
            
            if not state.thread_id:
                self.logger.error("对话状态缺少对话ID")
                return False
            
            if not state.customer_input:
                self.logger.error("对话状态缺少客户输入")
                return False
            
            # 检查状态格式
            if state.input_type not in ["text", "voice", "image"]:
                self.logger.error(f"不支持的输入类型: {state.input_type}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"状态验证过程中出错: {e}")
            return False
    
    def create_error_state(
            self, 
            original_state: ThreadState, 
            error: Exception
    ) -> ThreadState:
        """
        创建错误状态
        
        当处理过程中发生错误时，创建包含错误信息的状态。
        
        参数:
            original_state: 原始对话状态
            error: 发生的错误
            
        返回:
            ThreadState: 包含错误信息的状态
        """
        error_state = original_state.model_copy()
        error_state.error_state = str(error)
        error_state.final_response = "抱歉，我现在遇到了一些技术问题。请稍后再试，我很乐意为您提供帮助。"
        error_state.processing_complete = True
        
        # 更新错误统计
        self.state_stats["error_completions"] += 1
        
        self.logger.error(f"创建错误状态: {error}")
        
        return error_state
    
    def update_completion_stats(self, state: ThreadState, processing_time_ms: float):
        """
        更新完成统计信息
        
        记录对话处理完成的统计信息，包括成功率和处理时间。
        
        参数:
            state: 完成的对话状态
            processing_time_ms: 处理时间（毫秒）
        """
        if state.processing_complete:
            if state.error_state:
                self.state_stats["error_completions"] += 1
            else:
                self.state_stats["successful_completions"] += 1
            
            # 更新平均处理时间
            total_completions = (
                self.state_stats["successful_completions"] + 
                self.state_stats["error_completions"]
            )
            
            if total_completions > 0:
                current_avg = self.state_stats["average_processing_time"]
                self.state_stats["average_processing_time"] = (
                    (current_avg * (total_completions - 1) + processing_time_ms) / 
                    total_completions
                )
            
            self.logger.info(
                f"对话完成 - 耗时: {processing_time_ms:.2f}ms, "
                f"状态: {'成功' if not state.error_state else '失败'}"
            )
    
    def get_state_statistics(self) -> Dict[str, Any]:
        """
        获取状态统计信息
        
        使用StatusMixin提供标准化状态响应。
        
        返回:
            Dict[str, Any]: 状态统计信息
        """
        total_completed = (
            self.state_stats["successful_completions"] + 
            self.state_stats["error_completions"]
        )
        
        success_rate = 0.0
        if total_completed > 0:
            success_rate = (
                self.state_stats["successful_completions"] / total_completed * 100
            )
        
        status_data = {
            "tenant_id": self.tenant_id,
            "total_conversations": self.state_stats["total_conversations"],
            "completed_conversations": total_completed,
            "successful_completions": self.state_stats["successful_completions"],
            "error_completions": self.state_stats["error_completions"],
            "success_rate": success_rate,
            "average_processing_time": self.state_stats["average_processing_time"],
            "last_activity": self.state_stats["last_activity"]
        }
        
        return self.create_status_response(status_data, "ThreadStateManager")
    
    def reset_statistics(self):
        """
        重置统计信息
        """
        self.state_stats = {
            "total_conversations": 0,
            "successful_completions": 0,
            "error_completions": 0,
            "average_processing_time": 0.0,
            "last_activity": None
        }
        
        self.logger.info("状态统计信息已重置")
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        获取状态管理器指标数据（不做主观健康判断）
        
        返回:
            Dict[str, Any]: 原始指标数据
        """
        total_completed = (
            self.state_stats["successful_completions"] + 
            self.state_stats["error_completions"]
        )
        
        error_rate = 0.0
        if total_completed > 0:
            error_rate = (
                self.state_stats["error_completions"] / total_completed * 100
            )
        
        metrics = {
            "error_rate": error_rate,
            "error_count": self.state_stats["error_completions"],
            "successful_count": self.state_stats["successful_completions"],
            "total_conversations": self.state_stats["total_conversations"],
            "average_processing_time": self.state_stats["average_processing_time"],
            "last_activity": self.state_stats["last_activity"]
        }
        
        details = {
            "component": "ThreadStateManager",
            "total_completed": total_completed
        }
        
        return self.create_metrics_response(metrics, details) 