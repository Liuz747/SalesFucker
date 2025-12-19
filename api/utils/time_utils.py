"""
时间处理工具模块

提供标准化的时间处理函数，消除重复的时间戳生成代码。

核心功能:
- 获取当前 UTC datetime
- 统一时间戳格式
- 处理时间计算
"""

from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo


def get_current_datetime() -> datetime:
    """
    获取当前 UTC 时间的datetime对象

    用于性能测量、时间戳生成等。统一的时间获取方法。

    返回:
        datetime: 当前 UTC 时间的datetime对象
    """
    return datetime.now(timezone.utc)


def get_chinese_time() -> str:
    """
    获取当前中国时区时间，格式化为中文字符串

    返回:
        str: 格式化的时间字符串，如 "2025年9月10日 周一 14时30分"
    """
    dt = datetime.now(ZoneInfo("Asia/Shanghai"))
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    return f"{dt.year}年{dt.month}月{dt.day}日 周{weekdays[dt.weekday()]} {dt.hour:02d}时{dt.minute:02d}分"


def get_current_timestamp_ms() -> int:
    """
    获取当前 UTC 时间的毫秒级时间戳

    返回整数类型的毫秒级时间戳，用于需要高精度时间测量的场景。

    返回:
        int: 当前 UTC 时间的毫秒级时间戳（13位整数）

    示例:
        >>> get_current_timestamp_ms()
        1735516800000
    """
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def get_current_timestamp() -> int:
    """
    获取当前 UTC 时间的秒级时间戳

    返回整数类型的秒级时间戳（Unix timestamp），这是标准的时间戳格式。

    返回:
        int: 当前 UTC 时间的秒级时间戳（10位整数）

    示例:
        >>> get_current_timestamp()
        1735516800
    """
    return int(datetime.now(timezone.utc).timestamp())


def get_processing_time_ms(start_time: datetime) -> float:
    """
    计算处理时间（毫秒）
    
    消除重复的时间差计算代码
    
    参数:
        start_time: 开始时间
    """
    return (datetime.now(timezone.utc) - start_time).total_seconds() * 1000


def get_processing_time(start_time: datetime) -> float:
    """
    计算处理时间（秒）
    
    参数:
        start_time: 开始时间
    """
    return (datetime.now(timezone.utc) - start_time).total_seconds()


def to_isoformat(dt: Optional[datetime] = None) -> str:
    """
    格式化时间戳为ISO格式字符串
    
    参数:
        dt: 要格式化的时间，为None则使用当前 UTC 时间
        
    返回:
        str: ISO格式时间戳 (e.g., "2024-01-15T10:30:45.123456Z")
    """
    if dt is None:
        dt = get_current_datetime()
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def from_isoformat(dt: str) -> datetime:
    """
    从ISO格式字符串解析为 UTC 的datetime对象
    
    参数:
        dt: 要解析的ISO字符串
        
    返回:
        datetime: UTC 时间的datetime对象
    """
    if dt.endswith("Z"):
        dt = dt.replace("Z", "+00:00")
    return datetime.fromisoformat(dt).astimezone(timezone.utc)


def from_timestamp(timestamp: int) -> datetime:
    """
    将时间戳转换为 UTC 时区的datetime对象

    参数:
        timestamp: 时间戳（整数，秒级）

    返回:
        datetime:  UTC 时区的datetime对象
    """
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def from_timestamp_ms(timestamp: int) -> datetime:
    """
    将毫秒级时间戳转换为 UTC 时区的datetime对象

    参数:
        timestamp: 时间戳（整数，毫秒级）

    返回:
        datetime:  UTC 时区的datetime对象
    """
    return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
