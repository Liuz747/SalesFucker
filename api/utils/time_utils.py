"""
时间处理工具模块

提供标准化的时间处理函数，消除重复的时间戳生成代码。

核心功能:
- 获取当前 UTC datetime
- 统一时间戳格式
- 处理时间计算
- 免打扰时间检查
"""

from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from config import mas_config


def get_current_datetime() -> datetime:
    """
    获取当前 UTC 时间的datetime对象

    用于性能测量、时间戳生成等。统一的时间获取方法。

    返回:
        datetime: 当前 UTC 时间的datetime对象
    """
    return datetime.now(timezone.utc)


def get_current_timezone_time(timezone_str: str) -> datetime:
    """
    获取指定时区的当前时间

    该函数是时间工具的核心辅助函数，用于消除重复的时区时间获取代码。

    参数:
        timezone_str: 时区字符串（例如 "Asia/Shanghai", "America/New_York"）

    返回:
        datetime: 指定时区的当前时间对象

    示例:
        >>> dt = get_current_timezone_time("Asia/Shanghai")
        >>> dt.tzinfo
        ZoneInfo(key='Asia/Shanghai')
    """
    tz = ZoneInfo(timezone_str)
    return datetime.now(tz)


def get_chinese_time() -> str:
    """
    获取当前中国时区时间，格式化为中文字符串

    返回:
        str: 格式化的时间字符串，如 "2025年9月10日 周一 14时30分"
    """
    dt = get_current_timezone_time("Asia/Shanghai")
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


def is_dnd_active(timezone: str | None = None) -> bool:
    """
    检查当前时间是否在免打扰时段内

    支持跨天的免打扰时段（例如 22:00 - 08:00）

    参数:
        timezone: 时区字符串（例如 "Asia/Shanghai"），None 则使用配置默认值

    返回:
        bool: True 表示当前在免打扰时段内，不应发送消息

    示例:
        >>> # DND: 22:00 - 08:00, 当前时间: 23:00
        >>> is_dnd_active()  # True

        >>> # DND: 22:00 - 08:00, 当前时间: 10:00
        >>> is_dnd_active()  # False
    """
    # 如果 DND 功能未启用，直接返回 False
    if not mas_config.DND_ENABLED:
        return False

    # 使用配置的时区或默认时区
    tz_str = timezone or mas_config.APP_TIMEZONE

    # 使用统一的时区时间获取函数
    now = get_current_timezone_time(tz_str)
    current_hour = now.hour

    start_hour = mas_config.DND_START_HOUR
    end_hour = mas_config.DND_END_HOUR

    # 处理跨天情况（例如 22:00 - 08:00）
    if start_hour > end_hour:
        # 跨天：如果当前小时 >= 起始小时 或 < 结束小时，则在 DND 时段内
        return current_hour >= start_hour or current_hour < end_hour
    else:
        # 不跨天：如果当前小时在 [start_hour, end_hour) 内，则在 DND 时段内
        return start_hour <= current_hour < end_hour
