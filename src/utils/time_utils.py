"""
时间处理工具模块

提供标准化的时间处理函数，消除重复的时间戳生成代码。

核心功能:
- 统一时间戳格式
- 处理时间计算
- 时间戳混入类
"""

from datetime import datetime
from typing import Optional


def get_current_timestamp() -> str:
    """
    获取当前UTC时间戳（ISO格式）
    
    消除重复的 datetime.utcnow().isoformat() 调用
    
    返回:
        str: ISO格式的UTC时间戳
    """
    return datetime.utcnow().isoformat()


def get_processing_time_ms(start_time: datetime) -> float:
    """
    计算处理时间（毫秒）
    
    消除重复的时间差计算代码
    
    参数:
        start_time: 开始时间
        
    返回:
        float: 处理时间（毫秒）
    """
    return (datetime.utcnow() - start_time).total_seconds() * 1000


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """
    格式化时间戳
    
    参数:
        dt: 要格式化的时间，为None则使用当前时间
        
    返回:
        str: ISO格式时间戳
    """
    if dt is None:
        dt = datetime.utcnow()
    return dt.isoformat()


class TimestampMixin:
    """
    时间戳混入类
    
    为需要时间戳功能的类提供标准化的时间处理方法。
    """
    
    def get_timestamp(self) -> str:
        """获取当前时间戳"""
        return get_current_timestamp()
    
    def calculate_processing_time(self, start_time: datetime) -> float:
        """计算处理时间"""
        return get_processing_time_ms(start_time)
    
    def format_time(self, dt: Optional[datetime] = None) -> str:
        """格式化时间"""
        return format_timestamp(dt) 