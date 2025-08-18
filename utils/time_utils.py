"""
时间处理工具模块

提供标准化的时间处理函数，消除重复的时间戳生成代码。

核心功能:
- 统一时间戳格式（使用Asia/Shanghai时区）
- 处理时间计算
"""

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

# 使用Asia/Shanghai作为默认时区
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


def get_current_datetime() -> datetime:
    """
    获取当前Shanghai时间的datetime对象
    
    用于性能测量、时间戳生成等。统一的时间获取方法。
    
    返回:
        datetime: Shanghai时区的datetime对象
    """
    return datetime.now(SHANGHAI_TZ)


def get_processing_time_ms(start_time: datetime) -> float:
    """
    计算处理时间（毫秒）
    
    消除重复的时间差计算代码
    
    参数:
        start_time: 开始时间
        
    返回:
        float: 处理时间（毫秒）
    """
    return (datetime.now(SHANGHAI_TZ) - start_time).total_seconds() * 1000


def to_isoformat(dt: Optional[datetime] = None) -> str:
    """
    格式化时间戳为ISO格式字符串
    
    参数:
        dt: 要格式化的时间，为None则使用当前Shanghai时间
        
    返回:
        str: ISO格式时间戳 (e.g., "2024-01-15T10:30:45.123456+08:00")
    """
    if dt is None:
        dt = get_current_datetime()
    return dt.isoformat()


def from_isoformat(dt: str) -> datetime:
    """
    格式化ISO格式字符串为时间戳
    
    参数:
        dt: 要格式化的时间，为None则使用当前Shanghai时间
        
    返回:
        str: ISO格式时间戳 (e.g., "2024-01-15T10:30:45.123456+08:00")
    """
    return datetime.fromisoformat(dt)


def from_timestamp(timestamp: int) -> datetime:
    """
    将时间戳转换为Shanghai时区的datetime对象

    参数:
        timestamp: 时间戳（整数，秒级）

    返回:
        datetime: Shanghai时区的datetime对象
    """
    return datetime.fromtimestamp(timestamp, tz=SHANGHAI_TZ)
